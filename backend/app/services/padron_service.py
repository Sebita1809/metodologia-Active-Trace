"""
app/services/padron_service.py — PadronService.

Business logic for versioned padrón ingestion:
  - preview: parse file (csv/xlsx), return entries + errors, NO DB writes
  - confirmar: create active version, deactivate previous, bulk-insert entries
  - sync_moodle: fetch from Moodle WS → confirmar (rollback on failure)
  - ver_padron_activo: return entries of the active version (email decrypted)
  - list_versiones: return version history
  - vaciar: soft-delete all versions + entries in scope

PII rules:
  - email is NEVER in logs, error messages, or __repr__
  - email is encrypted (AES-256-GCM) before DB write
  - email is decrypted ONLY in this service layer before returning

Tenant isolation: all repo calls are scoped to self._tenant_id (from JWT).

File parsing logic lives in padron_parser.py (pure/stateless).

Implemented: C-09 (padron-ingesta-moodle)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.crypto import CryptoService
from app.integrations.moodle_ws import EntradaCruda, MoodleIntegrationError, MoodleWSClient
from app.models.entrada_padron import EntradaPadron
from app.models.version_padron import VersionPadron
from app.repositories.entrada_padron_repository import EntradaPadronRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.repositories.version_padron_repository import VersionPadronRepository
from app.schemas.padron import (
    ConfirmarPadronResponse,
    EntradaParseada,
    EntradaPadronResponse,
    ErrorParseo,
    PadronPreviewResponse,
    VersionPadronResponse,
)
from app.services.audit_codes import AccionAuditoria
from app.services.audit_service import AuditService
from app.services.padron_parser import _FilaRaw, parsear_archivo

logger = logging.getLogger(__name__)

# Public re-export so tests that import _parsear_archivo still work
_parsear_archivo = parsear_archivo
_REQUIRED_COLUMNS = {"nombre", "apellidos", "email"}


def _entradas_crudas_to_filas(entradas_crudas: list[EntradaCruda]) -> tuple[list[_FilaRaw], list[ErrorParseo]]:
    """Convert Moodle EntradaCruda list to _FilaRaw list (same normalization as file parser)."""
    filas: list[_FilaRaw] = []
    errores: list[ErrorParseo] = []

    for idx, entrada in enumerate(entradas_crudas, start=1):
        email_norm = (entrada.email or "").strip().lower()
        nombre = (entrada.nombre or "").strip()
        apellidos = (entrada.apellidos or "").strip()

        if not nombre or not apellidos or not email_norm or "@" not in email_norm:
            errores.append(ErrorParseo(
                fila=idx,
                columna=None,
                mensaje=f"Entrada Moodle en posición {idx} con campos requeridos inválidos",
            ))
            continue

        filas.append(_FilaRaw(
            fila=idx,
            nombre=nombre,
            apellidos=apellidos,
            email=email_norm,
            comision=entrada.comision,
            regional=entrada.regional,
        ))

    return filas, errores


class PadronService:
    """Service for versioned student roster (padrón) management.

    All operations scoped to *tenant_id* from JWT — never from request body.
    PII (email) encrypted before DB writes; decrypted only here for responses.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        crypto: CryptoService,
        audit_svc: AuditService,
    ) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._crypto = crypto
        self._audit_svc = audit_svc
        self._version_repo = VersionPadronRepository(session=session, tenant_id=tenant_id)
        self._entrada_repo = EntradaPadronRepository(session=session, tenant_id=tenant_id)
        self._usuario_repo = UsuarioRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Preview — pure parse, NO DB writes
    # ------------------------------------------------------------------

    async def preview(
        self,
        *,
        file_data: bytes,
        content_type: str,
    ) -> PadronPreviewResponse:
        """Parse the uploaded file and return preview data WITHOUT persisting anything."""
        filas, errores = parsear_archivo(file_data, content_type)

        entradas_parseadas = [
            EntradaParseada(
                fila=f.fila,
                nombre=f.nombre,
                apellidos=f.apellidos,
                email=f.email,
                comision=f.comision,
                regional=f.regional,
            )
            for f in filas
        ]

        return PadronPreviewResponse(
            entradas=entradas_parseadas,
            errores=errores,
            total_filas=len(filas) + len(errores),
            total_errores=len(errores),
        )

    # ------------------------------------------------------------------
    # Confirmar — create active version from file
    # ------------------------------------------------------------------

    async def confirmar(
        self,
        *,
        current_user: CurrentUser,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        file_data: bytes,
        content_type: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> ConfirmarPadronResponse:
        """Parse file, create new active version, deactivate the previous one."""
        filas, _errores = parsear_archivo(file_data, content_type)

        return await self._persistir_version(
            current_user=current_user,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            filas=filas,
            origen="archivo",
            ip=ip,
            user_agent=user_agent,
        )

    # ------------------------------------------------------------------
    # Sync Moodle — fetch from LMS → confirmar
    # ------------------------------------------------------------------

    async def sync_moodle(
        self,
        *,
        current_user: CurrentUser,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        moodle_client: MoodleWSClient,
        curso_ref: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> ConfirmarPadronResponse:
        """Fetch padrón from Moodle and create a new active version.

        Raises MoodleIntegrationError on Moodle failure (router maps to 502).
        If Moodle fails, no version is created or activated.
        """
        # May raise MoodleIntegrationError — if so, NO version is created
        entradas_crudas = await moodle_client.fetch_padron(curso_ref)

        filas, _errores = _entradas_crudas_to_filas(entradas_crudas)

        return await self._persistir_version(
            current_user=current_user,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            filas=filas,
            origen="moodle",
            ip=ip,
            user_agent=user_agent,
        )

    # ------------------------------------------------------------------
    # Ver padrón activo
    # ------------------------------------------------------------------

    async def ver_padron_activo(
        self,
        *,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> list[EntradaPadronResponse]:
        """Return all entries of the active padrón version (email decrypted)."""
        version = await self._version_repo.get_activa(materia_id, cohorte_id)
        if version is None:
            return []

        entradas = await self._entrada_repo.list_by_version(version.id)
        return [self._to_entrada_response(e) for e in entradas]

    # ------------------------------------------------------------------
    # List versiones
    # ------------------------------------------------------------------

    async def list_versiones(
        self,
        *,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> list[VersionPadronResponse]:
        """Return version history for (materia, cohorte), newest first."""
        versiones = await self._version_repo.list_versiones(materia_id, cohorte_id)
        return [VersionPadronResponse.model_validate(v) for v in versiones]

    # ------------------------------------------------------------------
    # Vaciar — soft-delete scope
    # ------------------------------------------------------------------

    async def vaciar(
        self,
        *,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> int:
        """Soft-delete all versions and entries for (materia, cohorte) in this tenant.

        Only affects this tenant's scope.
        Returns the total number of EntradaPadron rows soft-deleted.
        """
        version_ids = await self._version_repo.list_version_ids_in_scope(
            materia_id, cohorte_id
        )

        if not version_ids:
            return 0

        entradas_eliminadas = await self._entrada_repo.soft_delete_by_versions(version_ids)
        await self._version_repo.soft_delete_scope(materia_id, cohorte_id)

        return entradas_eliminadas

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _persistir_version(
        self,
        *,
        current_user: CurrentUser,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        filas: list[_FilaRaw],
        origen: Literal["archivo", "moodle"],
        ip: str | None,
        user_agent: str | None,
    ) -> ConfirmarPadronResponse:
        """Shared logic for confirmar and sync_moodle.

        Within a single transaction:
          1. Deactivate the current active version (if any).
          2. Create a new VersionPadron (activa=True).
          3. Bulk-create EntradaPadron (email encrypted, usuario_id resolved).
          4. Emit PADRON_CARGAR audit event.
        """
        await self._version_repo.desactivar_activa(materia_id, cohorte_id)

        nueva_version = VersionPadron(
            tenant_id=self._tenant_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=current_user.user_id,
            cargado_at=datetime.now(tz=timezone.utc),
            activa=True,
            origen=origen,
        )
        nueva_version = await self._version_repo.create(nueva_version)

        entradas_objects, sin_match = await self._build_entradas(
            version=nueva_version,
            filas=filas,
        )
        if entradas_objects:
            await self._entrada_repo.bulk_create(entradas_objects)

        await self._session.flush()

        await self._audit_svc.registrar(
            current_user,
            AccionAuditoria.PADRON_CARGAR,
            materia_id=materia_id,
            filas_afectadas=len(entradas_objects),
            detalle={
                "version_id": str(nueva_version.id),
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
                "origen": origen,
                "sin_match": sin_match,
            },
            ip=ip,
            user_agent=user_agent,
        )

        return ConfirmarPadronResponse(
            version=VersionPadronResponse.model_validate(nueva_version),
            entradas_cargadas=len(entradas_objects),
            entradas_sin_match=sin_match,
        )

    async def _build_entradas(
        self,
        *,
        version: VersionPadron,
        filas: list[_FilaRaw],
    ) -> tuple[list[EntradaPadron], int]:
        """Build EntradaPadron objects from parsed rows.

        For each row: encrypt email, look up usuario_id via email_hash.
        Returns (entradas, sin_match_count).
        """
        entradas: list[EntradaPadron] = []
        sin_match = 0

        for fila in filas:
            email_hash = self._crypto.hash_deterministic(fila.email)
            usuario = await self._usuario_repo.get_by_email_hash(email_hash)
            usuario_id = usuario.id if usuario is not None else None
            if usuario_id is None:
                sin_match += 1

            entrada = EntradaPadron(
                tenant_id=self._tenant_id,
                version_id=version.id,
                usuario_id=usuario_id,
                nombre=fila.nombre,
                apellidos=fila.apellidos,
                email=self._crypto.encrypt(fila.email),  # PII encrypted
                comision=fila.comision,
                regional=fila.regional,
            )
            entradas.append(entrada)

        return entradas, sin_match

    def _to_entrada_response(self, entrada: EntradaPadron) -> EntradaPadronResponse:
        """Build EntradaPadronResponse with decrypted email."""
        return EntradaPadronResponse(
            id=entrada.id,
            version_id=entrada.version_id,
            usuario_id=entrada.usuario_id,
            nombre=entrada.nombre,
            apellidos=entrada.apellidos,
            email=self._crypto.decrypt(entrada.email),  # decrypt PII
            comision=entrada.comision,
            regional=entrada.regional,
            created_at=entrada.created_at,
        )

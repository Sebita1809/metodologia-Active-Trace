"""
app/services/calificacion_service.py — CalificacionService.

Business logic for LMS grade imports and approval calculation:
  - preview_import: parse file, return detected activities, NO DB writes
  - confirm_import: parse, filter selected activities, build Calificacion rows,
                    compute aprobado per row, emit CALIFICACIONES_IMPORTAR audit
  - finalizacion_preview: parse finalization report, return textual-only items
                          that have no calificacion yet (RN-07/RN-08)

Business rules:
  RN-01: numeric note >= umbral_pct → aprobado=True
  RN-02: textual note in valores_aprobatorios → aprobado=True
  RN-03: defaults — umbral_pct=60, valores_aprobatorios=["Satisfactorio","Supera lo esperado"]

Tenant isolation: all repo calls scoped to self._tenant_id (from JWT).

Implemented: C-10 (calificaciones-y-umbral)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.crypto import CryptoService
from app.models.calificacion import Calificacion
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.calificacion_repository import CalificacionRepository
from app.repositories.entrada_padron_repository import EntradaPadronRepository
from app.repositories.umbral_materia_repository import UmbralMateriaRepository
from app.repositories.version_padron_repository import VersionPadronRepository
from app.schemas.calificacion import (
    CalificacionRead,
    FinalizacionItem,
    FinalizacionPreviewResponse,
    ImportConfirmRequest,
    ImportPreviewResponse,
)
from app.services.audit_codes import AccionAuditoria
from app.services.audit_service import AuditService
from app.services.lms_parser import parse_finalizacion, parse_lms_grades

logger = logging.getLogger(__name__)

DEFAULT_UMBRAL_PCT = 60
DEFAULT_VALORES_APROBATORIOS = ["Satisfactorio", "Supera lo esperado"]


def _compute_aprobado(
    nota_numerica: float | None,
    nota_textual: str | None,
    umbral_pct: int = DEFAULT_UMBRAL_PCT,
    valores_aprobatorios: list[str] | None = None,
) -> bool:
    """Compute the approval status for a single grade.

    Business rules:
      RN-01: nota_numerica >= umbral_pct → aprobado=True
      RN-02: nota_textual in valores_aprobatorios → aprobado=True
      Otherwise: aprobado=False

    Parameters:
        nota_numerica      — numeric grade value, or None
        nota_textual       — textual grade value, or None
        umbral_pct         — minimum passing numeric grade (default 60)
        valores_aprobatorios — list of passing textual values; uses defaults if None
    """
    if valores_aprobatorios is None:
        valores_aprobatorios = DEFAULT_VALORES_APROBATORIOS

    if nota_numerica is not None:
        return nota_numerica >= umbral_pct

    if nota_textual is not None:
        return nota_textual in valores_aprobatorios

    return False


class CalificacionService:
    """Service for LMS grade import and approval calculation.

    All operations scoped to *tenant_id* from JWT — never from request body.
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
        self._cal_repo = CalificacionRepository(session=session, tenant_id=tenant_id)
        self._umbral_repo = UmbralMateriaRepository(session=session, tenant_id=tenant_id)
        self._entrada_repo = EntradaPadronRepository(session=session, tenant_id=tenant_id)
        self._version_repo = VersionPadronRepository(session=session, tenant_id=tenant_id)
        self._asignacion_repo = AsignacionRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Preview — pure parse, NO DB writes
    # ------------------------------------------------------------------

    async def preview_import(
        self,
        file_bytes: bytes,
        filename: str,
        asignacion_id: uuid.UUID,  # noqa: ARG002 — reserved for future filtering
    ) -> ImportPreviewResponse:
        """Parse the uploaded LMS grades file and return detected activities.

        No DB writes are performed.
        Raises ValueError on format errors (router maps to 422).
        """
        parsed = parse_lms_grades(file_bytes, filename)

        # Count unique student emails
        emails = set(parsed.emails)

        return ImportPreviewResponse(
            actividades_numericas=parsed.actividades_numericas,
            actividades_textuales=parsed.actividades_textuales,
            alumnos_detectados=len(emails),
        )

    # ------------------------------------------------------------------
    # Confirm — parse + persist grades
    # ------------------------------------------------------------------

    async def confirm_import(
        self,
        file_bytes: bytes,
        filename: str,
        request: ImportConfirmRequest,
        current_user: CurrentUser,
    ) -> list[CalificacionRead]:
        """Parse file, filter selected activities, persist Calificacion rows.

        Steps:
          1. Parse the LMS file
          2. Load the Asignacion to get materia_id and cohorte_id
          3. Get the active VersionPadron for (materia, cohorte)
          4. Load all EntradaPadron for that version — build email→entrada map
          5. Load UmbralMateria for the asignacion (or use defaults)
          6. For each row × selected activity: compute aprobado, create Calificacion
          7. Emit CALIFICACIONES_IMPORTAR audit event
          8. Return CalificacionRead list

        Raises ValueError on format errors or if asignacion not found.
        Identity comes exclusively from current_user (JWT).
        """
        parsed = parse_lms_grades(file_bytes, filename)

        # Load the Asignacion to get materia_id
        asignacion = await self._asignacion_repo.get(request.asignacion_id)
        if asignacion is None:
            raise ValueError(f"Asignacion {request.asignacion_id} no encontrada")
        if asignacion.materia_id is None:
            raise ValueError(f"Asignacion {request.asignacion_id} no tiene materia_id")
        if asignacion.cohorte_id is None:
            raise ValueError(f"Asignacion {request.asignacion_id} no tiene cohorte_id")

        materia_id = asignacion.materia_id
        cohorte_id = asignacion.cohorte_id

        # Get the active padrón version for (materia, cohorte)
        version = await self._version_repo.get_activa(materia_id, cohorte_id)
        if version is None:
            raise ValueError(
                f"No existe padron activo para la asignacion {request.asignacion_id}"
            )

        # Load all EntradaPadron rows for this version; build email→id map
        entradas = await self._entrada_repo.list_by_version(version.id)
        email_to_entrada: dict[str, uuid.UUID] = {}
        for entrada in entradas:
            try:
                email_decrypted = self._crypto.decrypt(entrada.email)
                email_to_entrada[email_decrypted.lower()] = entrada.id
            except Exception:
                # Skip entries where decryption fails (should not happen in practice)
                logger.warning(
                    "No se pudo descifrar email de entrada_padron %s",
                    entrada.id,
                    exc_info=False,
                )
                continue

        # Load UmbralMateria (or use defaults)
        umbral = await self._umbral_repo.get_by_asignacion(request.asignacion_id)
        umbral_pct = umbral.umbral_pct if umbral else DEFAULT_UMBRAL_PCT
        valores_aprobatorios: list[str] = (
            list(umbral.valores_aprobatorios)
            if umbral and umbral.valores_aprobatorios
            else DEFAULT_VALORES_APROBATORIOS
        )

        # Filter filas to only selected activities
        selected = set(request.actividades_seleccionadas)
        importado_at = datetime.now(tz=timezone.utc)

        # Build activity type lookup
        numericas_set = set(parsed.actividades_numericas)

        # Collect Calificacion objects to persist
        calificaciones: list[Calificacion] = []

        for fila in parsed.filas:
            actividad = fila["actividad"]
            if actividad not in selected:
                continue

            email = fila["email"]
            entrada_id = email_to_entrada.get(email)
            if entrada_id is None:
                # Student not in padrón — skip silently
                continue

            nota_numerica: float | None = fila.get("nota_numerica")
            nota_textual: str | None = fila.get("nota_textual")

            aprobado = _compute_aprobado(
                nota_numerica=nota_numerica,
                nota_textual=nota_textual,
                umbral_pct=umbral_pct,
                valores_aprobatorios=valores_aprobatorios,
            )

            cal = Calificacion(
                tenant_id=self._tenant_id,
                entrada_padron_id=entrada_id,
                materia_id=materia_id,
                actividad=actividad,
                nota_numerica=nota_numerica,
                nota_textual=nota_textual,
                aprobado=aprobado,
                origen="Importado",
                importado_at=importado_at,
            )
            calificaciones.append(cal)

        if calificaciones:
            calificaciones = await self._cal_repo.create_many(calificaciones)

        await self._audit_svc.registrar(
            current_user,
            AccionAuditoria.CALIFICACIONES_IMPORTAR,
            materia_id=materia_id,
            filas_afectadas=len(calificaciones),
            detalle={
                "asignacion_id": str(request.asignacion_id),
                "actividades_seleccionadas": list(selected),
                "filas_importadas": len(calificaciones),
            },
        )

        return [CalificacionRead.model_validate(c) for c in calificaciones]

    # ------------------------------------------------------------------
    # Finalizacion preview — textual activities only (RN-07/RN-08)
    # ------------------------------------------------------------------

    async def finalizacion_preview(
        self,
        file_bytes: bytes,
        filename: str,
        asignacion_id: uuid.UUID,
    ) -> FinalizacionPreviewResponse:
        """Parse LMS finalization report and return textual activities not yet graded.

        Only textual activities are returned (RN-08: finalizacion data is for
        textual grading only).

        Raises ValueError on format errors.
        """
        filas_fin = parse_finalizacion(file_bytes, filename)

        # Load asignacion to get materia/cohorte
        asignacion = await self._asignacion_repo.get(asignacion_id)
        if asignacion is None:
            raise ValueError(f"Asignacion {asignacion_id} no encontrada")
        if asignacion.materia_id is None or asignacion.cohorte_id is None:
            return FinalizacionPreviewResponse(items=[])

        # Get active padrón version
        version = await self._version_repo.get_activa(
            asignacion.materia_id, asignacion.cohorte_id
        )
        if version is None:
            return FinalizacionPreviewResponse(items=[])

        # Get all entradas and build email map
        entradas = await self._entrada_repo.list_by_version(version.id)
        email_to_entrada: dict[str, uuid.UUID] = {}
        for entrada in entradas:
            try:
                email_decrypted = self._crypto.decrypt(entrada.email)
                email_to_entrada[email_decrypted.lower()] = entrada.id
            except Exception:
                continue

        entrada_ids = list(email_to_entrada.values())

        # Get existing calificaciones (textual only — we'll filter by actividad)
        existing_cals = await self._cal_repo.list_by_entradas(entrada_ids)

        # Build set of (entrada_id, actividad) that already have a calificacion
        existing_pairs: set[tuple[uuid.UUID, str]] = {
            (c.entrada_padron_id, c.actividad) for c in existing_cals
        }

        # Build reverse map: entrada_id → email (for response)
        entrada_to_email: dict[uuid.UUID, str] = {
            entrada_id: email
            for email, entrada_id in email_to_entrada.items()
        }

        items: list[FinalizacionItem] = []

        for fila in filas_fin:
            if not fila.finalizado:
                continue

            email = fila.alumno_email
            actividad = fila.actividad

            entrada_id = email_to_entrada.get(email)
            if entrada_id is None:
                continue

            # Only textual activities (RN-08)
            # Skip if already has a calificacion for this (entrada, actividad)
            if (entrada_id, actividad) in existing_pairs:
                continue

            items.append(FinalizacionItem(
                alumno_email=entrada_to_email.get(entrada_id, email),
                actividad=actividad,
            ))

        return FinalizacionPreviewResponse(items=items)

"""
app/services/comunicacion_service.py — ComunicacionService.

Business logic for the communications module (C-12). Orchestrates:
  - Preview rendering (no persistence)
  - Batch enqueue (encolar_lote) with crypto + audit
  - Approval (aprobar) and cancellation (cancelar)
  - Queue listing with decryption

Architecture rules:
  - Services call Repositories — NEVER access DB directly.
  - Identities (actor_id, tenant_id) come EXCLUSIVELY from the JWT (CurrentUser).
  - CryptoService encrypts destinatario before persisting; decrypts only on read.
  - AuditService is called once per lote (not once per recipient).
  - Domain errors raised as ValueError with descriptive messages.

Implemented: C-12 (comunicaciones-cola-worker)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.crypto import CryptoService
from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.repositories.comunicacion_repository import ComunicacionRepository
from app.schemas.comunicacion import (
    AprobarItemRequest,
    AprobarLoteRequest,
    CancelarItemRequest,
    CancelarLoteRequest,
    ComunicacionRead,
    ColaQuery,
    EncolarLoteRequest,
    EncolarLoteResponse,
    PreviewRequest,
    PreviewResponse,
    RenderResult,
)
from app.services.audit_codes import AccionAuditoria
from app.services.audit_service import AuditService
from app.services.comunicacion_estado import render_plantilla, transicion_valida


class ComunicacionService:
    """Service for outgoing communications (C-12).

    Constructor parameters:
        session    — open AsyncSession
        tenant_id  — tenant scope (from JWT)
        crypto     — CryptoService for AES-256 encrypt/decrypt
        audit_svc  — AuditService for writing COMUNICACION_ENVIAR events
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
        self._repo = ComunicacionRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Task 5.1 — preview (no persistence)
    # ------------------------------------------------------------------

    async def preview(
        self,
        request: PreviewRequest,
        current_user: CurrentUser,
    ) -> PreviewResponse:
        """Render template for each recipient WITHOUT persisting any Comunicacion.

        RN-16: preview must be obtained before enqueueing.
        """
        resultados = []
        for dest in request.destinatarios:
            asunto_renderizado = render_plantilla(request.asunto, dest.variables)
            cuerpo_renderizado = render_plantilla(request.cuerpo, dest.variables)
            resultados.append(
                RenderResult(
                    email=dest.email,
                    asunto_renderizado=asunto_renderizado,
                    cuerpo_renderizado=cuerpo_renderizado,
                )
            )
        return PreviewResponse(resultados=resultados)

    # ------------------------------------------------------------------
    # Task 5.2 + 5.3 — encolar_lote (persist + audit)
    # ------------------------------------------------------------------

    async def encolar_lote(
        self,
        request: EncolarLoteRequest,
        current_user: CurrentUser,
    ) -> EncolarLoteResponse:
        """Create one Comunicacion per recipient in Pendiente, all with the same lote_id.

        - enviado_por and tenant_id come EXCLUSIVELY from current_user (JWT).
        - destinatario is encrypted with CryptoService before persisting.
        - A single AuditLog entry is emitted (not one per recipient).
        - All rows are created atomically in one flush.
        """
        lote_id = uuid.uuid4()

        comunicaciones = []
        for dest in request.destinatarios:
            asunto_renderizado = render_plantilla(request.asunto, dest.variables)
            cuerpo_renderizado = render_plantilla(request.cuerpo, dest.variables)
            destinatario_cifrado = self._crypto.encrypt(dest.email)

            com = Comunicacion(
                tenant_id=self._tenant_id,
                enviado_por=current_user.user_id,
                materia_id=request.materia_id,
                destinatario=destinatario_cifrado,
                asunto=asunto_renderizado,
                cuerpo=cuerpo_renderizado,
                estado=EstadoComunicacion.Pendiente.value,
                lote_id=lote_id,
            )
            comunicaciones.append(com)

        await self._repo.create_many(comunicaciones)

        # Single audit event per lote (not per recipient — D-06)
        await self._audit_svc.registrar(
            current_user,
            AccionAuditoria.COMUNICACION_ENVIAR,
            materia_id=request.materia_id,
            detalle={"lote_id": str(lote_id), "cantidad": len(comunicaciones)},
            filas_afectadas=len(comunicaciones),
            ip=None,
            user_agent=None,
        )

        return EncolarLoteResponse(lote_id=lote_id, cantidad=len(comunicaciones))

    # ------------------------------------------------------------------
    # Task 5.4 — aprobar
    # ------------------------------------------------------------------

    async def aprobar_lote(
        self,
        request: AprobarLoteRequest,
        current_user: CurrentUser,
    ) -> int:
        """Approve all Pendiente messages in a lote.

        aprobado_por comes EXCLUSIVELY from current_user (JWT).
        Returns number of rows updated.
        """
        return await self._repo.marcar_aprobado_por_lote(
            request.lote_id,
            aprobado_por=current_user.user_id,
        )

    async def aprobar_item(
        self,
        request: AprobarItemRequest,
        current_user: CurrentUser,
    ) -> int:
        """Approve a single Comunicacion by id.

        Returns 1 if updated, 0 if not found or not Pendiente.
        """
        return await self._repo.marcar_aprobado_por_id(
            request.comunicacion_id,
            aprobado_por=current_user.user_id,
        )

    # ------------------------------------------------------------------
    # Task 5.5 — cancelar
    # ------------------------------------------------------------------

    async def cancelar_lote(
        self,
        request: CancelarLoteRequest,
        current_user: CurrentUser,
    ) -> int:
        """Cancel all Pendiente messages in a lote.

        Only Pendiente messages can be cancelled (RN-15 / state machine).
        Non-Pendiente messages in the lote are left untouched.
        Returns number of rows cancelled.
        """
        pendientes = await self._repo.list_cola(
            lote_id=request.lote_id,
            estado=EstadoComunicacion.Pendiente,
        )

        cancelled = 0
        for com in pendientes:
            if not transicion_valida(com.estado, EstadoComunicacion.Cancelado):
                continue
            rowcount = await self._repo.aplicar_transicion_condicional(
                com.id,
                desde=EstadoComunicacion.Pendiente,
                hacia=EstadoComunicacion.Cancelado,
            )
            cancelled += rowcount

        return cancelled

    async def cancelar_item(
        self,
        request: CancelarItemRequest,
        current_user: CurrentUser,
    ) -> None:
        """Cancel a single Comunicacion by id.

        Raises ValueError if the transition is not valid (e.g., state is not Pendiente).
        """
        com = await self._repo.get(request.comunicacion_id)
        if com is None:
            raise ValueError(f"Comunicacion {request.comunicacion_id} not found")

        if not transicion_valida(com.estado, EstadoComunicacion.Cancelado):
            raise ValueError(
                f"No se puede cancelar una comunicación en estado '{com.estado}'. "
                "Solo se puede cancelar desde Pendiente."
            )

        await self._repo.aplicar_transicion_condicional(
            com.id,
            desde=EstadoComunicacion.Pendiente,
            hacia=EstadoComunicacion.Cancelado,
        )

    # ------------------------------------------------------------------
    # Task 5.6 — listar_cola (with decryption)
    # ------------------------------------------------------------------

    async def listar_cola(
        self,
        query: ColaQuery,
        current_user: CurrentUser,
    ) -> list[ComunicacionRead]:
        """Return communications in the queue, with destinatario decrypted.

        Decryption happens ONLY in this presentation layer — the DB always
        stores ciphertext (D-03).

        Filters: lote_id, estado (both optional).
        Tenant isolation is enforced by the repository.
        """
        coms = await self._repo.list_cola(
            lote_id=query.lote_id,
            estado=query.estado,
        )

        result = []
        for com in coms:
            try:
                destinatario_claro = self._crypto.decrypt(com.destinatario)
            except Exception:
                # If decryption fails (corrupt ciphertext), skip gracefully
                destinatario_claro = "[decryption error]"

            result.append(
                ComunicacionRead(
                    id=com.id,
                    tenant_id=com.tenant_id,
                    enviado_por=com.enviado_por,
                    materia_id=com.materia_id,
                    destinatario=destinatario_claro,
                    asunto=com.asunto,
                    cuerpo=com.cuerpo,
                    estado=com.estado,
                    lote_id=com.lote_id,
                    enviado_at=com.enviado_at,
                    aprobado_at=com.aprobado_at,
                    aprobado_por=com.aprobado_por,
                    created_at=com.created_at,
                )
            )

        return result

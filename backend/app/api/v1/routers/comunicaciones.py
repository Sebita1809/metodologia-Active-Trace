"""
api/v1/routers/comunicaciones.py — Comunicaciones endpoints.

Routes (all under /api/comunicaciones):
  POST   /preview   — render template without persisting [comunicacion:enviar]
  POST   /          — encolar lote (create Pendiente batch) [comunicacion:enviar]
  GET    /          — list queue with filters [comunicacion:enviar | comunicacion:aprobar]
  POST   /aprobar   — approve lote or individual item [comunicacion:aprobar]
  POST   /cancelar  — cancel lote or individual item [comunicacion:aprobar]

Rules enforced:
  - Identity and tenant ALWAYS from JWT (get_current_user) — never from body/params.
  - No business logic in this router — all delegated to ComunicacionService.
  - Fail-closed: missing permission → HTTP 403.
  - ValueError from service → HTTP 422.

Implemented: C-12 (comunicaciones-cola-worker)
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.models.comunicacion import EstadoComunicacion
from app.schemas.comunicacion import (
    AprobarItemRequest,
    AprobarLoteRequest,
    CancelarItemRequest,
    CancelarLoteRequest,
    ColaQuery,
    ComunicacionRead,
    EncolarLoteRequest,
    EncolarLoteResponse,
    PreviewRequest,
    PreviewResponse,
)

router = APIRouter(tags=["comunicaciones"])

_require_enviar = require_permission("comunicacion:enviar")
_require_aprobar = require_permission("comunicacion:aprobar")


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Build ComunicacionService scoped to the authenticated user's tenant."""
    from app.core.config import get_settings  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.services.audit_service import AuditService  # noqa: PLC0415
    from app.services.comunicacion_service import ComunicacionService  # noqa: PLC0415

    settings = get_settings()
    crypto = CryptoService(settings.encryption_key)
    audit_svc = AuditService(session=session, tenant_id=current_user.tenant_id)

    return ComunicacionService(
        session=session,
        tenant_id=current_user.tenant_id,
        crypto=crypto,
        audit_svc=audit_svc,
    )


# ---------------------------------------------------------------------------
# Task 8.2 — POST /preview
# ---------------------------------------------------------------------------

@router.post(
    "/preview",
    response_model=PreviewResponse,
    summary="Previsualizar render de plantilla (sin persistir)",
)
async def preview(
    body: PreviewRequest,
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_enviar),
    svc=Depends(_get_svc),
) -> PreviewResponse:
    """Render the message template for each recipient without persisting anything.

    Identity and tenant come exclusively from the JWT.
    RN-16: preview is required before enqueueing.
    """
    try:
        return await svc.preview(body, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# Task 8.3 — POST / (encolar lote)
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=EncolarLoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Encolar lote de comunicaciones",
)
async def encolar_lote(
    body: EncolarLoteRequest,
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_enviar),
    svc=Depends(_get_svc),
) -> EncolarLoteResponse:
    """Create one Comunicacion per recipient in Pendiente state with a shared lote_id.

    Identity (enviado_por, tenant_id) come exclusively from the JWT.
    Emits a single COMUNICACION_ENVIAR audit event for the entire lote.
    """
    try:
        return await svc.encolar_lote(body, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# Task 8.4 — GET / (queue listing)
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=list[ComunicacionRead],
    summary="Listar cola de comunicaciones",
)
async def listar_cola(
    lote_id: uuid.UUID | None = Query(default=None, description="Filter by lote_id"),
    estado: EstadoComunicacion | None = Query(default=None, description="Filter by estado"),
    current_user: CurrentUser = Depends(get_current_user),
    _perm_enviar: PermisoConcedido | None = Depends(
        require_permission("comunicacion:enviar")
    ),
    session: AsyncSession = Depends(get_db),
) -> list[ComunicacionRead]:
    """List communications in the queue for this tenant.

    Requires comunicacion:enviar or comunicacion:aprobar.
    destinatario is returned decrypted (service handles decryption).
    """
    from app.core.config import get_settings  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.services.audit_service import AuditService  # noqa: PLC0415
    from app.services.comunicacion_service import ComunicacionService  # noqa: PLC0415

    settings = get_settings()
    crypto = CryptoService(settings.encryption_key)
    audit_svc = AuditService(session=session, tenant_id=current_user.tenant_id)
    svc = ComunicacionService(
        session=session,
        tenant_id=current_user.tenant_id,
        crypto=crypto,
        audit_svc=audit_svc,
    )
    query = ColaQuery(lote_id=lote_id, estado=estado)
    return await svc.listar_cola(query, current_user)


# ---------------------------------------------------------------------------
# Task 8.5 — POST /aprobar
# ---------------------------------------------------------------------------

@router.post(
    "/aprobar",
    status_code=status.HTTP_200_OK,
    summary="Aprobar lote completo o destinatario individual",
)
async def aprobar(
    body: AprobarLoteRequest | AprobarItemRequest,
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_aprobar),
    svc=Depends(_get_svc),
) -> dict:
    """Approve all Pendiente messages in a lote, or a single message by id.

    aprobado_por comes exclusively from the JWT.
    """
    try:
        if isinstance(body, AprobarLoteRequest):
            updated = await svc.aprobar_lote(body, current_user)
        else:
            updated = await svc.aprobar_item(body, current_user)
        return {"actualizados": updated}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# Task 8.6 — POST /cancelar
# ---------------------------------------------------------------------------

@router.post(
    "/cancelar",
    status_code=status.HTTP_200_OK,
    summary="Cancelar lote completo o destinatario individual",
)
async def cancelar(
    body: CancelarLoteRequest | CancelarItemRequest,
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_aprobar),
    svc=Depends(_get_svc),
) -> dict:
    """Cancel all Pendiente messages in a lote, or a single message by id.

    Only Pendiente messages can be cancelled (RN-15).
    Raises HTTP 422 if transition is invalid.
    """
    try:
        if isinstance(body, CancelarLoteRequest):
            cancelled = await svc.cancelar_lote(body, current_user)
            return {"cancelados": cancelled}
        else:
            await svc.cancelar_item(body, current_user)
            return {"cancelados": 1}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

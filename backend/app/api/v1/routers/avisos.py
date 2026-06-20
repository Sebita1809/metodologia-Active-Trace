"""
api/v1/routers/avisos.py — Avisos (notice board) endpoints.

Routes (all under /api/avisos):
  POST   /              → avisos:publicar (crear aviso), HTTP 201
  GET    /              → avisos:publicar (listar_admin con total_acks)
  PATCH  /{id}          → avisos:publicar (actualizar aviso)
  DELETE /{id}          → avisos:publicar (eliminar aviso, soft delete), HTTP 204
  GET    /mis-avisos    → any authenticated user (user feed)
  POST   /{id}/ack      → avisos:ack (acusar recibo), HTTP 201

No business logic in this router — all delegated to AvisoService / AckService.
Identity (tenant_id, user_id) ALWAYS from JWT via get_current_user.

Implemented: C-15 (avisos-y-acknowledgment)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.avisos import AckResponse, AvisoCreate, AvisoListItem, AvisoResponse, AvisoUpdate
from app.services.ack_service import AckService
from app.services.aviso_service import AvisoService

router = APIRouter(tags=["avisos"])

_require_publicar = require_permission("avisos:publicar", scope="global")
_require_ack = require_permission("avisos:ack", scope="global")


def _get_aviso_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AvisoService:
    """Build AvisoService scoped to the authenticated user's tenant."""
    return AvisoService(session=session, tenant_id=current_user.tenant_id)


def _get_ack_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AckService:
    """Build AckService scoped to the authenticated user's tenant."""
    return AckService(session=session, tenant_id=current_user.tenant_id)


@router.post(
    "/",
    response_model=AvisoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_aviso(
    body: AvisoCreate,
    _perm: PermisoConcedido = Depends(_require_publicar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AvisoService = Depends(_get_aviso_svc),
) -> AvisoResponse:
    """Create a new institutional notice.

    Requires avisos:publicar permission (COORDINADOR/ADMIN).
    tenant_id from JWT — never from request body.
    """
    return await svc.crear(body, current_user)


@router.get(
    "/",
    response_model=list[AvisoResponse],
)
async def listar_avisos_admin(
    _perm: PermisoConcedido = Depends(_require_publicar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AvisoService = Depends(_get_aviso_svc),
) -> list[AvisoResponse]:
    """List all avisos for the tenant (admin view, includes total_acks).

    Requires avisos:publicar permission.
    """
    return await svc.listar_admin(current_user)


@router.get(
    "/mis-avisos",
    response_model=list[AvisoListItem],
)
async def mis_avisos(
    current_user: CurrentUser = Depends(get_current_user),
    svc: AvisoService = Depends(_get_aviso_svc),
) -> list[AvisoListItem]:
    """Return the authenticated user's visible notice feed.

    No extra permission required — any authenticated user can see their own feed.
    Audience filtering and vigencia enforced by service.
    """
    return await svc.listar_para_usuario(current_user)


@router.patch(
    "/{aviso_id}",
    response_model=AvisoResponse,
)
async def actualizar_aviso(
    aviso_id: uuid.UUID,
    body: AvisoUpdate,
    _perm: PermisoConcedido = Depends(_require_publicar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AvisoService = Depends(_get_aviso_svc),
) -> AvisoResponse:
    """Partially update an existing aviso.

    Requires avisos:publicar permission.
    Raises 404 if the aviso does not exist in this tenant.
    """
    return await svc.actualizar(aviso_id, body, current_user)


@router.delete(
    "/{aviso_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar_aviso(
    aviso_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_publicar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AvisoService = Depends(_get_aviso_svc),
) -> None:
    """Soft-delete an aviso.

    Requires avisos:publicar permission.
    Raises 404 if the aviso does not exist in this tenant.
    """
    await svc.eliminar(aviso_id, current_user)


@router.post(
    "/{aviso_id}/ack",
    response_model=AckResponse,
    status_code=status.HTTP_201_CREATED,
)
async def acusar_recibo(
    aviso_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_ack),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AckService = Depends(_get_ack_svc),
) -> AckResponse:
    """Acknowledge a notice.

    Requires avisos:ack permission.
    Raises 404 if aviso not found or not vigente.
    Raises 403 if user is not in aviso's audience.
    Raises 409 if user has already acknowledged this aviso.
    """
    return await svc.acusar(aviso_id, current_user)

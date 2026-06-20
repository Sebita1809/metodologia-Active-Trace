"""
api/v1/routers/facturas.py — Factura endpoints (C-18).

Routes (all under /api/facturas, FINANZAS only, fail-closed):

  POST   /              facturas:gestionar  → 201
  GET    /              facturas:gestionar
  GET    /{id}          facturas:gestionar
  PATCH  /{id}          facturas:gestionar
  DELETE /{id}          facturas:gestionar  → 204
  PATCH  /{id}/estado   facturas:gestionar  → Pendiente → Abonada

No business logic in this router — all delegated to FacturaService.
Identity (tenant_id) ALWAYS from JWT via get_current_user.

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.models.factura import EstadoFactura
from app.schemas.factura import (
    CambiarEstadoRequest,
    FacturaCreate,
    FacturaRead,
    FacturaUpdate,
)
from app.services.factura_service import FacturaService

router = APIRouter(tags=["facturas"])

_require_gestionar = require_permission("facturas:gestionar", scope="global")


def _get_factura_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FacturaService:
    return FacturaService(session=session, tenant_id=current_user.tenant_id)


# ---------------------------------------------------------------------------
# POST / — create factura
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=FacturaRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear_factura(
    body: FacturaCreate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: FacturaService = Depends(_get_factura_svc),
) -> FacturaRead:
    """Create a new factura. Initial estado = Pendiente."""
    return await svc.crear_factura(body)


# ---------------------------------------------------------------------------
# GET / — list facturas
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=list[FacturaRead],
)
async def listar_facturas(
    _perm: PermisoConcedido = Depends(_require_gestionar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: FacturaService = Depends(_get_factura_svc),
    usuario_id: uuid.UUID | None = Query(default=None),
    estado: EstadoFactura | None = Query(default=None),
    periodo_mes: int | None = Query(default=None, ge=1, le=12),
    periodo_anio: int | None = Query(default=None, ge=2000),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[FacturaRead]:
    """Return facturas for this tenant with optional filters."""
    return await svc.listar_facturas(
        usuario_id=usuario_id,
        estado=estado.value if estado else None,
        periodo_mes=periodo_mes,
        periodo_anio=periodo_anio,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# GET /{id} — get factura
# ---------------------------------------------------------------------------

@router.get(
    "/{factura_id}",
    response_model=FacturaRead,
)
async def get_factura(
    factura_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: FacturaService = Depends(_get_factura_svc),
) -> FacturaRead:
    """Return a single factura by id. Raises 404 if not found."""
    return await svc.get_factura(factura_id)


# ---------------------------------------------------------------------------
# PATCH /{id} — update factura
# ---------------------------------------------------------------------------

@router.patch(
    "/{factura_id}",
    response_model=FacturaRead,
)
async def actualizar_factura(
    factura_id: uuid.UUID,
    body: FacturaUpdate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: FacturaService = Depends(_get_factura_svc),
) -> FacturaRead:
    """Update factura fields. Raises 404 if not found."""
    return await svc.actualizar_factura(factura_id, body)


# ---------------------------------------------------------------------------
# DELETE /{id} — soft-delete factura
# ---------------------------------------------------------------------------

@router.delete(
    "/{factura_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar_factura(
    factura_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: FacturaService = Depends(_get_factura_svc),
) -> None:
    """Soft-delete a factura. Raises 404 if not found."""
    await svc.eliminar_factura(factura_id)


# ---------------------------------------------------------------------------
# PATCH /{id}/estado — change estado
# ---------------------------------------------------------------------------

@router.patch(
    "/{factura_id}/estado",
    response_model=FacturaRead,
)
async def cambiar_estado_factura(
    factura_id: uuid.UUID,
    body: CambiarEstadoRequest,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: FacturaService = Depends(_get_factura_svc),
) -> FacturaRead:
    """Transition factura estado: Pendiente → Abonada (sets abonada_at, RN-39).

    Raises 404 if not found.
    Raises 422 if transition is invalid.
    """
    return await svc.cambiar_estado(factura_id, body)

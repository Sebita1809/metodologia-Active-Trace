"""
api/v1/routers/liquidaciones.py — Liquidacion and Grilla Salarial endpoints (C-18).

Routes (all under /api/liquidaciones, FINANZAS only, fail-closed):

  Liquidaciones:
    POST /calcular                  liquidaciones:calcular
    GET  /periodo                   liquidaciones:ver  (query: cohorte_id, mes, anio)
    GET  /historial                 liquidaciones:ver
    GET  /{id}                      liquidaciones:ver
    POST /cerrar                    liquidaciones:cerrar

  Grilla Base (under /api/liquidaciones/grilla/base):
    POST   /                        liquidaciones:configurar-salarios  → 201
    GET    /                        liquidaciones:configurar-salarios
    PATCH  /{id}                    liquidaciones:configurar-salarios
    DELETE /{id}                    liquidaciones:configurar-salarios

  Grilla Plus (under /api/liquidaciones/grilla/plus):
    POST   /                        liquidaciones:configurar-salarios  → 201
    GET    /                        liquidaciones:configurar-salarios
    PATCH  /{id}                    liquidaciones:configurar-salarios
    DELETE /{id}                    liquidaciones:configurar-salarios

No business logic in this router — all delegated to LiquidacionService / GrillaSalarialService.
Identity (tenant_id, user_id) ALWAYS from JWT via get_current_user.
ValueError → 409 (immutability / overlap).

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.liquidacion import (
    CalcularRequest,
    CerrarRequest,
    LiquidacionRead,
    PeriodoView,
)
from app.schemas.salario_base import SalarioBaseCreate, SalarioBaseResponse, SalarioBaseUpdate
from app.schemas.salario_plus import SalarioPlusCreate, SalarioPlusResponse, SalarioPlusUpdate
from app.services.grilla_salarial_service import GrillaSalarialService
from app.services.liquidacion_service import LiquidacionService

router = APIRouter(tags=["liquidaciones"])

_require_ver = require_permission("liquidaciones:ver", scope="global")
_require_calcular = require_permission("liquidaciones:calcular", scope="global")
_require_cerrar = require_permission("liquidaciones:cerrar", scope="global")
_require_grilla = require_permission("liquidaciones:configurar-salarios", scope="global")


def _get_liq_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LiquidacionService:
    return LiquidacionService(session=session, tenant_id=current_user.tenant_id)


def _get_grilla_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> GrillaSalarialService:
    return GrillaSalarialService(session=session, tenant_id=current_user.tenant_id)


# ---------------------------------------------------------------------------
# POST /calcular
# ---------------------------------------------------------------------------

@router.post(
    "/calcular",
    response_model=list[LiquidacionRead],
    status_code=status.HTTP_200_OK,
)
async def calcular_periodo(
    body: CalcularRequest,
    _perm: PermisoConcedido = Depends(_require_calcular),
    current_user: CurrentUser = Depends(get_current_user),
    svc: LiquidacionService = Depends(_get_liq_svc),
) -> list[LiquidacionRead]:
    """Trigger salary calculation for a (cohorte, mes, anio) period.

    Idempotent for open periods: re-running updates existing rows.
    Raises 409 if the period is already closed.
    """
    try:
        return await svc.calcular_periodo(body, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /periodo
# ---------------------------------------------------------------------------

@router.get(
    "/periodo",
    response_model=PeriodoView,
)
async def vista_periodo(
    cohorte_id: uuid.UUID = Query(...),
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2000),
    _perm: PermisoConcedido = Depends(_require_ver),
    current_user: CurrentUser = Depends(get_current_user),
    svc: LiquidacionService = Depends(_get_liq_svc),
) -> PeriodoView:
    """Return the segmented view of a period with KPIs (F10.6)."""
    return await svc.vista_periodo(cohorte_id, mes, anio)


# ---------------------------------------------------------------------------
# GET /historial
# ---------------------------------------------------------------------------

@router.get(
    "/historial",
    response_model=list[LiquidacionRead],
)
async def historial(
    _perm: PermisoConcedido = Depends(_require_ver),
    current_user: CurrentUser = Depends(get_current_user),
    svc: LiquidacionService = Depends(_get_liq_svc),
) -> list[LiquidacionRead]:
    """Return all closed liquidaciones for this tenant."""
    return await svc.historial()


# ---------------------------------------------------------------------------
# GET /{id}
# ---------------------------------------------------------------------------

@router.get(
    "/{liquidacion_id}",
    response_model=LiquidacionRead,
)
async def get_liquidacion(
    liquidacion_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_ver),
    current_user: CurrentUser = Depends(get_current_user),
    svc: LiquidacionService = Depends(_get_liq_svc),
) -> LiquidacionRead:
    """Return a single liquidacion by id. Raises 404 if not found."""
    return await svc.get_by_id(liquidacion_id)


# ---------------------------------------------------------------------------
# POST /cerrar
# ---------------------------------------------------------------------------

@router.post(
    "/cerrar",
    response_model=list[LiquidacionRead],
)
async def cerrar_periodo(
    body: CerrarRequest,
    _perm: PermisoConcedido = Depends(_require_cerrar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: LiquidacionService = Depends(_get_liq_svc),
) -> list[LiquidacionRead]:
    """Close all liquidaciones in a period. Immutable once closed (RN-22).

    Emits LIQUIDACION_CERRAR audit event.
    Raises 409 if already closed or period is empty.
    """
    return await svc.cerrar_periodo(body, current_user)


# ---------------------------------------------------------------------------
# Grilla Base endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/grilla/base",
    response_model=SalarioBaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_base(
    body: SalarioBaseCreate,
    _perm: PermisoConcedido = Depends(_require_grilla),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GrillaSalarialService = Depends(_get_grilla_svc),
) -> SalarioBaseResponse:
    """Create a SalarioBase row. Raises 409 on vigency overlap."""
    try:
        return await svc.crear_base(body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/grilla/base",
    response_model=list[SalarioBaseResponse],
)
async def listar_bases(
    _perm: PermisoConcedido = Depends(_require_grilla),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GrillaSalarialService = Depends(_get_grilla_svc),
) -> list[SalarioBaseResponse]:
    """Return all active SalarioBase rows for this tenant."""
    return await svc.listar_bases()


@router.patch(
    "/grilla/base/{base_id}",
    response_model=SalarioBaseResponse,
)
async def actualizar_base(
    base_id: uuid.UUID,
    body: SalarioBaseUpdate,
    _perm: PermisoConcedido = Depends(_require_grilla),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GrillaSalarialService = Depends(_get_grilla_svc),
) -> SalarioBaseResponse:
    """Update a SalarioBase row. Raises 409 on overlap, 404 if not found."""
    try:
        return await svc.actualizar_base(base_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete(
    "/grilla/base/{base_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar_base(
    base_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_grilla),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GrillaSalarialService = Depends(_get_grilla_svc),
) -> None:
    """Soft-delete a SalarioBase row. Raises 404 if not found."""
    deleted = await svc.eliminar_base(base_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="SalarioBase no encontrado.")


# ---------------------------------------------------------------------------
# Grilla Plus endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/grilla/plus",
    response_model=SalarioPlusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_plus(
    body: SalarioPlusCreate,
    _perm: PermisoConcedido = Depends(_require_grilla),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GrillaSalarialService = Depends(_get_grilla_svc),
) -> SalarioPlusResponse:
    """Create a SalarioPlus row. Raises 409 on vigency overlap."""
    try:
        return await svc.crear_plus(body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/grilla/plus",
    response_model=list[SalarioPlusResponse],
)
async def listar_plus(
    _perm: PermisoConcedido = Depends(_require_grilla),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GrillaSalarialService = Depends(_get_grilla_svc),
) -> list[SalarioPlusResponse]:
    """Return all active SalarioPlus rows for this tenant."""
    return await svc.listar_plus()


@router.patch(
    "/grilla/plus/{plus_id}",
    response_model=SalarioPlusResponse,
)
async def actualizar_plus(
    plus_id: uuid.UUID,
    body: SalarioPlusUpdate,
    _perm: PermisoConcedido = Depends(_require_grilla),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GrillaSalarialService = Depends(_get_grilla_svc),
) -> SalarioPlusResponse:
    """Update a SalarioPlus row. Raises 409 on overlap, 404 if not found."""
    try:
        return await svc.actualizar_plus(plus_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete(
    "/grilla/plus/{plus_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar_plus(
    plus_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_grilla),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GrillaSalarialService = Depends(_get_grilla_svc),
) -> None:
    """Soft-delete a SalarioPlus row. Raises 404 if not found."""
    deleted = await svc.eliminar_plus(plus_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="SalarioPlus no encontrado.")

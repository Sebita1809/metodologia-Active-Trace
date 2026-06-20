"""
api/v1/routers/analisis.py — Analisis endpoints.

Routes (all under /api/v1/analisis):
  GET /atrasados     — alumnos atrasados por asignación [analisis:ver propio]
  GET /ranking       — ranking de actividades aprobadas [analisis:ver propio]
  GET /notas-finales — nota final agrupada por alumno [analisis:ver propio]
  GET /reporte       — métricas rápidas de la asignación [analisis:ver propio]
  GET /monitor       — monitor general de actividades del tenant [analisis:ver global]

Rules enforced:
  - Identity and tenant ALWAYS from JWT — never from params.
  - asignacion_id is business data, not identity.
  - ValueError → HTTP 422.
  - No business logic here — delegated to analisis_service.

Implemented: C-11 (analisis-atrasados-reportes)
Updated:     C-23 (monitor-general)
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.analisis import (
    AtrasadosResponse,
    MonitorGeneralResponse,
    NotasFinalesResponse,
    RankingResponse,
    ReporteAsignacion,
)
from app.services.analisis_service import (
    MonitorFilters,
    get_atrasados,
    get_monitor_general,
    get_notas_finales,
    get_ranking,
    get_reporte,
)

router = APIRouter(prefix="/analisis", tags=["analisis"])

_require_ver = require_permission("analisis:ver", scope="propio")
_require_ver_global = require_permission("analisis:ver", scope="global")


# ---------------------------------------------------------------------------
# GET /analisis/atrasados
# ---------------------------------------------------------------------------

@router.get(
    "/atrasados",
    response_model=AtrasadosResponse,
    summary="Listar alumnos atrasados de una asignación",
)
async def endpoint_atrasados(
    asignacion_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_ver),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AtrasadosResponse:
    try:
        return await get_atrasados(asignacion_id, session, current_user.tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /analisis/ranking
# ---------------------------------------------------------------------------

@router.get(
    "/ranking",
    response_model=RankingResponse,
    summary="Ranking de actividades aprobadas de una asignación",
)
async def endpoint_ranking(
    asignacion_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_ver),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RankingResponse:
    try:
        return await get_ranking(asignacion_id, session, current_user.tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /analisis/notas-finales
# ---------------------------------------------------------------------------

@router.get(
    "/notas-finales",
    response_model=NotasFinalesResponse,
    summary="Notas finales agrupadas por alumno de una asignación",
)
async def endpoint_notas_finales(
    asignacion_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_ver),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotasFinalesResponse:
    try:
        return await get_notas_finales(asignacion_id, session, current_user.tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /analisis/reporte
# ---------------------------------------------------------------------------

@router.get(
    "/reporte",
    response_model=ReporteAsignacion,
    summary="Métricas rápidas de una asignación",
)
async def endpoint_reporte(
    asignacion_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_ver),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ReporteAsignacion:
    try:
        return await get_reporte(asignacion_id, session, current_user.tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /analisis/monitor
# ---------------------------------------------------------------------------

@router.get(
    "/monitor",
    response_model=MonitorGeneralResponse,
    summary="Monitor general de actividades del tenant",
)
async def endpoint_monitor(
    materia_id: Optional[uuid.UUID] = Query(default=None),
    cohorte_id: Optional[uuid.UUID] = Query(default=None),
    comision: Optional[str] = Query(default=None),
    busqueda: Optional[str] = Query(default=None),
    estado_actividad: Optional[str] = Query(default=None),
    _perm: PermisoConcedido = Depends(_require_ver_global),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MonitorGeneralResponse:
    """Cross-cutting view of all students in the tenant with their activity status.

    Requires analisis:ver with global scope (COORDINADOR / ADMIN only).
    Identity and tenant always resolved from the JWT — never from params.
    """
    if estado_actividad is not None and estado_actividad not in (
        "al_dia", "atrasado", "sin_datos"
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"estado_actividad must be 'al_dia', 'atrasado', or 'sin_datos'; got {estado_actividad!r}",
        )

    filters = MonitorFilters(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        comision=comision,
        busqueda=busqueda,
        estado_actividad=estado_actividad,
    )
    try:
        return await get_monitor_general(
            tenant_id=current_user.tenant_id,
            filters=filters,
            db=session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

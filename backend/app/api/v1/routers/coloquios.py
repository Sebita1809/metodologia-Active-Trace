"""
api/v1/routers/coloquios.py — Coloquios / Evaluaciones endpoints.

Routes (all under /api/v1/coloquios):
  POST   /                        → crear evaluacion [coloquios:gestionar]
  GET    /                        → listar con metricas [coloquios:ver]
  GET    /metricas                → panel de metricas [coloquios:ver]
  POST   /{evaluacion_id}/alumnos → importar padron [coloquios:gestionar]
  POST   /{evaluacion_id}/reservas         → reservar [coloquios:reservar]
  DELETE /{evaluacion_id}/reservas/{rid}   → cancelar reserva [coloquios:reservar]
  GET    /{evaluacion_id}/reservas         → listar agenda [coloquios:ver]
  POST   /{evaluacion_id}/resultados       → registrar resultado [coloquios:gestionar]
  GET    /{evaluacion_id}/resultados       → listar resultados [coloquios:ver]

Rules enforced:
  - Identity and tenant ALWAYS from JWT (get_current_user) — never from body/params.
  - alumno_id on reservar comes from current_user.user_id (JWT).
  - ValueError → HTTP 422; LookupError → HTTP 409 (duplicate resultado).
  - No business logic here — delegated to EvaluacionService / ReservaService / ResultadoService.

Implemented: C-14 (evaluaciones-y-coloquios)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.coloquios import (
    EvaluacionConMetricas,
    EvaluacionCreate,
    EvaluacionRead,
    ImportarPadronRequest,
    ImportarPadronResponse,
    MetricasPanel,
    RegistrarResultadoRequest,
    ReservaEvaluacionRead,
    ReservarRequest,
    ResultadoEvaluacionRead,
)
from app.services.evaluacion_service import EvaluacionService
from app.services.reserva_service import ReservaService
from app.services.resultado_service import ResultadoService

router = APIRouter(tags=["coloquios"])

_require_gestionar = require_permission("coloquios:gestionar", scope="global")
_require_ver = require_permission("coloquios:ver", scope="propio")
_require_reservar = require_permission("coloquios:reservar", scope="propio")


# ---------------------------------------------------------------------------
# Dependency factories
# ---------------------------------------------------------------------------

def _get_eval_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EvaluacionService:
    """Build EvaluacionService scoped to the authenticated user's tenant."""
    return EvaluacionService(session=session, tenant_id=current_user.tenant_id)


def _get_reserva_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ReservaService:
    """Build ReservaService scoped to the authenticated user's tenant."""
    return ReservaService(session=session, tenant_id=current_user.tenant_id)


def _get_resultado_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ResultadoService:
    """Build ResultadoService scoped to the authenticated user's tenant."""
    return ResultadoService(session=session, tenant_id=current_user.tenant_id)


# ---------------------------------------------------------------------------
# POST /coloquios/
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=EvaluacionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva evaluación",
)
async def crear_evaluacion(
    body: EvaluacionCreate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: EvaluacionService = Depends(_get_eval_svc),
) -> EvaluacionRead:
    """Create a new evaluacion (coloquio, parcial, etc.).

    tipo and estado validation is enforced by EvaluacionCreate schema.
    Identity and tenant come exclusively from the JWT.
    """
    try:
        return await svc.crear(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /coloquios/
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=list[EvaluacionConMetricas],
    summary="Listar evaluaciones con métricas de cupo",
)
async def listar_evaluaciones(
    _perm: PermisoConcedido = Depends(_require_ver),
    svc: EvaluacionService = Depends(_get_eval_svc),
) -> list[EvaluacionConMetricas]:
    """Return all active evaluaciones for this tenant, annotated with cupos_libres_hoy."""
    return await svc.listar_con_metricas()


# ---------------------------------------------------------------------------
# GET /coloquios/metricas
# ---------------------------------------------------------------------------

@router.get(
    "/metricas",
    response_model=MetricasPanel,
    summary="Panel de métricas de coloquios",
)
async def metricas_panel(
    _perm: PermisoConcedido = Depends(_require_ver),
    svc: EvaluacionService = Depends(_get_eval_svc),
) -> MetricasPanel:
    """Return 4 aggregated counters for the coloquios dashboard panel."""
    return await svc.metricas_panel()


# ---------------------------------------------------------------------------
# POST /coloquios/{evaluacion_id}/alumnos
# ---------------------------------------------------------------------------

@router.post(
    "/{evaluacion_id}/alumnos",
    response_model=ImportarPadronResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Importar padrón de alumnos para una evaluación",
)
async def importar_padron(
    evaluacion_id: uuid.UUID,
    body: ImportarPadronRequest,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: EvaluacionService = Depends(_get_eval_svc),
) -> ImportarPadronResponse:
    """Bulk-register alumnos into an evaluacion.

    Alumnos not found in this tenant are silently omitted and counted as 'omitidos'.
    """
    try:
        return await svc.importar_padron(evaluacion_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /coloquios/{evaluacion_id}/reservas
# ---------------------------------------------------------------------------

@router.post(
    "/{evaluacion_id}/reservas",
    response_model=ReservaEvaluacionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Reservar turno para una evaluación",
)
async def reservar(
    evaluacion_id: uuid.UUID,
    body: ReservarRequest,
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_reservar),
    svc: ReservaService = Depends(_get_reserva_svc),
) -> ReservaEvaluacionRead:
    """Reserve a slot for the authenticated alumno in *evaluacion_id*.

    alumno_id comes EXCLUSIVELY from current_user (JWT) — never from body or URL.
    """
    try:
        return await svc.reservar(evaluacion_id, body, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# DELETE /coloquios/{evaluacion_id}/reservas/{reserva_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{evaluacion_id}/reservas/{reserva_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancelar reserva propia",
)
async def cancelar_reserva(
    evaluacion_id: uuid.UUID,
    reserva_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_reservar),
    svc: ReservaService = Depends(_get_reserva_svc),
) -> None:
    """Cancel a reservation.

    Only the alumno who made the reservation can cancel it.
    Only allowed when the evaluacion is still Activa.
    """
    try:
        await svc.cancelar(evaluacion_id, reserva_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /coloquios/{evaluacion_id}/reservas
# ---------------------------------------------------------------------------

@router.get(
    "/{evaluacion_id}/reservas",
    response_model=list[ReservaEvaluacionRead],
    summary="Listar agenda de reservas de una evaluación",
)
async def listar_reservas(
    evaluacion_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_ver),
    svc: ReservaService = Depends(_get_reserva_svc),
) -> list[ReservaEvaluacionRead]:
    """Return all reservas for *evaluacion_id*, scoped to this tenant."""
    return await svc.listar_agenda(evaluacion_id)


# ---------------------------------------------------------------------------
# POST /coloquios/{evaluacion_id}/resultados
# ---------------------------------------------------------------------------

@router.post(
    "/{evaluacion_id}/resultados",
    response_model=ResultadoEvaluacionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar resultado de una evaluación",
)
async def registrar_resultado(
    evaluacion_id: uuid.UUID,
    body: RegistrarResultadoRequest,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: ResultadoService = Depends(_get_resultado_svc),
) -> ResultadoEvaluacionRead:
    """Register a final grade for an alumno in *evaluacion_id*.

    Returns 409 Conflict if a resultado already exists for this alumno × evaluacion.
    """
    try:
        return await svc.registrar(evaluacion_id, body)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /coloquios/{evaluacion_id}/resultados
# ---------------------------------------------------------------------------

@router.get(
    "/{evaluacion_id}/resultados",
    response_model=list[ResultadoEvaluacionRead],
    summary="Listar resultados de una evaluación",
)
async def listar_resultados(
    evaluacion_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_ver),
    svc: ResultadoService = Depends(_get_resultado_svc),
) -> list[ResultadoEvaluacionRead]:
    """Return all resultados for *evaluacion_id*, scoped to this tenant."""
    return await svc.listar_resultados(evaluacion_id)

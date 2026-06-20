"""
api/v1/routers/asignaciones.py — Asignacion management endpoints.

Routes (all under /api/asignaciones):
  POST   /       — create asignacion (requires equipos:asignar)
  GET    /       — list asignaciones with optional filters (open within tenant)
  GET    /{id}   — get asignacion (open within tenant)
  PATCH  /{id}   — update asignacion (requires equipos:asignar)
  DELETE /{id}   — soft-delete asignacion (requires equipos:asignar), returns 204

Query params for GET /: usuario_id, materia_id, carrera_id, cohorte_id, rol, responsable_id.
No business logic in this router — all delegated to AsignacionService.

Implemented: C-07 (usuarios-y-asignaciones)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.asignacion import AsignacionCreate, AsignacionResponse, AsignacionUpdate
from app.services.asignacion_service import AsignacionConVigencia, AsignacionService

router = APIRouter(tags=["asignaciones"])

_require_asignar = require_permission("equipos:asignar", scope="global")


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AsignacionService:
    """Build AsignacionService scoped to the authenticated user's tenant."""
    return AsignacionService(session=session, tenant_id=current_user.tenant_id)


def _to_response(dto: AsignacionConVigencia) -> AsignacionResponse:
    """Convert AsignacionConVigencia to AsignacionResponse."""
    return AsignacionResponse.model_validate(dto)


@router.post("/", response_model=AsignacionResponse, status_code=status.HTTP_201_CREATED)
async def create_asignacion(
    body: AsignacionCreate,
    _perm: PermisoConcedido = Depends(_require_asignar),
    svc: AsignacionService = Depends(_get_svc),
) -> AsignacionResponse:
    dto = await svc.create(
        usuario_id=body.usuario_id,
        rol=body.rol,
        desde=body.desde,
        hasta=body.hasta,
        materia_id=body.materia_id,
        carrera_id=body.carrera_id,
        cohorte_id=body.cohorte_id,
        comisiones=body.comisiones,
        responsable_id=body.responsable_id,
    )
    return _to_response(dto)


@router.get("/", response_model=list[AsignacionResponse])
async def list_asignaciones(
    usuario_id: uuid.UUID | None = Query(default=None),
    materia_id: uuid.UUID | None = Query(default=None),
    carrera_id: uuid.UUID | None = Query(default=None),
    cohorte_id: uuid.UUID | None = Query(default=None),
    rol: str | None = Query(default=None),
    responsable_id: uuid.UUID | None = Query(default=None),
    svc: AsignacionService = Depends(_get_svc),
) -> list[AsignacionResponse]:
    dtos = await svc.list_with_filters(
        usuario_id=usuario_id,
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        rol=rol,
        responsable_id=responsable_id,
    )
    return [_to_response(d) for d in dtos]


@router.get("/{asignacion_id}", response_model=AsignacionResponse)
async def get_asignacion(
    asignacion_id: uuid.UUID,
    svc: AsignacionService = Depends(_get_svc),
) -> AsignacionResponse:
    dto = await svc.get(asignacion_id)
    if dto is None:
        raise HTTPException(status_code=404, detail="Asignacion not found")
    return _to_response(dto)


@router.patch("/{asignacion_id}", response_model=AsignacionResponse)
async def update_asignacion(
    asignacion_id: uuid.UUID,
    body: AsignacionUpdate,
    _perm: PermisoConcedido = Depends(_require_asignar),
    svc: AsignacionService = Depends(_get_svc),
) -> AsignacionResponse:
    dto = await svc.update(
        asignacion_id,
        rol=body.rol,
        desde=body.desde,
        hasta=body.hasta,
        materia_id=body.materia_id,
        carrera_id=body.carrera_id,
        cohorte_id=body.cohorte_id,
        comisiones=body.comisiones,
        responsable_id=body.responsable_id,
    )
    if dto is None:
        raise HTTPException(status_code=404, detail="Asignacion not found")
    return _to_response(dto)


@router.delete("/{asignacion_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_asignacion(
    asignacion_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_asignar),
    svc: AsignacionService = Depends(_get_svc),
) -> None:
    deleted = await svc.delete(asignacion_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Asignacion not found")

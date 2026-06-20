"""
api/v1/routers/carreras.py — Carrera catalog administration endpoints.

Routes (all under /api/admin/carreras):
  POST   /       — create carrera (requires estructura:gestionar)
  GET    /       — list carreras (open within tenant)
  GET    /{id}   — get carrera (open within tenant)
  PATCH  /{id}   — update carrera (requires estructura:gestionar)
  DELETE /{id}   — soft-delete carrera (requires estructura:gestionar), returns 204

No business logic in this router — all delegated to CarreraService.

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.carrera import CarreraCreate, CarreraResponse, CarreraUpdate
from app.services.carrera_service import CarreraService

router = APIRouter(tags=["estructura"])

_require_gestionar = require_permission("estructura:gestionar", scope="global")


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CarreraService:
    """Build CarreraService scoped to the authenticated user's tenant."""
    return CarreraService(session=session, tenant_id=current_user.tenant_id)


@router.post("/", response_model=CarreraResponse, status_code=status.HTTP_201_CREATED)
async def create_carrera(
    body: CarreraCreate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: CarreraService = Depends(_get_svc),
) -> CarreraResponse:
    try:
        carrera = await svc.create(
            codigo=body.codigo,
            nombre=body.nombre,
            estado=body.estado,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return CarreraResponse.model_validate(carrera)


@router.get("/", response_model=list[CarreraResponse])
async def list_carreras(
    svc: CarreraService = Depends(_get_svc),
) -> list[CarreraResponse]:
    carreras = await svc.list()
    return [CarreraResponse.model_validate(c) for c in carreras]


@router.get("/{carrera_id}", response_model=CarreraResponse)
async def get_carrera(
    carrera_id: uuid.UUID,
    svc: CarreraService = Depends(_get_svc),
) -> CarreraResponse:
    carrera = await svc.get(carrera_id)
    if carrera is None:
        raise HTTPException(status_code=404, detail="Carrera not found")
    return CarreraResponse.model_validate(carrera)


@router.patch("/{carrera_id}", response_model=CarreraResponse)
async def update_carrera(
    carrera_id: uuid.UUID,
    body: CarreraUpdate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: CarreraService = Depends(_get_svc),
) -> CarreraResponse:
    try:
        carrera = await svc.update(
            carrera_id,
            codigo=body.codigo,
            nombre=body.nombre,
            estado=body.estado,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if carrera is None:
        raise HTTPException(status_code=404, detail="Carrera not found")
    return CarreraResponse.model_validate(carrera)


@router.delete("/{carrera_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_carrera(
    carrera_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: CarreraService = Depends(_get_svc),
) -> None:
    deleted = await svc.delete(carrera_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Carrera not found")

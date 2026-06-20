"""
api/v1/routers/materias.py — Materia catalog administration endpoints.

Routes (all under /api/admin/materias):
  POST   /       — create materia (requires estructura:gestionar)
  GET    /       — list materias (open within tenant)
  GET    /{id}   — get materia (open within tenant)
  PATCH  /{id}   — update materia (requires estructura:gestionar)
  DELETE /{id}   — soft-delete materia (requires estructura:gestionar), returns 204

No business logic in this router — all delegated to MateriaService.

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.materia import MateriaCreate, MateriaResponse, MateriaUpdate
from app.services.materia_service import MateriaService

router = APIRouter(tags=["estructura"])

_require_gestionar = require_permission("estructura:gestionar", scope="global")


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MateriaService:
    """Build MateriaService scoped to the authenticated user's tenant."""
    return MateriaService(session=session, tenant_id=current_user.tenant_id)


@router.post("/", response_model=MateriaResponse, status_code=status.HTTP_201_CREATED)
async def create_materia(
    body: MateriaCreate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: MateriaService = Depends(_get_svc),
) -> MateriaResponse:
    try:
        materia = await svc.create(
            codigo=body.codigo,
            nombre=body.nombre,
            estado=body.estado,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return MateriaResponse.model_validate(materia)


@router.get("/", response_model=list[MateriaResponse])
async def list_materias(
    svc: MateriaService = Depends(_get_svc),
) -> list[MateriaResponse]:
    materias = await svc.list()
    return [MateriaResponse.model_validate(m) for m in materias]


@router.get("/{materia_id}", response_model=MateriaResponse)
async def get_materia(
    materia_id: uuid.UUID,
    svc: MateriaService = Depends(_get_svc),
) -> MateriaResponse:
    materia = await svc.get(materia_id)
    if materia is None:
        raise HTTPException(status_code=404, detail="Materia not found")
    return MateriaResponse.model_validate(materia)


@router.patch("/{materia_id}", response_model=MateriaResponse)
async def update_materia(
    materia_id: uuid.UUID,
    body: MateriaUpdate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: MateriaService = Depends(_get_svc),
) -> MateriaResponse:
    try:
        materia = await svc.update(
            materia_id,
            codigo=body.codigo,
            nombre=body.nombre,
            estado=body.estado,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if materia is None:
        raise HTTPException(status_code=404, detail="Materia not found")
    return MateriaResponse.model_validate(materia)


@router.delete("/{materia_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_materia(
    materia_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: MateriaService = Depends(_get_svc),
) -> None:
    deleted = await svc.delete(materia_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Materia not found")

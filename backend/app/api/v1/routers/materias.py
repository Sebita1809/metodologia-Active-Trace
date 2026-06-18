"""CRUD endpoints for Materia (subjects)."""

import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, UserContext
from app.core.permissions import require_permission
from app.schemas.estructura import MateriaCreate, MateriaResponse, MateriaUpdate
from app.services.estructura.materia_service import MateriaService

router = APIRouter(prefix="/admin/materias", tags=["admin"])


@router.get("/", response_model=list[MateriaResponse])
async def list_materias(
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = MateriaService(db, current_user.tenant_id)
    return await service.list()


@router.post(
    "/",
    response_model=MateriaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_materia(
    body: MateriaCreate,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = MateriaService(db, current_user.tenant_id)
    return await service.create(body.model_dump())


@router.get("/{id}", response_model=MateriaResponse)
async def get_materia(
    id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = MateriaService(db, current_user.tenant_id)
    return await service.get(id)


@router.put("/{id}", response_model=MateriaResponse)
async def update_materia(
    id: uuid.UUID,
    body: MateriaUpdate,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = MateriaService(db, current_user.tenant_id)
    return await service.update(id, body.model_dump(exclude_none=True))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_materia(
    id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = MateriaService(db, current_user.tenant_id)
    await service.delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

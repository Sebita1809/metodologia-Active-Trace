"""CRUD endpoints for Carrera (academic programs)."""

import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, UserContext
from app.core.permissions import require_permission
from app.schemas.estructura import CarreraCreate, CarreraResponse, CarreraUpdate
from app.services.estructura.carrera_service import CarreraService

router = APIRouter(prefix="/admin/carreras", tags=["admin"])


@router.get("/", response_model=list[CarreraResponse])
async def list_carreras(
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = CarreraService(db, current_user.tenant_id)
    return await service.list()


@router.post(
    "/",
    response_model=CarreraResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_carrera(
    body: CarreraCreate,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = CarreraService(db, current_user.tenant_id)
    return await service.create(body.model_dump())


@router.get("/{id}", response_model=CarreraResponse)
async def get_carrera(
    id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = CarreraService(db, current_user.tenant_id)
    return await service.get(id)


@router.put("/{id}", response_model=CarreraResponse)
async def update_carrera(
    id: uuid.UUID,
    body: CarreraUpdate,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = CarreraService(db, current_user.tenant_id)
    return await service.update(id, body.model_dump(exclude_none=True))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_carrera(
    id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = CarreraService(db, current_user.tenant_id)
    await service.delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

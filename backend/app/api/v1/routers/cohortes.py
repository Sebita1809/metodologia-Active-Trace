"""CRUD endpoints for Cohorte (cohorts within a carrera)."""

import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, UserContext
from app.core.permissions import require_permission
from app.schemas.estructura import CohorteCreate, CohorteResponse, CohorteUpdate
from app.services.estructura.cohorte_service import CohorteService

router = APIRouter(prefix="/admin/cohortes", tags=["admin"])


@router.get("/", response_model=list[CohorteResponse])
async def list_cohortes(
    carrera_id: uuid.UUID | None = None,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = CohorteService(db, current_user.tenant_id)
    return await service.list(carrera_id=carrera_id)


@router.post(
    "/",
    response_model=CohorteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cohorte(
    body: CohorteCreate,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = CohorteService(db, current_user.tenant_id)
    return await service.create(body.model_dump())


@router.get("/{id}", response_model=CohorteResponse)
async def get_cohorte(
    id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = CohorteService(db, current_user.tenant_id)
    return await service.get(id)


@router.put("/{id}", response_model=CohorteResponse)
async def update_cohorte(
    id: uuid.UUID,
    body: CohorteUpdate,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = CohorteService(db, current_user.tenant_id)
    return await service.update(id, body.model_dump(exclude_none=True))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cohorte(
    id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("estructura:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = CohorteService(db, current_user.tenant_id)
    await service.delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

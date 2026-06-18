"""CRUD endpoints for Asignacion (role assignments)."""
import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, UserContext
from app.core.permissions import require_permission
from app.schemas.asignaciones import AsignacionCreate, AsignacionResponse, AsignacionUpdate
from app.services.usuarios.asignacion_service import AsignacionService

router = APIRouter(prefix="/asignaciones", tags=["asignaciones"])


@router.get("/", response_model=list[AsignacionResponse])
async def list_asignaciones(
    usuario_id: uuid.UUID | None = Query(default=None),
    materia_id: uuid.UUID | None = Query(default=None),
    solo_vigentes: bool = Query(default=False),
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("equipos:asignar")),
    db: AsyncSession = Depends(get_db),
):
    service = AsignacionService(db, current_user.tenant_id)
    return await service.list(
        usuario_id=usuario_id,
        materia_id=materia_id,
        solo_vigentes=solo_vigentes,
    )


@router.post("/", response_model=AsignacionResponse, status_code=status.HTTP_201_CREATED)
async def create_asignacion(
    body: AsignacionCreate,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("equipos:asignar")),
    db: AsyncSession = Depends(get_db),
):
    service = AsignacionService(db, current_user.tenant_id)
    return await service.create(body.model_dump())


@router.get("/{id}", response_model=AsignacionResponse)
async def get_asignacion(
    id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("equipos:asignar")),
    db: AsyncSession = Depends(get_db),
):
    service = AsignacionService(db, current_user.tenant_id)
    return await service.get(id)


@router.patch("/{id}", response_model=AsignacionResponse)
async def update_asignacion(
    id: uuid.UUID,
    body: AsignacionUpdate,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("equipos:asignar")),
    db: AsyncSession = Depends(get_db),
):
    service = AsignacionService(db, current_user.tenant_id)
    return await service.update(id, body.model_dump(exclude_none=True))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asignacion(
    id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("equipos:asignar")),
    db: AsyncSession = Depends(get_db),
):
    service = AsignacionService(db, current_user.tenant_id)
    await service.delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

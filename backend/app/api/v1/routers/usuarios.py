"""CRUD endpoints for Usuario (admin user management)."""
import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, UserContext
from app.core.permissions import require_permission
from app.schemas.usuarios import UsuarioCreate, UsuarioResponse, UsuarioUpdate
from app.services.usuarios.usuario_service import UsuarioService

router = APIRouter(prefix="/admin/usuarios", tags=["admin"])


@router.get("/", response_model=list[UsuarioResponse])
async def list_usuarios(
    email: str | None = Query(default=None),
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("usuarios:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = UsuarioService(db, current_user.tenant_id)
    return await service.list(email=email)


@router.post("/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def create_usuario(
    body: UsuarioCreate,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("usuarios:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = UsuarioService(db, current_user.tenant_id)
    return await service.create(body.model_dump())


@router.get("/{id}", response_model=UsuarioResponse)
async def get_usuario(
    id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("usuarios:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = UsuarioService(db, current_user.tenant_id)
    return await service.get(id)


@router.patch("/{id}", response_model=UsuarioResponse)
async def update_usuario(
    id: uuid.UUID,
    body: UsuarioUpdate,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("usuarios:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = UsuarioService(db, current_user.tenant_id)
    return await service.update(id, body.model_dump(exclude_none=True))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_usuario(
    id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("usuarios:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    service = UsuarioService(db, current_user.tenant_id)
    await service.deactivate(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

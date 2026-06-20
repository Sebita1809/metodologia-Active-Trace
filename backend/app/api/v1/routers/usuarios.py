"""
api/v1/routers/usuarios.py — Usuario administration endpoints.

Routes (all under /api/admin/usuarios):
  POST   /       — create usuario (requires usuarios:gestionar)
  GET    /       — list usuarios (open within tenant)
  GET    /{id}   — get usuario (open within tenant)
  PATCH  /{id}   — update usuario (requires usuarios:gestionar)
  DELETE /{id}   — soft-delete usuario (requires usuarios:gestionar), returns 204

No business logic in this router — all delegated to UsuarioService.
email_hash is NEVER returned in responses.

Implemented: C-07 (usuarios-y-asignaciones)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.usuario import UsuarioCreate, UsuarioResponse, UsuarioUpdate
from app.services.usuario_service import UsuarioDecifrado, UsuarioService

router = APIRouter(tags=["usuarios"])

_require_gestionar = require_permission("usuarios:gestionar", scope="global")


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UsuarioService:
    """Build UsuarioService scoped to the authenticated user's tenant."""
    from app.core.config import get_settings  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415

    settings = get_settings()
    crypto = CryptoService(settings.encryption_key)
    return UsuarioService(
        session=session,
        tenant_id=current_user.tenant_id,
        crypto=crypto,
    )


def _to_response(dto: UsuarioDecifrado) -> UsuarioResponse:
    """Convert UsuarioDecifrado to UsuarioResponse (no email_hash)."""
    return UsuarioResponse.model_validate(dto)


@router.post("/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def create_usuario(
    body: UsuarioCreate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: UsuarioService = Depends(_get_svc),
) -> UsuarioResponse:
    try:
        dto = await svc.create(
            nombre=body.nombre,
            apellidos=body.apellidos,
            email=str(body.email),
            dni=body.dni,
            cuil=body.cuil,
            cbu=body.cbu,
            alias_cbu=body.alias_cbu,
            banco=body.banco,
            regional=body.regional,
            legajo=body.legajo,
            legajo_profesional=body.legajo_profesional,
            sexo=body.sexo,
            modalidad_cobro=body.modalidad_cobro,
            facturador=body.facturador,
            estado=body.estado,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _to_response(dto)


@router.get("/", response_model=list[UsuarioResponse])
async def list_usuarios(
    svc: UsuarioService = Depends(_get_svc),
) -> list[UsuarioResponse]:
    dtos = await svc.list()
    return [_to_response(d) for d in dtos]


@router.get("/{usuario_id}", response_model=UsuarioResponse)
async def get_usuario(
    usuario_id: uuid.UUID,
    svc: UsuarioService = Depends(_get_svc),
) -> UsuarioResponse:
    dto = await svc.get(usuario_id)
    if dto is None:
        raise HTTPException(status_code=404, detail="Usuario not found")
    return _to_response(dto)


@router.patch("/{usuario_id}", response_model=UsuarioResponse)
async def update_usuario(
    usuario_id: uuid.UUID,
    body: UsuarioUpdate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: UsuarioService = Depends(_get_svc),
) -> UsuarioResponse:
    try:
        dto = await svc.update(
            usuario_id,
            nombre=body.nombre,
            apellidos=body.apellidos,
            email=str(body.email) if body.email is not None else None,
            dni=body.dni,
            cuil=body.cuil,
            cbu=body.cbu,
            alias_cbu=body.alias_cbu,
            banco=body.banco,
            regional=body.regional,
            legajo=body.legajo,
            legajo_profesional=body.legajo_profesional,
            sexo=body.sexo,
            modalidad_cobro=body.modalidad_cobro,
            facturador=body.facturador,
            estado=body.estado,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if dto is None:
        raise HTTPException(status_code=404, detail="Usuario not found")
    return _to_response(dto)


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_usuario(
    usuario_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: UsuarioService = Depends(_get_svc),
) -> None:
    deleted = await svc.delete(usuario_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Usuario not found")

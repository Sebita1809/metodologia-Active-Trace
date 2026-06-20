"""
api/v1/routers/perfil.py — Self-service profile endpoints.

Routes:
  GET   /api/perfil — read own profile (any authenticated user)
  PATCH /api/perfil — update own editable fields (any authenticated user)

Identity resolved exclusively from JWT via get_current_user.
No business logic in this router — delegated to PerfilService.
email_hash is NEVER returned.

Implemented: C-20 (perfil-y-mensajeria-interna)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.schemas.perfil import PerfilResponse, PerfilUpdate
from app.services.perfil_service import PerfilService
from app.services.usuario_service import UsuarioDecifrado

router = APIRouter(tags=["perfil"])


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PerfilService:
    """Build PerfilService scoped to the authenticated user."""
    from app.core.config import get_settings  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415

    settings = get_settings()
    crypto = CryptoService(settings.encryption_key)
    return PerfilService(
        session=session,
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        crypto=crypto,
    )


def _to_response(dto: UsuarioDecifrado) -> PerfilResponse:
    return PerfilResponse.model_validate(dto)


@router.get("", response_model=PerfilResponse)
async def get_perfil(
    svc: PerfilService = Depends(_get_svc),
) -> PerfilResponse:
    dto = await svc.get_perfil()
    if dto is None:
        raise HTTPException(status_code=404, detail="Perfil not found")
    return _to_response(dto)


@router.patch("", response_model=PerfilResponse)
async def update_perfil(
    body: PerfilUpdate,
    svc: PerfilService = Depends(_get_svc),
) -> PerfilResponse:
    try:
        dto = await svc.update_perfil(
            nombre=body.nombre,
            apellidos=body.apellidos,
            email=str(body.email) if body.email is not None else None,
            sexo=body.sexo,
            banco=body.banco,
            cbu=body.cbu,
            alias_cbu=body.alias_cbu,
            regional=body.regional,
            legajo_profesional=body.legajo_profesional,
            modalidad_cobro=body.modalidad_cobro,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if dto is None:
        raise HTTPException(status_code=404, detail="Perfil not found")
    return _to_response(dto)

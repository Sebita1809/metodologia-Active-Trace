"""Impersonation endpoints — init and end privileged session switching."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_codes import AuditAction
from app.core.dependencies import (
    UserContext,
    get_current_user,
    get_db,
    get_request_metadata,
    require_permission,
)
from app.core.security import create_access_token
from app.models.auth_user import AuthUser
from app.services.audit.audit_service import audit_record

router = APIRouter(prefix="/api/v1/impersonacion", tags=["impersonacion"])


class IniciarRequest(BaseModel):
    """Request to start impersonating another user."""
    model_config = ConfigDict(extra="forbid")
    usuario_id: UUID


class IniciarResponse(BaseModel):
    """Response with impersonation JWT."""
    model_config = ConfigDict(extra="forbid")
    access_token: str
    token_type: str = "bearer"
    impersonated_user_id: UUID
    impersonating: bool = True


class FinalizarResponse(BaseModel):
    """Response after ending impersonation — normal JWT."""
    model_config = ConfigDict(extra="forbid")
    access_token: str
    token_type: str = "bearer"
    impersonating: bool = False


@router.post("/iniciar", response_model=IniciarResponse)
async def impersonacion_iniciar(
    body: IniciarRequest,
    request: Request,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("impersonacion:usar")),
    db: AsyncSession = Depends(get_db),
    metadata = Depends(get_request_metadata),
):
    """Start impersonating another user in the same tenant.

    Only users with impersonacion:usar permission can impersonate.
    The impersonation session is clearly distinguishable from a normal session.
    All actions during impersonation are attributed to the original actor.
    """
    result = await db.execute(
        select(AuthUser).where(
            AuthUser.id == body.usuario_id,
            AuthUser.tenant_id == current_user.tenant_id,
            AuthUser.deleted_at.is_(None),
        )
    )
    target_user = result.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado en el tenant actual",
        )

    impersonation_token = create_access_token(
        user_id=str(body.usuario_id),
        tenant_id=str(current_user.tenant_id),
        roles=current_user.roles,
        impersonated_user_id=str(body.usuario_id),
        actor_id=str(current_user.user_id),
    )

    await audit_record(
        db=db,
        actor_id=current_user.user_id,
        accion=AuditAction.IMPERSONACION_INICIAR,
        tenant_id=current_user.tenant_id,
        impersonado_id=body.usuario_id,
        ip=metadata.ip,
        user_agent=metadata.user_agent,
    )

    return IniciarResponse(
        access_token=impersonation_token,
        impersonated_user_id=body.usuario_id,
    )


@router.post("/finalizar", response_model=FinalizarResponse)
async def impersonacion_finalizar(
    request: Request,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    metadata = Depends(get_request_metadata),
):
    """End impersonation session and return to normal access.

    Requires an active impersonation session (JWT type=impersonation).
    Creates a new standard access token for the real user (actor).
    """
    if not current_user.is_impersonating:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay una sesión de impersonación activa",
        )

    real_user_id = current_user.actor_id
    if real_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Estado de impersonación inválido",
        )

    normal_token = create_access_token(
        user_id=str(real_user_id),
        tenant_id=str(current_user.tenant_id),
        roles=current_user.roles,
    )

    await audit_record(
        db=db,
        actor_id=real_user_id,
        accion=AuditAction.IMPERSONACION_FINALIZAR,
        tenant_id=current_user.tenant_id,
        impersonado_id=current_user.impersonated_user_id,
        ip=metadata.ip,
        user_agent=metadata.user_agent,
    )

    return FinalizarResponse(access_token=normal_token)

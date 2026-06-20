"""
api/v1/routers/impersonacion.py — Impersonation session endpoints.

Routes:
  POST /api/impersonacion/iniciar    — start an impersonation session
  POST /api/impersonacion/finalizar  — end the current impersonation session

Both endpoints require impersonacion:usar permission.
The identity of the actor is ALWAYS taken from the JWT (get_current_user).

Design (D-06): actor in JWT sub, impersonated user in 'impersonando' claim.
Fail-closed: missing impersonacion:usar → 403 (via require_permission).

Implemented: C-05 (audit-log)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.services.impersonation_service import ImpersonationService

router = APIRouter(tags=["impersonacion"])

_require_impersonar = require_permission("impersonacion:usar", scope="global")


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class IniciarImpersonacionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usuario_id: uuid.UUID


class ImpersonacionTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: str = "bearer"


class FinalizarImpersonacionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mensaje: str = "Impersonation session ended"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ImpersonationService:
    return ImpersonationService(session=session, tenant_id=current_user.tenant_id)


def _get_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/iniciar", response_model=ImpersonacionTokenResponse)
async def iniciar_impersonacion(
    body: IniciarImpersonacionRequest,
    request: Request,
    _perm: PermisoConcedido = Depends(_require_impersonar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ImpersonationService = Depends(_get_svc),
) -> ImpersonacionTokenResponse:
    """Start an impersonation session.

    Requires impersonacion:usar. The emitted token's 'sub' is the real actor;
    'impersonando' claim identifies the impersonated user.
    """
    token = await svc.iniciar_impersonacion(
        current_user=current_user,
        usuario_id=body.usuario_id,
        ip=_get_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return ImpersonacionTokenResponse(access_token=token)


@router.post("/finalizar", response_model=FinalizarImpersonacionResponse)
async def finalizar_impersonacion(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FinalizarImpersonacionResponse:
    """End the current impersonation session.

    Can be called with any valid access token (impersonation or normal session).
    If the token carries an 'impersonando' claim, the FINALIZAR audit record
    is written with actor_id=real actor, impersonado_id=impersonated user.
    """
    svc = ImpersonationService(session=session, tenant_id=current_user.tenant_id)
    await svc.finalizar_impersonacion(
        current_user=current_user,
        ip=_get_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return FinalizarImpersonacionResponse()

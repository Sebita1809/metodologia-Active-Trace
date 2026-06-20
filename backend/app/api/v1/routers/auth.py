"""
api/v1/routers/auth.py — Authentication endpoints.

Routes:
  POST /api/auth/login            — credential login (rate-limited 5/min)
  POST /api/auth/refresh          — rotate refresh token
  POST /api/auth/logout           — revoke refresh token
  POST /api/auth/forgot           — initiate password recovery
  POST /api/auth/reset            — complete password recovery
  POST /api/auth/2fa/enroll       — begin TOTP enrollment (requires auth)
  POST /api/auth/2fa/verify       — confirm TOTP enrollment (requires auth)
  POST /api/auth/2fa/login-verify — complete 2FA gate with partial_token

Implemented: C-03 (auth-jwt-2fa)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import AuthenticationError, InvalidTokenError, TotpError
from app.core.rate_limiter import limiter
from app.features.auth.dependencies import get_auth_service
from app.features.auth.schemas import (
    ForgotRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    PartialTokenResponse,
    RefreshRequest,
    ResetRequest,
    TotpEnrollResponse,
    TotpLoginVerifyRequest,
    TotpVerifyRequest,
    TokenResponse,
)
from app.features.auth.service import AuthService

router = APIRouter()


@router.get("/tenant/{slug}", response_model=dict)
async def resolve_tenant(slug: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Public endpoint — resolve a tenant slug to its UUID.

    Used by the frontend login form to obtain the X-Tenant-ID before authentication.
    Returns 404 if the slug does not exist or the tenant is inactive.
    """
    from sqlalchemy import select, text  # noqa: PLC0415
    from app.models.tenant import Tenant  # noqa: PLC0415
    result = await db.execute(
        text("SELECT id, nombre FROM tenants WHERE slug = :slug AND activo = true AND deleted_at IS NULL"),
        {"slug": slug},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Institución no encontrada")
    return {"id": str(row[0]), "nombre": row[1]}


@router.post(
    "/login",
    response_model=TokenResponse | PartialTokenResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    svc: AuthService = Depends(get_auth_service),
) -> TokenResponse | PartialTokenResponse:
    try:
        return await svc.login(
            email=body.email,
            password=body.password,
            tenant_id=request.state.tenant_id if hasattr(request.state, "tenant_id") else _extract_tenant_from_host(request),
        )
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid credentials")


def _extract_tenant_from_host(request: Request):
    """Placeholder tenant resolver — C-02 tenancy middleware will provide this properly.

    For now, returns None which causes get_by_email to fail gracefully.
    C-04 / C-08 will wire the proper tenant resolver.
    """
    import uuid  # noqa: PLC0415
    raw = request.headers.get("X-Tenant-ID")
    if raw:
        try:
            return uuid.UUID(raw)
        except ValueError:
            pass
    raise HTTPException(status_code=400, detail="X-Tenant-ID header required")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        return await svc.refresh(
            raw_token=body.refresh_token,
            tenant_id=_extract_tenant_from_host(request),
        )
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(
    body: LogoutRequest,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    if body.refresh_token:
        await svc.logout(
            raw_token=body.refresh_token,
            tenant_id=_extract_tenant_from_host(request),
        )
    return MessageResponse(message="Logged out successfully")


@router.post("/forgot", response_model=MessageResponse)
async def forgot_password(
    body: ForgotRequest,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await svc.forgot_password(
        email=body.email,
        tenant_id=_extract_tenant_from_host(request),
    )
    return MessageResponse(message="If the email exists, a reset link has been sent")


@router.post("/reset", response_model=MessageResponse)
async def reset_password(
    body: ResetRequest,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    try:
        await svc.reset_password(
            raw_token=body.token,
            new_password=body.new_password,
            tenant_id=_extract_tenant_from_host(request),
        )
    except InvalidTokenError:
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")
    return MessageResponse(message="Password updated successfully")


@router.post("/2fa/enroll", response_model=TotpEnrollResponse)
async def enroll_2fa(
    request: Request,
    svc: AuthService = Depends(get_auth_service),
    current_user: CurrentUser = Depends(get_current_user),
) -> TotpEnrollResponse:
    return await svc.enroll_2fa(
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        email=request.headers.get("X-User-Email", ""),
    )


@router.post("/2fa/verify", response_model=MessageResponse)
async def verify_2fa(
    body: TotpVerifyRequest,
    svc: AuthService = Depends(get_auth_service),
    current_user: CurrentUser = Depends(get_current_user),
) -> MessageResponse:
    try:
        await svc.confirm_2fa(
            user_id=current_user.user_id,
            tenant_id=current_user.tenant_id,
            code=body.code,
        )
    except TotpError:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    return MessageResponse(message="2FA enabled successfully")


@router.post("/2fa/login-verify", response_model=TokenResponse)
async def login_verify_2fa(
    body: TotpLoginVerifyRequest,
    svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        return await svc.verify_2fa_gate(
            partial_token=body.partial_token,
            code=body.code,
        )
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid token or TOTP code")

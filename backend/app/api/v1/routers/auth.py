"""Auth router — login, refresh, logout, 2FA, recovery endpoints."""

import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.core.rate_limiter import rate_limit_login
from app.core.security import create_temp_session_token, verify_token
from app.models.auth_user import AuthUser
from app.schemas.auth import (
    EnrollResponse,
    ForgotRequest,
    ForgotResponse,
    LoginRequest,
    LoginResponse,
    Login2FARequiredResponse,
    RefreshRequest,
    RefreshResponse,
    LogoutRequest,
    ResetRequest,
    Verify2FARequest,
)
from app.services.auth.auth_service import AuthService
from app.services.auth.recovery_service import RecoveryService
from app.services.auth.totp_service import TOTPService

# Placeholder tenant used during login — authenticate() resolves
# the real tenant_id from the user record and overrides it.
_LOGIN_PLACEHOLDER_TENANT = uuid.UUID("00000000-0000-0000-0000-000000000000")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse | Login2FARequiredResponse,
    summary="Authenticate user and return tokens or 2FA challenge",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_login),
) -> LoginResponse | Login2FARequiredResponse:
    auth_service = AuthService(db, _LOGIN_PLACEHOLDER_TENANT)
    user = await auth_service.authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.totp_enabled:
        session_token = create_temp_session_token(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            email=user.email,
        )
        return Login2FARequiredResponse(session_token=session_token)

    access_token, refresh_token_str, _ = await auth_service.create_session(user)
    return LoginResponse(access_token=access_token, refresh_token=refresh_token_str)


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Rotate refresh token and return new access+refresh pair",
)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    auth_service = AuthService(db, _LOGIN_PLACEHOLDER_TENANT)
    try:
        access_token, new_refresh_token, _ = await auth_service.refresh_session(
            body.refresh_token
        )
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
        if "reuse" in exc.detail.lower():
            raise HTTPException(
                status_code=401,
                detail="Session revoked — re-authentication required",
            )
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return RefreshResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.post(
    "/logout",
    summary="Revoke refresh token and terminate session",
)
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    auth_service = AuthService(db, _LOGIN_PLACEHOLDER_TENANT)
    success = await auth_service.revoke_session(body.refresh_token)
    if not success:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return {"detail": "Logged out successfully"}


@router.post(
    "/forgot",
    response_model=ForgotResponse,
    summary="Request password recovery token",
)
async def forgot(
    body: ForgotRequest,
    db: AsyncSession = Depends(get_db),
) -> ForgotResponse:
    recovery_service = RecoveryService(db, _LOGIN_PLACEHOLDER_TENANT)
    token = await recovery_service.create_recovery_token(body.email)
    return ForgotResponse(
        message="If the email exists, a recovery link has been sent",
        token=token,
    )


@router.post(
    "/reset",
    summary="Reset password with recovery token",
)
async def reset(
    body: ResetRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    recovery_service = RecoveryService(db, _LOGIN_PLACEHOLDER_TENANT)
    success = await recovery_service.verify_reset(body.token, body.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired recovery token")
    return {"detail": "Password reset successfully"}


@router.post(
    "/2fa/enroll",
    response_model=EnrollResponse,
    summary="Enroll in 2FA TOTP — generate secret and provisioning URI",
)
async def enroll_2fa(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EnrollResponse:
    totp_service = TOTPService(db)
    uri, secret = await totp_service.generate_secret(
        user_id=current_user.user_id,
        email=current_user.email,
    )
    return EnrollResponse(uri=uri, secret=secret)


@router.post(
    "/2fa/verify",
    response_model=LoginResponse,
    summary="Verify a 2FA TOTP code and complete login",
)
async def verify_2fa(
    body: Verify2FARequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    payload = verify_token(body.session_token)
    user_id = UUID(payload["sub"])
    tenant_id = UUID(payload["tenant_id"])

    totp_service = TOTPService(db)
    valid = await totp_service.verify_code(user_id, body.code)
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    stmt = select(AuthUser).where(
        AuthUser.id == user_id,
        AuthUser.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    auth_service = AuthService(db, tenant_id)
    access_token, refresh_token_str, _ = await auth_service.create_session(user)
    return LoginResponse(access_token=access_token, refresh_token=refresh_token_str)

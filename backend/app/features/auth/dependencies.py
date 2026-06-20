"""
app/features/auth/dependencies.py — FastAPI dependency for AuthService.

Implemented: C-03 (auth-jwt-2fa)
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import CryptoService
from app.core.dependencies import get_db
from app.features.auth.service import AuthService


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Build an AuthService bound to the current request session."""
    settings = get_settings()
    return AuthService(
        session=db,
        crypto=CryptoService(settings.encryption_key),
        secret_key=settings.secret_key,
        access_token_expire_minutes=settings.access_token_expire_minutes,
    )

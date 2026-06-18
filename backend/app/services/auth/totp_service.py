"""TOTP service — 2FA enrollment and code verification."""

from uuid import UUID

import pyotp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import AESCipher
from app.models.auth_user import AuthUser


class TOTPService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_secret(self, user_id: UUID, email: str) -> tuple[str, str]:
        secret = pyotp.random_base32()
        uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name=get_settings().TOTP_ISSUER,
        )
        encrypted_secret = AESCipher.encrypt(secret)

        stmt = select(AuthUser).where(AuthUser.id == user_id, AuthUser.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        user.totp_secret = encrypted_secret
        user.totp_enabled = False
        await self.db.commit()

        return uri, secret

    async def verify_code(self, user_id: UUID, code: str) -> bool:
        stmt = select(AuthUser).where(AuthUser.id == user_id, AuthUser.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None or user.totp_secret is None:
            return False

        secret = AESCipher.decrypt(user.totp_secret)
        valid = pyotp.TOTP(secret).verify(code, valid_window=1)

        if valid and not user.totp_enabled:
            user.totp_enabled = True
            await self.db.commit()

        return valid

    async def is_totp_enabled(self, user_id: UUID) -> bool:
        stmt = select(AuthUser).where(AuthUser.id == user_id, AuthUser.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        return user is not None and user.totp_enabled

"""RecoveryService — password recovery token generation and reset."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.auth_user import AuthUser
from app.models.password_recovery_token import PasswordRecoveryToken


class RecoveryService:
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.ph = PasswordHasher()

    async def create_recovery_token(self, email: str) -> str | None:
        # Find user by email across all tenants — no tenant filter.
        stmt = (
            select(AuthUser)
            .where(
                AuthUser.email == email,
                AuthUser.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return None

        token = str(uuid4())
        token_hash = sha256(token.encode()).hexdigest()
        expires_at = datetime.now(tz=timezone.utc) + timedelta(
            minutes=get_settings().RECOVERY_TOKEN_EXPIRE_MINUTES
        )

        recovery_token = PasswordRecoveryToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            used_at=None,
        )
        self.db.add(recovery_token)
        await self.db.commit()

        return token

    async def verify_reset(self, token_str: str, new_password: str) -> bool:
        token_hash = sha256(token_str.encode()).hexdigest()
        stmt = select(PasswordRecoveryToken).where(
            PasswordRecoveryToken.token_hash == token_hash,
        )
        result = await self.db.execute(stmt)
        recovery_token = result.scalar_one_or_none()
        if recovery_token is None:
            return False
        if recovery_token.used_at is not None:
            return False
        if recovery_token.expires_at < datetime.now(tz=timezone.utc):
            return False

        stmt = (
            select(AuthUser)
            .where(
                AuthUser.id == recovery_token.user_id,
                AuthUser.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return False

        user.password_hash = self.ph.hash(new_password)
        recovery_token.used_at = datetime.now(tz=timezone.utc)
        await self.db.commit()
        return True

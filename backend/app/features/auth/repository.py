"""
app/features/auth/repository.py — Auth session repositories.

These repositories do NOT extend BaseRepository[T] because the auth token
models inherit from Base directly (not BaseTenantModel).  Tenant isolation is
enforced explicitly on every query here — never omit the tenant_id filter.

Implemented: C-03 (auth-jwt-2fa)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import PasswordResetToken, RefreshToken, TotpSecret


class RefreshTokenRepository:
    """Manages refresh token lifecycle for one tenant."""

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        rt = RefreshToken(
            user_id=user_id,
            tenant_id=self._tenant_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(rt)
        await self._session.flush()
        await self._session.refresh(rt)
        return rt

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Return the active (non-revoked) token matching hash, scoped to this tenant."""
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.tenant_id == self._tenant_id)
            .where(RefreshToken.token_hash == token_hash)
            .where(RefreshToken.revoked_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_any_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Return the token regardless of revoked status — used to detect token reuse."""
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.tenant_id == self._tenant_id)
            .where(RefreshToken.token_hash == token_hash)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token_hash: str) -> None:
        """Set revoked_at on the matching active token for this tenant."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.tenant_id == self._tenant_id)
            .where(RefreshToken.token_hash == token_hash)
            .where(RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(tz=timezone.utc))
        )
        await self._session.execute(stmt)

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke every active refresh token belonging to user_id within this tenant."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.tenant_id == self._tenant_id)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(tz=timezone.utc))
        )
        await self._session.execute(stmt)


class PasswordResetTokenRepository:
    """Manages single-use password reset tokens for one tenant."""

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        prt = PasswordResetToken(
            user_id=user_id,
            tenant_id=self._tenant_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(prt)
        await self._session.flush()
        await self._session.refresh(prt)
        return prt

    async def get_valid_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        """Return token if it exists, belongs to this tenant, is unused, and not expired."""
        now = datetime.now(tz=timezone.utc)
        stmt = (
            select(PasswordResetToken)
            .where(PasswordResetToken.tenant_id == self._tenant_id)
            .where(PasswordResetToken.token_hash == token_hash)
            .where(PasswordResetToken.used_at.is_(None))
            .where(PasswordResetToken.expires_at > now)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_used(self, token_hash: str) -> None:
        """Mark the token as used so it cannot be reused."""
        stmt = (
            update(PasswordResetToken)
            .where(PasswordResetToken.tenant_id == self._tenant_id)
            .where(PasswordResetToken.token_hash == token_hash)
            .where(PasswordResetToken.used_at.is_(None))
            .values(used_at=datetime.now(tz=timezone.utc))
        )
        await self._session.execute(stmt)

    async def invalidate_previous_for_user(self, user_id: uuid.UUID) -> None:
        """Mark all outstanding reset tokens for user_id as used (only one valid at a time)."""
        stmt = (
            update(PasswordResetToken)
            .where(PasswordResetToken.tenant_id == self._tenant_id)
            .where(PasswordResetToken.user_id == user_id)
            .where(PasswordResetToken.used_at.is_(None))
            .values(used_at=datetime.now(tz=timezone.utc))
        )
        await self._session.execute(stmt)


class TotpSecretRepository:
    """Manages TOTP enrollment secrets for one tenant."""

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def create_pending(
        self,
        *,
        user_id: uuid.UUID,
        encrypted_secret: str,
    ) -> TotpSecret:
        """Create an unconfirmed TOTP secret (enrollment in progress)."""
        ts = TotpSecret(
            user_id=user_id,
            tenant_id=self._tenant_id,
            encrypted_secret=encrypted_secret,
            confirmed=False,
        )
        self._session.add(ts)
        await self._session.flush()
        await self._session.refresh(ts)
        return ts

    async def get_for_user(self, user_id: uuid.UUID) -> TotpSecret | None:
        """Return the confirmed (active) TOTP secret for user_id, or None."""
        stmt = (
            select(TotpSecret)
            .where(TotpSecret.tenant_id == self._tenant_id)
            .where(TotpSecret.user_id == user_id)
            .where(TotpSecret.confirmed.is_(True))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def confirm(self, secret_id: uuid.UUID) -> None:
        """Flip confirmed=True to activate 2FA for the user."""
        stmt = (
            update(TotpSecret)
            .where(TotpSecret.tenant_id == self._tenant_id)
            .where(TotpSecret.id == secret_id)
            .values(confirmed=True)
        )
        await self._session.execute(stmt)

    async def get_pending_for_user(self, user_id: uuid.UUID) -> TotpSecret | None:
        """Return the unconfirmed TOTP secret for user_id, or None."""
        stmt = (
            select(TotpSecret)
            .where(TotpSecret.tenant_id == self._tenant_id)
            .where(TotpSecret.user_id == user_id)
            .where(TotpSecret.confirmed.is_(False))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

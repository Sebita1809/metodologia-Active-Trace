"""RefreshToken repository — token rotation tracking and family invalidation."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        super().__init__(db, tenant_id, RefreshToken)

    async def create(self, token_data: dict) -> RefreshToken:
        return await super().create(token_data)

    async def get_by_token_hash(
        self, token_hash: str, *, tenant_scope: bool = False
    ) -> RefreshToken | None:
        """Look up a refresh token by its hash.

        By default (**tenant_scope=False**) the lookup is
        tenant-agnostic — the token_hash is globally unique.
        Set **tenant_scope=True** to restrict to the repo's tenant.
        """
        stmt = select(self.model).where(
            self.model.deleted_at.is_(None),
            self.model.token_hash == token_hash,
        )
        if tenant_scope:
            stmt = stmt.where(self.model.tenant_id == self.tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token_id: UUID, replaced_by: UUID | None = None) -> None:
        token = await self.get(token_id)
        if token is None:
            return
        token.revoked_at = datetime.now(tz=timezone.utc)
        if replaced_by is not None:
            token.replaced_by = replaced_by
        await self.db.commit()

    async def list_active_by_user_id(self, user_id: UUID) -> list[RefreshToken]:
        now = datetime.now(tz=timezone.utc)
        stmt = (
            select(self.model)
            .where(
                self.model.tenant_id == self.tenant_id,
                self.model.deleted_at.is_(None),
                self.model.user_id == user_id,
                self.model.revoked_at.is_(None),
                self.model.expires_at > now,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        active = await self.list_active_by_user_id(user_id)
        now = datetime.now(tz=timezone.utc)
        for token in active:
            token.revoked_at = now
        await self.db.commit()

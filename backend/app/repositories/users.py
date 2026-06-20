"""
app/repositories/users.py — User repository.

Extends BaseRepository[User] with auth-specific lookups.
C-07 (usuarios-y-asignaciones) will add profile-related methods.

Implemented: C-03 (auth-jwt-2fa)
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=User, session=session, tenant_id=tenant_id)

    async def get_by_email(self, email: str) -> User | None:
        """Return the active user with *email* in this tenant, or None."""
        stmt = (
            self._base_query()
            .where(User.email == email)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_password(self, user_id: uuid.UUID, new_hash: str) -> None:
        """Update password_hash for *user_id* within this tenant."""
        await self.update(user_id, password_hash=new_hash)

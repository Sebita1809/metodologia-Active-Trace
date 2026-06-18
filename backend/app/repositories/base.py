"""Generic repository with automatic tenant scoping.

Every query includes tenant_id and deleted_at IS NULL filters automatically.
Use get_by_id_without_tenant() only for controlled administrative operations.
"""

import uuid
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.base import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseRepository(Generic[ModelT]):
    """Repository with tenant-scoped CRUD operations."""

    def __init__(self, db: AsyncSession, tenant_id: UUID, model: type[ModelT]):
        self.db = db
        self.tenant_id = tenant_id
        self.model = model

    async def create(self, data: dict) -> ModelT:
        entity = self.model(**data, tenant_id=self.tenant_id)
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def get(
        self, id: UUID, *, include_deleted: bool = False
    ) -> ModelT | None:
        stmt = select(self.model).where(
            self.model.id == id,
            self.model.tenant_id == self.tenant_id,
        )
        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, **filters) -> list[ModelT]:
        stmt = select(self.model).where(
            self.model.tenant_id == self.tenant_id,
            self.model.deleted_at.is_(None),
        )
        for key, value in filters.items():
            column = getattr(self.model, key, None)
            if column is not None:
                stmt = stmt.where(column == value)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, id: UUID, data: dict) -> ModelT | None:
        entity = await self.get(id)
        if entity is None:
            return None
        for key, value in data.items():
            setattr(entity, key, value)
        entity.updated_at = func.now()
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> bool:
        entity = await self.get(id)
        if entity is None:
            return False
        entity.deleted_at = func.now()
        await self.db.commit()
        return True

    async def get_by_id_without_tenant(self, id: UUID) -> ModelT | None:
        """Bypass tenant scope — use ONLY for admin operations."""
        stmt = select(self.model).where(
            self.model.id == id,
            self.model.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

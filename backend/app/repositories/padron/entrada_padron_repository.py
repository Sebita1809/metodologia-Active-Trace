"""Repository for EntradaPadron entities."""
from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.entrada_padron import EntradaPadron
from app.repositories.base import BaseRepository


class EntradaPadronRepository(BaseRepository[EntradaPadron]):
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        super().__init__(db, tenant_id, EntradaPadron)

    async def bulk_create(self, entradas: list[dict]) -> list[EntradaPadron]:
        """Create multiple EntradaPadron entries in one transaction."""
        entities = []
        for data in entradas:
            entity = EntradaPadron(**data, tenant_id=self.tenant_id)
            self.db.add(entity)
            entities.append(entity)
        await self.db.flush()
        for e in entities:
            await self.db.refresh(e)
        await self.db.commit()
        return entities

    async def get_by_version(self, version_id: UUID) -> list[EntradaPadron]:
        stmt = select(EntradaPadron).where(
            EntradaPadron.tenant_id == self.tenant_id,
            EntradaPadron.version_id == version_id,
            EntradaPadron.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def hard_delete_by_version(self, version_id: UUID) -> int:
        """Hard delete all entries for a given version."""
        stmt = select(EntradaPadron).where(
            EntradaPadron.tenant_id == self.tenant_id,
            EntradaPadron.version_id == version_id,
        )
        result = await self.db.execute(stmt)
        entries = list(result.scalars().all())
        count = len(entries)
        for e in entries:
            await self.db.delete(e)
        await self.db.commit()
        return count

    async def count_by_version(self, version_id: UUID) -> int:
        stmt = select(func.count()).select_from(EntradaPadron).where(
            EntradaPadron.tenant_id == self.tenant_id,
            EntradaPadron.version_id == version_id,
            EntradaPadron.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

"""Repository for VersionPadron entities."""
from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.version_padron import VersionPadron
from app.repositories.base import BaseRepository


class VersionPadronRepository(BaseRepository[VersionPadron]):
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        super().__init__(db, tenant_id, VersionPadron)

    async def get_active_by_materia_cohorte(
        self, materia_id: UUID, cohorte_id: UUID
    ) -> VersionPadron | None:
        stmt = select(VersionPadron).where(
            VersionPadron.tenant_id == self.tenant_id,
            VersionPadron.materia_id == materia_id,
            VersionPadron.cohorte_id == cohorte_id,
            VersionPadron.activa.is_(True),
            VersionPadron.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_materia_cohorte(
        self, materia_id: UUID, cohorte_id: UUID
    ) -> list[VersionPadron]:
        stmt = (
            select(VersionPadron)
            .where(
                VersionPadron.tenant_id == self.tenant_id,
                VersionPadron.materia_id == materia_id,
                VersionPadron.cohorte_id == cohorte_id,
                VersionPadron.deleted_at.is_(None),
            )
            .order_by(VersionPadron.cargado_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def deactivate_previous_active(
        self, materia_id: UUID, cohorte_id: UUID
    ) -> None:
        """Deactivate the currently active version for a materia+cohorte."""
        active = await self.get_active_by_materia_cohorte(materia_id, cohorte_id)
        if active is not None:
            active.activa = False
            active.updated_at = func.now()
            await self.db.flush()

    async def hard_delete_by_materia_cohorte(
        self, materia_id: UUID, cohorte_id: UUID
    ) -> int:
        """Hard delete all version_padron rows for a materia+cohorte (for clear subject data)."""
        stmt = select(VersionPadron).where(
            VersionPadron.tenant_id == self.tenant_id,
            VersionPadron.materia_id == materia_id,
            VersionPadron.cohorte_id == cohorte_id,
        )
        result = await self.db.execute(stmt)
        versions = list(result.scalars().all())
        count = len(versions)
        for v in versions:
            await self.db.delete(v)
        await self.db.commit()
        return count

    async def activate(self, version_id: UUID) -> VersionPadron | None:
        """Set activa=True for a specific version."""
        entity = await self.get(version_id)
        if entity is None:
            return None
        entity.activa = True
        entity.updated_at = func.now()
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

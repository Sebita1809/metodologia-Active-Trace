"""Repository for UmbralMateria CRUD."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.umbral_materia import UmbralMateria
from app.repositories.base import BaseRepository


class UmbralMateriaRepository(BaseRepository[UmbralMateria]):
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(db, tenant_id, UmbralMateria)

    async def create_default(
        self, asignacion_id: uuid.UUID, materia_id: uuid.UUID
    ) -> UmbralMateria:
        return await self.create({
            "asignacion_id": asignacion_id,
            "materia_id": materia_id,
            "umbral_pct": 60,
        })

    async def get_by_asignacion(
        self, asignacion_id: uuid.UUID
    ) -> UmbralMateria | None:
        stmt = select(self.model).where(
            self.model.tenant_id == self.tenant_id,
            self.model.asignacion_id == asignacion_id,
            self.model.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_config(
        self, umbral_id: uuid.UUID, data: dict
    ) -> UmbralMateria | None:
        return await self.update(umbral_id, data)

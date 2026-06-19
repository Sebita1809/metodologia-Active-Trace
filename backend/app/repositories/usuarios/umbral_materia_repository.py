"""Repository for UmbralMateria CRUD."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.umbral_materia import UmbralMateria
from app.repositories.base import BaseRepository


class UmbralMateriaRepository(BaseRepository[UmbralMateria]):
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(db, tenant_id, UmbralMateria)

    async def create_default(self, asignacion_id: uuid.UUID, materia_id: uuid.UUID) -> UmbralMateria:
        return await self.create({
            "asignacion_id": asignacion_id,
            "materia_id": materia_id,
            "umbral_pct": 60,
        })

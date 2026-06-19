"""Repository for Calificacion CRUD."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.calificacion import Calificacion
from app.repositories.base import BaseRepository


class CalificacionRepository(BaseRepository[Calificacion]):
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(db, tenant_id, Calificacion)

    async def list_by_materia_cohorte(
        self, materia_id: uuid.UUID, entrada_ids: list[uuid.UUID]
    ) -> list[Calificacion]:
        stmt = select(self.model).where(
            self.model.tenant_id == self.tenant_id,
            self.model.materia_id == materia_id,
            self.model.entrada_padron_id.in_(entrada_ids),
            self.model.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def hard_delete_by_materia(
        self, materia_id: uuid.UUID, entrada_ids: list[uuid.UUID]
    ) -> None:
        """Permanently delete all calificaciones for a materia (F1.5)."""
        stmt = select(self.model).where(
            self.model.tenant_id == self.tenant_id,
            self.model.materia_id == materia_id,
            self.model.entrada_padron_id.in_(entrada_ids),
        )
        result = await self.db.execute(stmt)
        entities = list(result.scalars().all())
        for entity in entities:
            await self.db.delete(entity)
        await self.db.commit()

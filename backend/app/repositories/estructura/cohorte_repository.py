"""Repository for Cohorte CRUD with tenant scope."""
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.cohorte import Cohorte
from app.repositories.base import BaseRepository


class CohorteRepository(BaseRepository[Cohorte]):
    """Cohorte CRUD with tenant scope."""

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        super().__init__(db, tenant_id, Cohorte)

    async def list_activas_por_carrera(self, carrera_id: UUID) -> list[Cohorte]:
        """Return active cohorts for a given carrera (within tenant scope)."""
        stmt = select(self.model).where(
            self.model.carrera_id == carrera_id,
            self.model.tenant_id == self.tenant_id,
            self.model.deleted_at.is_(None),
            self.model.estado == "Activa",
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_activas_por_carrera(self, carrera_id: UUID) -> int:
        """Count active cohorts for a given carrera."""
        cohorts = await self.list_activas_por_carrera(carrera_id)
        return len(cohorts)

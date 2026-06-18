"""Repository for Materia CRUD with tenant scope."""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.materia import Materia
from app.repositories.base import BaseRepository


class MateriaRepository(BaseRepository[Materia]):
    """Materia CRUD with tenant scope."""

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        super().__init__(db, tenant_id, Materia)

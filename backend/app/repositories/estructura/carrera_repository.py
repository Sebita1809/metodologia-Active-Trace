"""Repository for Carrera CRUD with tenant scope."""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.carrera import Carrera
from app.repositories.base import BaseRepository


class CarreraRepository(BaseRepository[Carrera]):
    """Carrera CRUD with tenant scope."""

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        super().__init__(db, tenant_id, Carrera)

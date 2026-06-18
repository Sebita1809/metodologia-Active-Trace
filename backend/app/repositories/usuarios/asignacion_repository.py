"""Repository for Asignacion CRUD with tenant scope."""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.asignacion import Asignacion
from app.repositories.base import BaseRepository


class AsignacionRepository(BaseRepository[Asignacion]):
    """Asignacion CRUD with tenant scope and filtered queries."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(db, tenant_id, Asignacion)

    async def list_by_usuario(self, usuario_id: uuid.UUID) -> list[Asignacion]:
        """List all non-deleted asignaciones for a user in the tenant."""
        stmt = select(Asignacion).where(
            Asignacion.tenant_id == self.tenant_id,
            Asignacion.usuario_id == usuario_id,
            Asignacion.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_materia(self, materia_id: uuid.UUID) -> list[Asignacion]:
        """List all non-deleted asignaciones for a subject in the tenant."""
        stmt = select(Asignacion).where(
            Asignacion.tenant_id == self.tenant_id,
            Asignacion.materia_id == materia_id,
            Asignacion.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_vigentes(self, fecha: date | None = None) -> list[Asignacion]:
        """List vigentes asignaciones: desde <= fecha and (hasta is null or hasta >= fecha)."""
        if fecha is None:
            fecha = datetime.now(timezone.utc).date()
        stmt = select(Asignacion).where(
            Asignacion.tenant_id == self.tenant_id,
            Asignacion.deleted_at.is_(None),
            Asignacion.desde <= fecha,
            (Asignacion.hasta.is_(None)) | (Asignacion.hasta >= fecha),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_vigentes_por_usuario(
        self, usuario_id: uuid.UUID, fecha: date | None = None
    ) -> list[Asignacion]:
        """List vigentes asignaciones for a specific user."""
        if fecha is None:
            fecha = datetime.now(timezone.utc).date()
        stmt = select(Asignacion).where(
            Asignacion.tenant_id == self.tenant_id,
            Asignacion.usuario_id == usuario_id,
            Asignacion.deleted_at.is_(None),
            Asignacion.desde <= fecha,
            (Asignacion.hasta.is_(None)) | (Asignacion.hasta >= fecha),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_activas_por_materia(self, materia_id: uuid.UUID) -> int:
        """Count vigentes asignaciones for a subject."""
        stmt = select(Asignacion.id).where(
            Asignacion.tenant_id == self.tenant_id,
            Asignacion.materia_id == materia_id,
            Asignacion.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return len(result.scalars().all())

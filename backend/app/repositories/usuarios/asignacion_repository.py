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

    async def list_vigentes_por_materia_y_cohorte(
        self, materia_id: uuid.UUID, cohorte_id: uuid.UUID | None = None
    ) -> list[Asignacion]:
        """List vigentes assignments filtered by materia, optionally cohorte."""
        fecha = datetime.now(timezone.utc).date()
        stmt = select(Asignacion).where(
            Asignacion.tenant_id == self.tenant_id,
            Asignacion.deleted_at.is_(None),
            Asignacion.materia_id == materia_id,
            Asignacion.desde <= fecha,
            (Asignacion.hasta.is_(None)) | (Asignacion.hasta >= fecha),
        )
        if cohorte_id is not None:
            stmt = stmt.where(Asignacion.cohorte_id == cohorte_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def tiene_asignaciones_activas_materia(self, materia_id: uuid.UUID) -> bool:
        """Check if any non-deleted asignaciones exist for a materia."""
        stmt = select(Asignacion.id).where(
            Asignacion.tenant_id == self.tenant_id,
            Asignacion.materia_id == materia_id,
            Asignacion.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def tiene_asignaciones_activas_carrera(self, carrera_id: uuid.UUID) -> bool:
        """Check if any non-deleted asignaciones exist for a carrera."""
        stmt = select(Asignacion.id).where(
            Asignacion.tenant_id == self.tenant_id,
            Asignacion.carrera_id == carrera_id,
            Asignacion.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def tiene_asignaciones_activas_cohorte(self, cohorte_id: uuid.UUID) -> bool:
        """Check if any non-deleted asignaciones exist for a cohorte."""
        stmt = select(Asignacion.id).where(
            Asignacion.tenant_id == self.tenant_id,
            Asignacion.cohorte_id == cohorte_id,
            Asignacion.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create_batch(self, data_list: list[dict]) -> list[Asignacion]:
        """Create multiple asignaciones in one transaction (flush after each, commit at end)."""
        entities = []
        for data in data_list:
            entity = self.model(**data, tenant_id=self.tenant_id)
            self.db.add(entity)
            await self.db.flush()
            await self.db.refresh(entity)
            entities.append(entity)
        await self.db.commit()
        return entities

    async def count_activas_por_materia(self, materia_id: uuid.UUID) -> int:
        """Count non-deleted asignaciones for a subject."""
        stmt = select(Asignacion.id).where(
            Asignacion.tenant_id == self.tenant_id,
            Asignacion.materia_id == materia_id,
            Asignacion.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return len(result.scalars().all())

"""
app/repositories/tarea_repository.py — TareaRepository.

Extends BaseRepository[Tarea] with:
  - listar: tenant-scoped with optional filters (estado, asignado_a, asignado_por, materia_id)
    and pagination (limit/offset).
  - get_by_id: alias for BaseRepository.get (tenant-scoped, excludes soft-deleted).

Tenant isolation is inherited from BaseRepository (mandatory).
All queries start from _base_query() to guarantee soft-delete filter.

Implemented: C-16 (tareas-internas)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tarea import Tarea
from app.repositories.base import BaseRepository


class TareaRepository(BaseRepository[Tarea]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Tarea, session=session, tenant_id=tenant_id)

    async def listar(
        self,
        *,
        estado: str | None = None,
        asignado_a: uuid.UUID | None = None,
        asignado_por: uuid.UUID | None = None,
        materia_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Tarea]:
        """Return active (non-deleted) tareas for this tenant, with optional filters.

        All filters are optional; None means "no constraint on this field".
        Pagination via limit/offset for high-volume queries (D6).
        Results ordered by created_at descending.
        """
        stmt = self._base_query()

        if estado is not None:
            stmt = stmt.where(Tarea.estado == estado)
        if asignado_a is not None:
            stmt = stmt.where(Tarea.asignado_a == asignado_a)
        if asignado_por is not None:
            stmt = stmt.where(Tarea.asignado_por == asignado_por)
        if materia_id is not None:
            stmt = stmt.where(Tarea.materia_id == materia_id)

        stmt = stmt.order_by(Tarea.created_at.desc()).offset(offset).limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, tarea_id: uuid.UUID) -> Tarea | None:
        """Return tarea by id, scoped to this tenant (excludes soft-deleted).

        Thin alias over BaseRepository.get for explicit naming in service layer.
        """
        return await self.get(tarea_id)

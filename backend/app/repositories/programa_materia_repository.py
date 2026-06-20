"""
app/repositories/programa_materia_repository.py — ProgramaMateriaRepository.

Extends BaseRepository[ProgramaMateria] with:
  - get_vivo_por_combo: tenant-scoped, returns the unique vivo programme for
    a (materia_id, carrera_id, cohorte_id) combination (excludes soft-deleted).
  - listar: tenant-scoped listing with optional filters (materia_id, carrera_id,
    cohorte_id) and no pagination (catalogue-size data).

Tenant isolation is inherited from BaseRepository (mandatory).
All queries start from _base_query() to guarantee soft-delete filter.

Implemented: C-17 (programas-y-fechas-academicas)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.programa_materia import ProgramaMateria
from app.repositories.base import BaseRepository


class ProgramaMateriaRepository(BaseRepository[ProgramaMateria]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=ProgramaMateria, session=session, tenant_id=tenant_id)

    async def get_vivo_por_combo(
        self,
        *,
        materia_id: uuid.UUID,
        carrera_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> ProgramaMateria | None:
        """Return the unique vivo programme for the given combo, or None.

        Scoped to this tenant. Excludes soft-deleted rows.
        There can only be one vivo row per combo due to the unique partial index.
        """
        stmt = (
            self._base_query()
            .where(ProgramaMateria.materia_id == materia_id)
            .where(ProgramaMateria.carrera_id == carrera_id)
            .where(ProgramaMateria.cohorte_id == cohorte_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def listar(
        self,
        *,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
    ) -> list[ProgramaMateria]:
        """Return active (non-deleted) programmes for this tenant, with optional filters.

        All filters are optional; None means "no constraint on this field".
        Results ordered by created_at descending.
        """
        stmt = self._base_query()

        if materia_id is not None:
            stmt = stmt.where(ProgramaMateria.materia_id == materia_id)
        if carrera_id is not None:
            stmt = stmt.where(ProgramaMateria.carrera_id == carrera_id)
        if cohorte_id is not None:
            stmt = stmt.where(ProgramaMateria.cohorte_id == cohorte_id)

        stmt = stmt.order_by(ProgramaMateria.created_at.desc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

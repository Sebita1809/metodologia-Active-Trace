"""
app/repositories/fecha_academica_repository.py — FechaAcademicaRepository.

Extends BaseRepository[FechaAcademica] with:
  - listar_por_materia_cohorte: ordered by fecha asc, tenant-scoped.
  - existe_combo: checks uniqueness for (materia_id, cohorte_id, tipo, numero),
    tenant-scoped, excludes soft-deleted.
  - get_by_id: alias for BaseRepository.get (tenant-scoped, excludes soft-deleted).

Tenant isolation is inherited from BaseRepository (mandatory).
All queries start from _base_query() to guarantee soft-delete filter.

Implemented: C-17 (programas-y-fechas-academicas)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fecha_academica import FechaAcademica
from app.repositories.base import BaseRepository


class FechaAcademicaRepository(BaseRepository[FechaAcademica]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=FechaAcademica, session=session, tenant_id=tenant_id)

    async def listar_por_materia_cohorte(
        self,
        *,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> list[FechaAcademica]:
        """Return active fechas for materia × cohorte, ordered by fecha asc.

        Scoped to this tenant. Excludes soft-deleted rows.
        """
        stmt = (
            self._base_query()
            .where(FechaAcademica.materia_id == materia_id)
            .where(FechaAcademica.cohorte_id == cohorte_id)
            .order_by(FechaAcademica.fecha.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def existe_combo(
        self,
        *,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        tipo: str,
        numero: int,
    ) -> bool:
        """Check if a vivo combo (materia_id, cohorte_id, tipo, numero) exists.

        Scoped to this tenant. Excludes soft-deleted rows.
        Returns True if a row exists, False otherwise.
        """
        stmt = (
            self._base_query()
            .where(FechaAcademica.materia_id == materia_id)
            .where(FechaAcademica.cohorte_id == cohorte_id)
            .where(FechaAcademica.tipo == tipo)
            .where(FechaAcademica.numero == numero)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_by_id(self, fecha_id: uuid.UUID) -> FechaAcademica | None:
        """Return fecha_academica by id, scoped to this tenant (excludes soft-deleted).

        Thin alias over BaseRepository.get for explicit naming in service layer.
        """
        return await self.get(fecha_id)

"""
app/repositories/umbral_materia_repository.py — UmbralMateriaRepository.

Extends BaseRepository[UmbralMateria] with upsert and asignacion-scoped
query operations.

Tenant isolation is MANDATORY via _base_query() — never bypassed.

Implemented: C-10 (calificaciones-y-umbral)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.umbral_materia import UmbralMateria
from app.repositories.base import BaseRepository


class UmbralMateriaRepository(BaseRepository[UmbralMateria]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=UmbralMateria, session=session, tenant_id=tenant_id)

    async def get_by_asignacion(self, asignacion_id: uuid.UUID) -> UmbralMateria | None:
        """Return the active UmbralMateria for the given asignacion_id, or None.

        Uses _base_query() for tenant isolation + soft-delete filter.
        """
        stmt = (
            self._base_query()
            .where(UmbralMateria.asignacion_id == asignacion_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        asignacion_id: uuid.UUID,
        materia_id: uuid.UUID,
        umbral_pct: int,
        valores_aprobatorios: list[str],
    ) -> UmbralMateria:
        """Create or update the UmbralMateria for the given asignacion.

        If a record already exists (tenant + asignacion), updates it in-place.
        If not, creates a new one.
        """
        existing = await self.get_by_asignacion(asignacion_id)

        if existing is not None:
            existing.umbral_pct = umbral_pct
            existing.valores_aprobatorios = valores_aprobatorios
            await self._session.flush()
            await self._session.refresh(existing)
            return existing

        # Create new
        obj = UmbralMateria(
            tenant_id=self._tenant_id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=umbral_pct,
            valores_aprobatorios=valores_aprobatorios,
        )
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

"""
app/repositories/cohorte_repository.py — CohorteRepository.

Extends BaseRepository[Cohorte] with domain-specific lookups.
Tenant isolation is inherited from BaseRepository (mandatory).

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cohorte import Cohorte
from app.repositories.base import BaseRepository


class CohorteRepository(BaseRepository[Cohorte]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Cohorte, session=session, tenant_id=tenant_id)

    async def get_by_nombre_carrera(
        self, nombre: str, carrera_id: uuid.UUID
    ) -> Cohorte | None:
        """Return the active Cohorte with *nombre* and *carrera_id* in this tenant, or None."""
        stmt = (
            self._base_query()
            .where(Cohorte.nombre == nombre)
            .where(Cohorte.carrera_id == carrera_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_carrera(self, carrera_id: uuid.UUID) -> list[Cohorte]:
        """Return all active (non-deleted) Cohortes for the given *carrera_id* in this tenant."""
        return await self.list(carrera_id=carrera_id)

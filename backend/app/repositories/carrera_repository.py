"""
app/repositories/carrera_repository.py — CarreraRepository.

Extends BaseRepository[Carrera] with domain-specific lookups.
Tenant isolation is inherited from BaseRepository (mandatory).

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.carrera import Carrera
from app.repositories.base import BaseRepository


class CarreraRepository(BaseRepository[Carrera]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Carrera, session=session, tenant_id=tenant_id)

    async def get_by_codigo(self, codigo: str) -> Carrera | None:
        """Return the active Carrera with *codigo* in this tenant, or None."""
        results = await self.list(codigo=codigo)
        return results[0] if results else None

    async def list_activas(self) -> list[Carrera]:
        """Return all active (non-deleted, estado=Activa) Carreras in this tenant."""
        return await self.list(estado="Activa")

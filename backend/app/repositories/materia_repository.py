"""
app/repositories/materia_repository.py — MateriaRepository.

Extends BaseRepository[Materia] with domain-specific lookups.
Tenant isolation is inherited from BaseRepository (mandatory).

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.materia import Materia
from app.repositories.base import BaseRepository


class MateriaRepository(BaseRepository[Materia]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Materia, session=session, tenant_id=tenant_id)

    async def get_by_codigo(self, codigo: str) -> Materia | None:
        """Return the active Materia with *codigo* in this tenant, or None."""
        results = await self.list(codigo=codigo)
        return results[0] if results else None

    async def list_activas(self) -> list[Materia]:
        """Return all active (non-deleted, estado=Activa) Materias in this tenant."""
        return await self.list(estado="Activa")

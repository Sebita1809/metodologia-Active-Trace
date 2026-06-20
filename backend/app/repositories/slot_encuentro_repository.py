"""
app/repositories/slot_encuentro_repository.py — SlotEncuentroRepository.

Extends BaseRepository[SlotEncuentro] with slot-specific query methods.
All queries are tenant-scoped via _base_query() — never bypassed.

Key methods:
    create          — inherited from BaseRepository
    get             — inherited (returns None for other tenants)
    list_by_asignacion — list active slots for an asignacion
    bulk_create_instancias — persist N InstanciaEncuentro atomically

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slot_encuentro import SlotEncuentro
from app.repositories.base import BaseRepository


class SlotEncuentroRepository(BaseRepository[SlotEncuentro]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=SlotEncuentro, session=session, tenant_id=tenant_id)

    async def list_by_asignacion(self, asignacion_id: uuid.UUID) -> list[SlotEncuentro]:
        """Return active slots for the given asignacion within this tenant."""
        return await self.list(asignacion_id=asignacion_id)

"""
app/repositories/guardia_repository.py — GuardiaRepository.

Extends BaseRepository[Guardia] with guardia-specific query methods.
All queries are tenant-scoped via _base_query() — never bypassed.

Soft delete is inherited from BaseRepository — list() and get() exclude
soft-deleted rows automatically.

Key methods:
    create       — inherited
    list         — inherited (all active guardias in tenant)
    soft_delete  — inherited
    list_by_asignacion — filter by asignacion_id

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guardia import Guardia
from app.repositories.base import BaseRepository


class GuardiaRepository(BaseRepository[Guardia]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Guardia, session=session, tenant_id=tenant_id)

    async def list_by_asignacion(self, asignacion_id: uuid.UUID) -> list[Guardia]:
        """Return active guardias for the given asignacion within this tenant."""
        return await self.list(asignacion_id=asignacion_id)

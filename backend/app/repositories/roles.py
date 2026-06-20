"""
app/repositories/roles.py — Rol repository.

Extends BaseRepository[Rol] with RBAC-specific lookups.
Tenant isolation is inherited from BaseRepository (mandatory).

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rol import Rol
from app.repositories.base import BaseRepository


class RolRepository(BaseRepository[Rol]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Rol, session=session, tenant_id=tenant_id)

    async def get_by_nombre(self, nombre: str) -> Rol | None:
        """Return the active Rol with *nombre* in this tenant, or None."""
        results = await self.list(nombre=nombre)
        return results[0] if results else None

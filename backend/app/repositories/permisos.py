"""
app/repositories/permisos.py — Permiso repository.

Extends BaseRepository[Permiso] with RBAC-specific lookups.
Tenant isolation is inherited from BaseRepository (mandatory).

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permiso import Permiso
from app.repositories.base import BaseRepository


class PermisoRepository(BaseRepository[Permiso]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Permiso, session=session, tenant_id=tenant_id)

    async def get_by_clave(self, clave: str) -> Permiso | None:
        """Return the active Permiso with *clave* in this tenant, or None."""
        results = await self.list(clave=clave)
        return results[0] if results else None

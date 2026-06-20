"""
app/repositories/rol_permiso.py — RolPermiso repository.

Extends BaseRepository[RolPermiso] for managing the role×permission matrix.
Tenant isolation is inherited from BaseRepository (mandatory).

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rol_permiso import RolPermiso
from app.repositories.base import BaseRepository


class RolPermisoRepository(BaseRepository[RolPermiso]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=RolPermiso, session=session, tenant_id=tenant_id)

    async def list_for_rol(self, rol_id: uuid.UUID) -> list[RolPermiso]:
        """Return all active RolPermiso entries for *rol_id* in this tenant."""
        stmt = (
            self._base_query()
            .where(RolPermiso.rol_id == rol_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_rol_and_permiso(
        self, rol_id: uuid.UUID, permiso_id: uuid.UUID
    ) -> RolPermiso | None:
        """Return the assignment for a specific (rol_id, permiso_id) pair, or None."""
        stmt = (
            self._base_query()
            .where(RolPermiso.rol_id == rol_id)
            .where(RolPermiso.permiso_id == permiso_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

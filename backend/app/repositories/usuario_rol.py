"""
app/repositories/usuario_rol.py — UsuarioRol repository.

Extends BaseRepository[UsuarioRol] for managing user role assignments.
Tenant isolation is inherited from BaseRepository (mandatory).

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario_rol import UsuarioRol
from app.repositories.base import BaseRepository


class UsuarioRolRepository(BaseRepository[UsuarioRol]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=UsuarioRol, session=session, tenant_id=tenant_id)

    async def list_vigentes(self, user_id: uuid.UUID, ahora: datetime) -> list[UsuarioRol]:
        """Return all active (vigente) role assignments for *user_id* at *ahora*.

        An assignment is vigente if:
          vigente_desde <= ahora AND (vigente_hasta IS NULL OR vigente_hasta > ahora)
        """
        stmt = (
            self._base_query()
            .where(UsuarioRol.user_id == user_id)
            .where(UsuarioRol.vigente_desde <= ahora)
            .where(
                or_(
                    UsuarioRol.vigente_hasta.is_(None),
                    UsuarioRol.vigente_hasta > ahora,
                )
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_user(self, user_id: uuid.UUID) -> list[UsuarioRol]:
        """Return ALL (including expired) role assignments for *user_id* in this tenant.

        For audit/history purposes.
        """
        stmt = self._base_query().where(UsuarioRol.user_id == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

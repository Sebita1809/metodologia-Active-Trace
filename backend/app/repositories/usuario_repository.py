"""
app/repositories/usuario_repository.py — UsuarioRepository.

Extends BaseRepository[Usuario] with domain-specific lookups.
Tenant isolation is inherited from BaseRepository (mandatory).

Implemented: C-07 (usuarios-y-asignaciones)
Updated:     C-08 (equipos-docentes) — search_by_name
Updated:     fix-admin-usuario-patch — selectinload asignaciones
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.usuario import Usuario
from app.repositories.base import BaseRepository


class UsuarioRepository(BaseRepository[Usuario]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Usuario, session=session, tenant_id=tenant_id)

    async def get(self, record_id: uuid.UUID) -> Usuario | None:
        stmt = (
            self._base_query()
            .where(Usuario.id == record_id)
            .options(selectinload(Usuario.asignaciones))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, **filters) -> list[Usuario]:
        stmt = self._base_query().options(selectinload(Usuario.asignaciones))
        for attr, value in filters.items():
            stmt = stmt.where(getattr(self._model, attr) == value)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_email_hash(self, email_hash: str) -> Usuario | None:
        """Return the active Usuario with *email_hash* in this tenant, or None.

        Uses _base_query() to guarantee tenant isolation and soft-delete filter.
        """
        results = await self.list(email_hash=email_hash)
        return results[0] if results else None

    async def list_activos(self) -> list[Usuario]:
        """Return all active (non-deleted, estado=Activo) Usuarios in this tenant."""
        return await self.list(estado="Activo")

    async def search_by_name(self, q: str) -> list[Usuario]:
        """Return up to 20 usuarios matching *q* on nombre or apellidos (case-insensitive).

        Caller must validate len(q) >= 2 before calling this method.
        Uses _base_query() for tenant isolation and soft-delete filter.
        """
        pattern = f"%{q}%"
        stmt = (
            self._base_query()
            .where(
                Usuario.nombre.ilike(pattern) | Usuario.apellidos.ilike(pattern)
            )
            .options(selectinload(Usuario.asignaciones))
            .limit(20)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

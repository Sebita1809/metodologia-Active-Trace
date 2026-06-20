"""
app/repositories/version_padron_repository.py — VersionPadronRepository.

Extends BaseRepository[VersionPadron] with domain-specific operations
for the versioned padrón feature.

Tenant isolation is MANDATORY via _base_query() — never bypassed.
Soft-delete semantics: deleted_at IS NULL for active records.

Implemented: C-09 (padron-ingesta-moodle)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.version_padron import VersionPadron
from app.repositories.base import BaseRepository


class VersionPadronRepository(BaseRepository[VersionPadron]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=VersionPadron, session=session, tenant_id=tenant_id)

    async def get_activa(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> VersionPadron | None:
        """Return the currently active VersionPadron for (materia, cohorte), or None.

        Uses _base_query() for tenant isolation and soft-delete filter.
        """
        stmt = (
            self._base_query()
            .where(VersionPadron.materia_id == materia_id)
            .where(VersionPadron.cohorte_id == cohorte_id)
            .where(VersionPadron.activa.is_(True))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_versiones(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> list[VersionPadron]:
        """Return all VersionPadron (active and inactive) for (materia, cohorte).

        Ordered by cargado_at descending (newest first).
        Uses _base_query() for tenant isolation.
        """
        stmt = (
            self._base_query()
            .where(VersionPadron.materia_id == materia_id)
            .where(VersionPadron.cohorte_id == cohorte_id)
            .order_by(VersionPadron.cargado_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def desactivar_activa(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> int:
        """Set activa=False on the currently active version for (materia, cohorte).

        Returns the number of rows updated (0 or 1).
        Scoped to this tenant — cannot affect other tenants.
        """
        stmt = (
            update(VersionPadron)
            .where(VersionPadron.tenant_id == self._tenant_id)
            .where(VersionPadron.materia_id == materia_id)
            .where(VersionPadron.cohorte_id == cohorte_id)
            .where(VersionPadron.activa.is_(True))
            .where(VersionPadron.deleted_at.is_(None))
            .values(activa=False, updated_at=datetime.now(tz=timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def soft_delete_scope(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> int:
        """Soft-delete ALL versions in (tenant, materia, cohorte) scope.

        Sets deleted_at on each non-deleted version.
        Returns the number of rows soft-deleted.
        Scoped to this tenant — cannot affect other tenants.
        """
        stmt = (
            update(VersionPadron)
            .where(VersionPadron.tenant_id == self._tenant_id)
            .where(VersionPadron.materia_id == materia_id)
            .where(VersionPadron.cohorte_id == cohorte_id)
            .where(VersionPadron.deleted_at.is_(None))
            .values(deleted_at=datetime.now(tz=timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def list_version_ids_in_scope(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        """Return IDs of all non-deleted versions in (tenant, materia, cohorte).

        Used by EntradaPadronRepository.soft_delete_by_versions before
        soft-deleting the version headers.
        """
        stmt = (
            select(VersionPadron.id)
            .where(VersionPadron.tenant_id == self._tenant_id)
            .where(VersionPadron.materia_id == materia_id)
            .where(VersionPadron.cohorte_id == cohorte_id)
            .where(VersionPadron.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

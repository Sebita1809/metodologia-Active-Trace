"""
app/repositories/entrada_padron_repository.py — EntradaPadronRepository.

Extends BaseRepository[EntradaPadron] with bulk-write and version-scoped
query operations.

Tenant isolation is MANDATORY via _base_query() — never bypassed.
Email PII is never decrypted here — that is the responsibility of PadronService.

Implemented: C-09 (padron-ingesta-moodle)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entrada_padron import EntradaPadron
from app.repositories.base import BaseRepository


class EntradaPadronRepository(BaseRepository[EntradaPadron]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=EntradaPadron, session=session, tenant_id=tenant_id)

    async def bulk_create(self, entradas: list[EntradaPadron]) -> list[EntradaPadron]:
        """Persist multiple EntradaPadron rows in a single flush.

        All objects MUST have tenant_id already set to self._tenant_id before
        calling this method (enforced via assertion).

        Returns the persisted objects with server-generated fields populated.
        """
        for entrada in entradas:
            if entrada.tenant_id != self._tenant_id:
                raise ValueError(
                    f"EntradaPadron tenant_id mismatch: {entrada.tenant_id} != {self._tenant_id}"
                )
            self._session.add(entrada)

        await self._session.flush()

        for entrada in entradas:
            await self._session.refresh(entrada)

        return entradas

    async def list_by_version(self, version_id: uuid.UUID) -> list[EntradaPadron]:
        """Return all non-deleted EntradaPadron rows for a given version_id.

        Uses _base_query() for tenant isolation + soft-delete filter.
        Additionally filters by version_id.
        """
        stmt = (
            self._base_query()
            .where(EntradaPadron.version_id == version_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete_by_versions(self, version_ids: list[uuid.UUID]) -> int:
        """Soft-delete all EntradaPadron rows belonging to the given version_ids.

        Only deletes rows that belong to this tenant and are not yet deleted.
        Returns the total number of rows soft-deleted.
        """
        if not version_ids:
            return 0

        stmt = (
            update(EntradaPadron)
            .where(EntradaPadron.tenant_id == self._tenant_id)
            .where(EntradaPadron.version_id.in_(version_ids))
            .where(EntradaPadron.deleted_at.is_(None))
            .values(deleted_at=datetime.now(tz=timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

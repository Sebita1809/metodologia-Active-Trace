"""
app/repositories/calificacion_repository.py — CalificacionRepository.

Extends BaseRepository[Calificacion] with bulk-write and padron-scoped
query operations.

Tenant isolation is MANDATORY via _base_query() — never bypassed.

Implemented: C-10 (calificaciones-y-umbral)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calificacion import Calificacion
from app.repositories.base import BaseRepository


class CalificacionRepository(BaseRepository[Calificacion]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Calificacion, session=session, tenant_id=tenant_id)

    async def create_many(self, calificaciones: list[Calificacion]) -> list[Calificacion]:
        """Persist multiple Calificacion rows in a single flush.

        All objects MUST have tenant_id already set to self._tenant_id before
        calling this method (enforced via assertion).

        Returns the persisted objects with server-generated fields populated.
        """
        for cal in calificaciones:
            if cal.tenant_id != self._tenant_id:
                raise ValueError(
                    f"Calificacion tenant_id mismatch: {cal.tenant_id} != {self._tenant_id}"
                )
            self._session.add(cal)

        await self._session.flush()

        for cal in calificaciones:
            await self._session.refresh(cal)

        return calificaciones

    async def list_by_entradas(self, entrada_padron_ids: list[uuid.UUID]) -> list[Calificacion]:
        """Return all non-deleted Calificacion rows for the given entrada_padron_ids.

        Uses _base_query() for tenant isolation + soft-delete filter.
        """
        if not entrada_padron_ids:
            return []

        stmt = (
            self._base_query()
            .where(Calificacion.entrada_padron_id.in_(entrada_padron_ids))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_asignacion(
        self,
        asignacion_id: uuid.UUID,  # noqa: ARG002 — kept for API clarity; caller provides entrada_ids
        entrada_padron_ids: list[uuid.UUID],
    ) -> list[Calificacion]:
        """Return all non-deleted Calificacion rows for the given asignacion.

        Filtering is done via the list of entrada_padron_ids that belong to
        the asignacion's active padrón version (resolved by the caller/service).
        """
        return await self.list_by_entradas(entrada_padron_ids)

    async def delete_by_entradas(self, entrada_padron_ids: list[uuid.UUID]) -> int:
        """Soft-delete all Calificacion rows for the given entrada_padron_ids.

        Only deletes rows that belong to this tenant and are not yet deleted.
        Returns the number of rows soft-deleted.
        """
        if not entrada_padron_ids:
            return 0

        stmt = (
            update(Calificacion)
            .where(Calificacion.tenant_id == self._tenant_id)
            .where(Calificacion.entrada_padron_id.in_(entrada_padron_ids))
            .where(Calificacion.deleted_at.is_(None))
            .values(deleted_at=datetime.now(tz=timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

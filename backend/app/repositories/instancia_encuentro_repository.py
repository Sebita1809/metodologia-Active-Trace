"""
app/repositories/instancia_encuentro_repository.py — InstanciaEncuentroRepository.

Extends BaseRepository[InstanciaEncuentro] with bulk insert, slot-scoped
listing, and asignacion-scoped listing.

All queries are tenant-scoped via _base_query() — never bypassed.

Key methods:
    bulk_create       — persist N InstanciaEncuentro rows in one flush
    list_by_slot      — list all active instancias for a slot
    list_by_asignacion — list all active instancias for an asignacion (via slot FK)
    get               — inherited
    update            — inherited (used by editar_instancia)

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instancia_encuentro import InstanciaEncuentro
from app.repositories.base import BaseRepository


class InstanciaEncuentroRepository(BaseRepository[InstanciaEncuentro]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=InstanciaEncuentro, session=session, tenant_id=tenant_id)

    async def bulk_create(
        self, instancias: list[InstanciaEncuentro]
    ) -> list[InstanciaEncuentro]:
        """Persist multiple InstanciaEncuentro rows in a single flush.

        All objects MUST have tenant_id == self._tenant_id (enforced via assertion).
        Returns the persisted objects with server-generated fields populated.
        """
        for inst in instancias:
            if inst.tenant_id != self._tenant_id:
                raise ValueError(
                    f"InstanciaEncuentro tenant_id mismatch: "
                    f"{inst.tenant_id} != {self._tenant_id}"
                )
            self._session.add(inst)

        await self._session.flush()

        for inst in instancias:
            await self._session.refresh(inst)

        return instancias

    async def list_by_slot(self, slot_id: uuid.UUID) -> list[InstanciaEncuentro]:
        """Return active instancias for the given slot within this tenant."""
        stmt = (
            self._base_query()
            .where(InstanciaEncuentro.slot_id == slot_id)
            .order_by(InstanciaEncuentro.fecha)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_materia(self, materia_id: uuid.UUID) -> list[InstanciaEncuentro]:
        """Return active instancias for the given materia within this tenant."""
        stmt = (
            self._base_query()
            .where(InstanciaEncuentro.materia_id == materia_id)
            .order_by(InstanciaEncuentro.fecha)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all_tenant(self) -> list[InstanciaEncuentro]:
        """Return all active instancias within this tenant (admin view).

        Does NOT cross tenants — still scoped to self._tenant_id via _base_query().
        """
        stmt = self._base_query().order_by(InstanciaEncuentro.fecha)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

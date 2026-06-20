"""
app/repositories/factura_repository.py — FacturaRepository (C-18).

Tenant-scoped repository for Factura. Implements:
  - listar(filtros)       → filtered list of active facturas
  - get_by_id(id)         → single factura by id
  - sumar_periodo(mes, anio) → sum of monto for active facturas in a period

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.factura import Factura
from app.repositories.base import BaseRepository


class FacturaRepository(BaseRepository[Factura]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Factura, session=session, tenant_id=tenant_id)

    async def listar(
        self,
        *,
        usuario_id: uuid.UUID | None = None,
        estado: str | None = None,
        periodo_mes: int | None = None,
        periodo_anio: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Factura]:
        """Return active facturas for this tenant, with optional filters.

        Filters are optional: None means no constraint on that field.
        Ordered by periodo desc, then created_at desc.
        """
        stmt = self._base_query()

        if usuario_id is not None:
            stmt = stmt.where(Factura.usuario_id == usuario_id)
        if estado is not None:
            stmt = stmt.where(Factura.estado == estado)
        if periodo_mes is not None:
            stmt = stmt.where(Factura.periodo_mes == periodo_mes)
        if periodo_anio is not None:
            stmt = stmt.where(Factura.periodo_anio == periodo_anio)

        stmt = (
            stmt.order_by(
                Factura.periodo_anio.desc(),
                Factura.periodo_mes.desc(),
                Factura.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, factura_id: uuid.UUID) -> Factura | None:
        """Return factura by id, scoped to this tenant (excludes soft-deleted)."""
        return await self.get(factura_id)

    async def sumar_periodo(
        self, mes: int, anio: int
    ) -> Decimal:
        """Return the sum of monto for all active facturas in (mes, anio) for this tenant.

        Used to compute the `total_con_factura` KPI (RN-38).
        Returns Decimal(0) if no rows found.
        """
        stmt = (
            select(func.coalesce(func.sum(Factura.monto), 0))
            .where(Factura.tenant_id == self._tenant_id)
            .where(Factura.deleted_at.is_(None))
            .where(Factura.periodo_mes == mes)
            .where(Factura.periodo_anio == anio)
        )
        result = await self._session.execute(stmt)
        raw = result.scalar_one()
        return Decimal(str(raw)) if raw is not None else Decimal("0")

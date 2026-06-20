"""
app/repositories/salario_base_repository.py — SalarioBaseRepository (C-18).

Tenant-scoped repository for SalarioBase. Implements:
  - listar()                   → all active rows for this tenant
  - get_vigente(rol, ref_date) → the row where desde <= ref_date AND (hasta IS NULL OR hasta >= ref_date)
  - existe_solapamiento(...)   → True if any vivo row for same rol overlaps the given range

Vigency logic (RN-31):
  ref_date = first day of the month being liquidated.
  A row is vigente if: desde <= ref_date AND (hasta IS NULL OR hasta >= ref_date).
  If multiple rows are vigente (invalid state), the one with latest `desde` is returned
  as a deterministic tiebreak — the service validates non-overlap at write time.

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.salario_base import SalarioBase
from app.repositories.base import BaseRepository


class SalarioBaseRepository(BaseRepository[SalarioBase]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=SalarioBase, session=session, tenant_id=tenant_id)

    async def listar(self) -> list[SalarioBase]:
        """Return all active (non-deleted) SalarioBase rows for this tenant.

        Ordered by rol asc, desde asc for consistent display.
        """
        stmt = self._base_query().order_by(SalarioBase.rol, SalarioBase.desde)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_vigente(self, rol: str, ref_date: date) -> SalarioBase | None:
        """Return the vigent SalarioBase for (rol, ref_date).

        Selects rows where:
            desde <= ref_date AND (hasta IS NULL OR hasta >= ref_date)

        If multiple rows match (should not happen with non-overlap validation),
        returns the one with the latest `desde` as deterministic tiebreak.
        """
        stmt = (
            self._base_query()
            .where(SalarioBase.rol == rol)
            .where(SalarioBase.desde <= ref_date)
            .where(
                or_(
                    SalarioBase.hasta.is_(None),
                    SalarioBase.hasta >= ref_date,
                )
            )
            .order_by(SalarioBase.desde.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def existe_solapamiento(
        self,
        rol: str,
        desde: date,
        hasta: date | None,
        excluir_id: uuid.UUID | None = None,
    ) -> bool:
        """Return True if any vivo row for (rol) overlaps the given range.

        Overlap conditions (RN-31):
          New range [desde, hasta] overlaps existing [e.desde, e.hasta] if:
            e.desde <= (hasta or ∞) AND (e.hasta or ∞) >= desde

        `excluir_id` is used when editing an existing row (exclude itself).
        """
        stmt = (
            self._base_query()
            .where(SalarioBase.rol == rol)
            # Existing row starts before or on our proposed end
            .where(
                or_(
                    hasta is None,  # our new range is open → anything that starts after desde overlaps
                    SalarioBase.desde <= hasta,
                )
            )
            # Existing row ends after or on our proposed start
            .where(
                or_(
                    SalarioBase.hasta.is_(None),
                    SalarioBase.hasta >= desde,
                )
            )
        )
        if excluir_id is not None:
            stmt = stmt.where(SalarioBase.id != excluir_id)

        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return row is not None

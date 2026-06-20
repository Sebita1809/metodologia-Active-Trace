"""
app/repositories/salario_plus_repository.py — SalarioPlusRepository (C-18).

Tenant-scoped repository for SalarioPlus. Implements:
  - listar()                          → all active rows for this tenant
  - get_vigente(clave, rol, ref_date) → vigent row for (clave, rol) at ref_date
  - existe_solapamiento(...)          → True if overlap for same (clave, rol)

Vigency logic mirrors SalarioBaseRepository (RN-31).

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.salario_plus import SalarioPlus
from app.repositories.base import BaseRepository


class SalarioPlusRepository(BaseRepository[SalarioPlus]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=SalarioPlus, session=session, tenant_id=tenant_id)

    async def listar(self) -> list[SalarioPlus]:
        """Return all active (non-deleted) SalarioPlus rows for this tenant.

        Ordered by clave asc, rol asc, desde asc.
        """
        stmt = self._base_query().order_by(
            SalarioPlus.clave, SalarioPlus.rol, SalarioPlus.desde
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_vigente(
        self, clave: str, rol: str, ref_date: date
    ) -> SalarioPlus | None:
        """Return the vigent SalarioPlus for (clave, rol, ref_date).

        Selects rows where:
            clave = :clave AND rol = :rol
            AND desde <= ref_date
            AND (hasta IS NULL OR hasta >= ref_date)

        Returns the latest `desde` on tie (should not happen).
        """
        stmt = (
            self._base_query()
            .where(SalarioPlus.clave == clave)
            .where(SalarioPlus.rol == rol)
            .where(SalarioPlus.desde <= ref_date)
            .where(
                or_(
                    SalarioPlus.hasta.is_(None),
                    SalarioPlus.hasta >= ref_date,
                )
            )
            .order_by(SalarioPlus.desde.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def existe_solapamiento(
        self,
        clave: str,
        rol: str,
        desde: date,
        hasta: date | None,
        excluir_id: uuid.UUID | None = None,
    ) -> bool:
        """Return True if any vivo row for (clave, rol) overlaps the given range."""
        stmt = (
            self._base_query()
            .where(SalarioPlus.clave == clave)
            .where(SalarioPlus.rol == rol)
            .where(
                or_(
                    hasta is None,
                    SalarioPlus.desde <= hasta,
                )
            )
            .where(
                or_(
                    SalarioPlus.hasta.is_(None),
                    SalarioPlus.hasta >= desde,
                )
            )
        )
        if excluir_id is not None:
            stmt = stmt.where(SalarioPlus.id != excluir_id)

        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return row is not None

"""
app/models/salario_base.py — SalarioBase domain entity (C-18).

Stores the base salary amount for a given role, scoped to a tenant.
Temporal validity is open-ended: desde (required) and hasta (nullable = no upper bound).
Non-overlap of vigency ranges per (tenant, rol) is enforced at the service layer.

StrEnum values for rol: PROFESOR | TUTOR | NEXO | COORDINADOR

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class SalarioBase(BaseTenantModel):
    """Base salary row for a role within a tenant.

    Columns beyond BaseTenantModel:
        rol    — role this base applies to (PROFESOR | TUTOR | NEXO | COORDINADOR)
        monto  — salary amount (Numeric 12,2; CHECK >= 0)
        desde  — start of validity range (inclusive)
        hasta  — end of validity range (inclusive, NULL = open / no limit)
    """

    __tablename__ = "salario_base"
    __table_args__ = (
        CheckConstraint("monto >= 0", name="ck_salario_base_monto_positivo"),
    )

    rol: Mapped[str] = mapped_column(String(30), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<SalarioBase id={self.id} tenant_id={self.tenant_id} "
            f"rol={self.rol!r} monto={self.monto} desde={self.desde} hasta={self.hasta}>"
        )

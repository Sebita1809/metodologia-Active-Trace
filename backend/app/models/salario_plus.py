"""
app/models/salario_plus.py — SalarioPlus domain entity (C-18).

Stores the plus salary amount for a (clave, rol) pair, scoped to a tenant.
`clave` is a tenant-free string (PA-22): each tenant defines its own keys.
Matches `Materia.clave_plus` to accumulate N times per N active comisiones.

Temporal validity: desde (required) and hasta (nullable = open).
Non-overlap of vigency ranges per (tenant, clave, rol) enforced at service layer.

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class SalarioPlus(BaseTenantModel):
    """Plus salary row for a (clave, rol) pair within a tenant.

    Columns beyond BaseTenantModel:
        clave       — free string key matching Materia.clave_plus (PA-22)
        rol         — role this plus applies to
        descripcion — human-readable description (nullable)
        monto       — plus amount per comision (Numeric 12,2; CHECK >= 0)
        desde       — start of validity range (inclusive)
        hasta       — end of validity range (inclusive, NULL = open)
    """

    __tablename__ = "salario_plus"
    __table_args__ = (
        CheckConstraint("monto >= 0", name="ck_salario_plus_monto_positivo"),
    )

    clave: Mapped[str] = mapped_column(String(50), nullable=False)
    rol: Mapped[str] = mapped_column(String(30), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<SalarioPlus id={self.id} tenant_id={self.tenant_id} "
            f"clave={self.clave!r} rol={self.rol!r} monto={self.monto}>"
        )

"""
app/models/carrera.py — Carrera model.

Represents an academic program (degree/career) owned by a tenant.

Table: carreras
Unique constraint: (tenant_id, codigo) — one code per tenant.
Estado values: "Activa", "Inactiva" (String, not enum, for simpler test setup).

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class Carrera(BaseTenantModel):
    """Academic program (degree) belonging to a tenant.

    Columns beyond BaseTenantModel:
        codigo  — short identifier (e.g. "ISI"), unique per tenant
        nombre  — full name (e.g. "Ingeniería en Sistemas")
        estado  — "Activa" | "Inactiva"
    """

    __tablename__ = "carreras"
    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo", name="uq_carrera_tenant_codigo"),
    )

    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Activa")

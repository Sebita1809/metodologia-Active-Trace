"""
app/models/materia.py — Materia model.

Represents a course/subject in the academic catalog, owned by a tenant.
This is the tenant-level catalog entry (ADR-006: Materia + Dictado model).

Table: materias
Unique constraint: (tenant_id, codigo) — one code per tenant.
Estado values: "Activa", "Inactiva" (String, not enum).

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class Materia(BaseTenantModel):
    """Course/subject catalog entry belonging to a tenant.

    Columns beyond BaseTenantModel:
        codigo  — short identifier (e.g. "MAT101"), unique per tenant
        nombre  — full name (e.g. "Matemática I")
        estado  — "Activa" | "Inactiva"
    """

    __tablename__ = "materias"
    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo", name="uq_materia_tenant_codigo"),
    )

    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Activa")

    # C-18: free-form key mapping this materia to a Plus salary category.
    # NULL means this materia does not contribute Plus to liquidations (RN-33, PA-22).
    clave_plus: Mapped[str | None] = mapped_column(String(50), nullable=True)

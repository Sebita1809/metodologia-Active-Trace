"""
app/models/cohorte.py — Cohorte model.

Represents a cohort (intake year/group) of a Carrera, owned by a tenant.

Table: cohortes
Unique constraint: (tenant_id, carrera_id, nombre) — one name per carrera per tenant.
Estado values: "Activa", "Inactiva" (String, not enum).

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class Cohorte(BaseTenantModel):
    """Cohort (intake group) belonging to a Carrera and tenant.

    Columns beyond BaseTenantModel:
        carrera_id  — FK to carreras.id
        nombre      — cohort label (e.g. "2024-1")
        anio        — calendar year
        vig_desde   — start date of validity
        vig_hasta   — end date of validity (nullable — open-ended cohort)
        estado      — "Activa" | "Inactiva"
    """

    __tablename__ = "cohortes"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "carrera_id", "nombre",
            name="uq_cohorte_tenant_carrera_nombre",
        ),
    )

    carrera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carreras.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    vig_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vig_hasta: Mapped[date | None] = mapped_column(Date, nullable=True, default=None)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Activa")

"""
app/models/umbral_materia.py — UmbralMateria domain entity.

Configures the approval threshold and textual approval values for a given
teaching assignment (asignacion). One umbral per (tenant, asignacion) pair.

FK references:
  asignacion_id → asignaciones.id (RESTRICT)
  materia_id    → materias.id (RESTRICT)

Unique constraint: (tenant_id, asignacion_id) WHERE deleted_at IS NULL

Implemented: C-10 (calificaciones-y-umbral)
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class UmbralMateria(BaseTenantModel):
    """Approval threshold configuration for a teaching assignment.

    Columns beyond BaseTenantModel:
        asignacion_id       — FK to asignaciones.id (RESTRICT, NOT NULL)
        materia_id          — FK to materias.id (RESTRICT, NOT NULL)
        umbral_pct          — minimum passing numeric grade (default 60)
        valores_aprobatorios — JSONB list of passing textual values
    """

    __tablename__ = "umbral_materia"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "asignacion_id",
            name="uq_umbral_materia_tenant_asignacion",
        ),
    )

    asignacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asignaciones.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materias.id", ondelete="RESTRICT"),
        nullable=False,
    )

    umbral_pct: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
    )

    valores_aprobatorios: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    def __repr__(self) -> str:
        return (
            f"<UmbralMateria id={self.id} tenant_id={self.tenant_id} "
            f"asignacion_id={self.asignacion_id} umbral_pct={self.umbral_pct}>"
        )

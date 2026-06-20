"""
app/models/asignacion.py — Asignacion domain entity.

Represents a role assignment for a Usuario within the academic structure.
Temporal validity (desde/hasta) is stored as dates; the derived field
`estado_vigencia` is NEVER persisted — it is computed by the Service layer.

FK references:
  usuario_id    → usuarios.id (RESTRICT)
  materia_id    → materias.id (RESTRICT, nullable)
  carrera_id    → carreras.id (RESTRICT, nullable)
  cohorte_id    → cohortes.id (RESTRICT, nullable)
  responsable_id → usuarios.id (RESTRICT, nullable — self-referential)

Implemented: C-07 (usuarios-y-asignaciones)
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class Asignacion(BaseTenantModel):
    """Role assignment with temporal validity.

    Columns:
        usuario_id      — FK to usuarios.id (NOT NULL)
        rol             — business role string: PROFESOR | TUTOR | COORDINADOR |
                          NEXO | ADMIN | FINANZAS
        materia_id      — FK to materias.id (nullable)
        carrera_id      — FK to carreras.id (nullable)
        cohorte_id      — FK to cohortes.id (nullable)
        comisiones      — JSONB array of commission strings (default [])
        responsable_id  — FK to usuarios.id (nullable, self-ref)
        desde           — start date (NOT NULL)
        hasta           — end date (nullable — open-ended assignment)

    Derived (not stored):
        estado_vigencia — "Vigente" | "Vencida" (computed by service)
    """

    __tablename__ = "asignaciones"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    rol: Mapped[str] = mapped_column(String(30), nullable=False)

    materia_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materias.id", ondelete="RESTRICT"),
        nullable=True,
    )

    carrera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carreras.id", ondelete="RESTRICT"),
        nullable=True,
    )

    cohorte_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohortes.id", ondelete="RESTRICT"),
        nullable=True,
    )

    comisiones: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    responsable_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Asignacion id={self.id} tenant_id={self.tenant_id} "
            f"usuario_id={self.usuario_id} rol={self.rol}>"
        )

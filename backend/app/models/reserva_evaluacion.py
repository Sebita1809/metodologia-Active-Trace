"""
app/models/reserva_evaluacion.py — ReservaEvaluacion domain entity.

An alumno reserves a time slot for an evaluation.

Fields:
  evaluacion_id — FK to evaluacion.id
  alumno_id     — FK to usuarios.id
  fecha_hora    — scheduled DateTime (timezone-aware)
  estado        — VARCHAR(20) + CHECK: Activa|Cancelada (default Activa)

Uniqueness: UNIQUE PARTIAL index (evaluacion_id, alumno_id) WHERE estado='Activa'
ensures an alumno has at most one active reservation per evaluation.

Implemented: C-14 (evaluaciones-y-coloquios)
"""
from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class EstadoReserva(StrEnum):
    ACTIVA = "Activa"
    CANCELADA = "Cancelada"


class ReservaEvaluacion(BaseTenantModel):
    """A scheduled reservation by an alumno for a specific evaluation.

    Columns beyond BaseTenantModel:
        evaluacion_id — FK to evaluacion.id (NOT NULL, index)
        alumno_id     — FK to usuarios.id (NOT NULL)
        fecha_hora    — UTC datetime of the scheduled slot (NOT NULL)
        estado        — VARCHAR(20) CHECK IN ('Activa','Cancelada'), default 'Activa'

    Note: UNIQUE PARTIAL index (evaluacion_id, alumno_id) WHERE estado='Activa'
    is created by the Alembic migration (cannot be expressed as a pure ORM constraint).
    """

    __tablename__ = "reserva_evaluacion"

    __table_args__ = (
        CheckConstraint(
            "estado IN ('Activa','Cancelada')",
            name="ck_reserva_evaluacion_estado",
        ),
    )

    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    alumno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    fecha_hora: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Activa")

    def __repr__(self) -> str:
        return (
            f"<ReservaEvaluacion id={self.id} tenant_id={self.tenant_id} "
            f"evaluacion_id={self.evaluacion_id} alumno_id={self.alumno_id} "
            f"estado={self.estado!r}>"
        )

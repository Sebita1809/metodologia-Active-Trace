"""
app/models/evaluacion.py — Evaluacion domain entity.

Represents a scheduled evaluation (parcial, TP, coloquio, recuperatorio)
for an academic context (materia × cohorte).

Fields:
  materia_id      — FK to materias.id
  cohorte_id      — FK to cohortes.id
  tipo            — VARCHAR(20) + CHECK: Parcial|TP|Coloquio|Recuperatorio
  estado          — VARCHAR(20) + CHECK: Activa|Cerrada (default Activa)
  instancia       — free text label (e.g. "1er Parcial")
  dias_disponibles — scheduling window in days
  cupo_por_dia    — max reservas per day

Implemented: C-14 (evaluaciones-y-coloquios)
"""
from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class TipoEvaluacion(StrEnum):
    PARCIAL = "Parcial"
    TP = "TP"
    COLOQUIO = "Coloquio"
    RECUPERATORIO = "Recuperatorio"


class EstadoEvaluacion(StrEnum):
    ACTIVA = "Activa"
    CERRADA = "Cerrada"


class Evaluacion(BaseTenantModel):
    """Exam / evaluation scheduled for a materia × cohorte pair.

    Columns beyond BaseTenantModel:
        materia_id       — FK to materias.id (NOT NULL, index)
        cohorte_id       — FK to cohortes.id (NOT NULL)
        tipo             — VARCHAR(20) CHECK IN ('Parcial','TP','Coloquio','Recuperatorio')
        estado           — VARCHAR(20) CHECK IN ('Activa','Cerrada'), default 'Activa'
        instancia        — descriptive label (varchar 200)
        dias_disponibles — window in days for scheduling (positive integer)
        cupo_por_dia     — max reservas per calendar day (positive integer)
    """

    __tablename__ = "evaluacion"

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('Parcial','TP','Coloquio','Recuperatorio')",
            name="ck_evaluacion_tipo",
        ),
        CheckConstraint(
            "estado IN ('Activa','Cerrada')",
            name="ck_evaluacion_estado",
        ),
        CheckConstraint(
            "dias_disponibles > 0",
            name="ck_evaluacion_dias_disponibles_positive",
        ),
        CheckConstraint(
            "cupo_por_dia > 0",
            name="ck_evaluacion_cupo_por_dia_positive",
        ),
    )

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    tipo: Mapped[str] = mapped_column(String(20), nullable=False)

    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Activa")

    instancia: Mapped[str] = mapped_column(String(200), nullable=False)

    dias_disponibles: Mapped[int] = mapped_column(Integer, nullable=False)

    cupo_por_dia: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Evaluacion id={self.id} tenant_id={self.tenant_id} "
            f"tipo={self.tipo!r} estado={self.estado!r}>"
        )

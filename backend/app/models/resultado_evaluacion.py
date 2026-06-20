"""
app/models/resultado_evaluacion.py — ResultadoEvaluacion domain entity.

Records the final outcome (nota) for an alumno in a specific evaluation.

Fields:
  evaluacion_id — FK to evaluacion.id
  alumno_id     — FK to usuarios.id
  nota_final    — free-text grade (numeric or qualitative)

Uniqueness: UNIQUE (evaluacion_id, alumno_id) — one result per alumno per evaluation.

Implemented: C-14 (evaluaciones-y-coloquios)
"""
from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class ResultadoEvaluacion(BaseTenantModel):
    """Final grade record for an alumno in a specific evaluation.

    Columns beyond BaseTenantModel:
        evaluacion_id — FK to evaluacion.id (NOT NULL, index)
        alumno_id     — FK to usuarios.id (NOT NULL)
        nota_final    — free-text grade value (varchar 100)

    Note: UNIQUE constraint (evaluacion_id, alumno_id) is created by
    the Alembic migration (partial unique with deleted_at IS NULL semantics).
    """

    __tablename__ = "resultado_evaluacion"

    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    alumno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    nota_final: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<ResultadoEvaluacion id={self.id} tenant_id={self.tenant_id} "
            f"evaluacion_id={self.evaluacion_id} alumno_id={self.alumno_id} "
            f"nota_final={self.nota_final!r}>"
        )

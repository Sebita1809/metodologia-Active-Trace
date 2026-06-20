"""
app/models/calificacion.py — Calificacion domain entity.

Stores a grade (numeric or textual) for an alumno on a specific activity,
derived from a padron entry.

FK references:
  entrada_padron_id → entrada_padron.id (RESTRICT)
  materia_id        → materias.id (RESTRICT)

Fields:
  nota_numerica — numeric grade (Numeric 5,2), nullable
  nota_textual  — textual grade (varchar 200), nullable
  aprobado      — computed approval flag (Boolean)
  origen        — "Importado" or "Manual"
  importado_at  — timestamp of LMS import (nullable)

Implemented: C-10 (calificaciones-y-umbral)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class Calificacion(BaseTenantModel):
    """Grade record for a single alumno × activity pair.

    Columns beyond BaseTenantModel:
        entrada_padron_id — FK to entrada_padron.id (RESTRICT, NOT NULL, index)
        materia_id        — FK to materias.id (RESTRICT, NOT NULL)
        actividad         — name of the graded activity (varchar 300)
        nota_numerica     — numeric grade (nullable)
        nota_textual      — textual grade (nullable)
        aprobado          — True if the grade meets the approval threshold
        origen            — source of the grade: "Importado" or "Manual"
        importado_at      — UTC timestamp of LMS import (nullable)
    """

    __tablename__ = "calificacion"

    entrada_padron_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entrada_padron.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materias.id", ondelete="RESTRICT"),
        nullable=False,
    )

    actividad: Mapped[str] = mapped_column(String(300), nullable=False)

    nota_numerica: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    nota_textual: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    aprobado: Mapped[bool] = mapped_column(Boolean, nullable=False)

    origen: Mapped[str] = mapped_column(String(20), nullable=False)

    importado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Calificacion id={self.id} tenant_id={self.tenant_id} "
            f"entrada_padron_id={self.entrada_padron_id} actividad={self.actividad!r}>"
        )

"""
app/models/guardia.py — Guardia domain entity (E11).

Represents a TUTOR's office-hour / guard shift associated with an Asignacion,
Materia, Carrera and Cohorte. Created by TUTOR; queried/exported by
COORDINADOR/ADMIN.

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class EstadoGuardia(StrEnum):
    """Valid states for a Guardia.

    StrEnum → VARCHAR storage, no PG ENUM migration required.
    """

    Pendiente = "Pendiente"
    Realizada = "Realizada"
    Cancelada = "Cancelada"


class Guardia(BaseTenantModel):
    """Tutor office-hours / guard shift record.

    Columns beyond BaseTenantModel:
        asignacion_id — FK to asignaciones.id (NOT NULL)
        materia_id    — FK to materias.id (NOT NULL)
        carrera_id    — FK to carreras.id (NOT NULL)
        cohorte_id    — FK to cohortes.id (NOT NULL)
        dia           — day of the week (VARCHAR CHECK)
        horario       — free-text time range, e.g. "14:00–14:45"
        estado        — current state (EstadoGuardia)
        comentarios   — free-text notes
        creada_at     — server-side creation timestamp (NOT NULL, set once on INSERT)
    """

    __tablename__ = "guardia"

    __table_args__ = (
        CheckConstraint(
            "dia IN ('Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo')",
            name="ck_guardia_dia_valid",
        ),
        CheckConstraint(
            "estado IN ('Pendiente','Realizada','Cancelada')",
            name="ck_guardia_estado_valid",
        ),
    )

    asignacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asignaciones.id", ondelete="RESTRICT"),
        nullable=False,
    )

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materias.id", ondelete="RESTRICT"),
        nullable=False,
    )

    carrera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carreras.id", ondelete="RESTRICT"),
        nullable=False,
    )

    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohortes.id", ondelete="RESTRICT"),
        nullable=False,
    )

    dia: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Day of week",
    )

    horario: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Free-text time range, e.g. '14:00–14:45'",
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EstadoGuardia.Pendiente,
        server_default="Pendiente",
    )

    comentarios: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    creada_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Server-side creation timestamp; set once on INSERT",
    )

    def __repr__(self) -> str:
        return (
            f"<Guardia id={self.id} tenant_id={self.tenant_id} "
            f"dia={self.dia!r} estado={self.estado!r}>"
        )

"""
app/models/slot_encuentro.py — SlotEncuentro domain entity (E9).

Represents a recurring or one-time meeting slot for an Asignacion.
Two mutually exclusive creation modes (RN-13):
  - Recurrente: cant_semanas > 0 + dia_semana + fecha_inicio → N InstanciaEncuentro
  - Único: fecha_unica + hora → 1 InstanciaEncuentro con slot_id=NULL

Validation of RN-13 exclusivity lives in the Service layer (not here).

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import uuid
from datetime import date, time
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class DiaSemana(StrEnum):
    """Valid days of the week for SlotEncuentro.dia_semana.

    StrEnum means values are plain strings — safe to store as VARCHAR,
    no PostgreSQL ENUM type needed (avoids painful migrations on additions).
    """

    Lunes = "Lunes"
    Martes = "Martes"
    Miercoles = "Miércoles"
    Jueves = "Jueves"
    Viernes = "Viernes"
    Sabado = "Sábado"
    Domingo = "Domingo"


class SlotEncuentro(BaseTenantModel):
    """Meeting slot (recurring or one-time) for an Asignacion.

    Columns beyond BaseTenantModel:
        asignacion_id — FK to asignaciones.id (NOT NULL)
        materia_id    — FK to materias.id (NOT NULL)
        titulo        — descriptive title
        hora          — time of the meeting (TIME); nullable for recurrent slots
        dia_semana    — day of the week (VARCHAR CHECK); NULL for unique mode
        fecha_inicio  — start date for recurrence; NULL for unique mode
        cant_semanas  — number of weeks to recur (0 = unique mode)
        fecha_unica   — specific date for unique-mode slots (nullable)
        meet_url      — video-conference URL
        vig_desde     — slot validity start date
        vig_hasta     — slot validity end date
    """

    __tablename__ = "slot_encuentro"

    __table_args__ = (
        CheckConstraint(
            "dia_semana IN ('Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo')",
            name="ck_slot_encuentro_dia_semana_valid",
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

    titulo: Mapped[str] = mapped_column(String(300), nullable=False)

    hora: Mapped[time | None] = mapped_column(Time, nullable=True)

    dia_semana: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Day of week for recurrence; NULL in unique mode",
    )

    fecha_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)

    cant_semanas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="0 = unique mode; > 0 = recur for N weeks",
    )

    fecha_unica: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Specific date for unique-mode slots",
    )

    meet_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    vig_desde: Mapped[date | None] = mapped_column(Date, nullable=True)

    vig_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<SlotEncuentro id={self.id} tenant_id={self.tenant_id} "
            f"titulo={self.titulo!r} cant_semanas={self.cant_semanas}>"
        )

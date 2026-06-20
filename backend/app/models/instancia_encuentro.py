"""
app/models/instancia_encuentro.py — InstanciaEncuentro domain entity (E10).

One row per concrete meeting occurrence. Created by:
  - EncuentroService.crear_slot_recurrente → N rows, each with slot_id set (RN-13.1)
  - EncuentroService.crear_encuentro_unico → 1 row with slot_id=NULL (RN-13.2)

State is independent per instance (RN-14): editing one instance never touches
the SlotEncuentro or any sibling instances.

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import uuid
from datetime import date, time
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class EstadoInstancia(StrEnum):
    """Valid states for an InstanciaEncuentro (RN-14).

    StrEnum → VARCHAR storage, no PG ENUM migration required.
    """

    Programado = "Programado"
    Realizado = "Realizado"
    Cancelado = "Cancelado"


class InstanciaEncuentro(BaseTenantModel):
    """Concrete meeting occurrence — one row per date/time.

    Columns beyond BaseTenantModel:
        slot_id    — FK to slot_encuentro.id (nullable; NULL for unique encounters)
        materia_id — FK to materias.id (NOT NULL, for quick tenant-scoped queries)
        fecha      — date of the meeting
        hora       — time of the meeting
        titulo     — title of this specific occurrence
        estado     — current state (EstadoInstancia)
        meet_url   — URL for this occurrence (may differ from slot default)
        video_url  — recording URL, set after the meeting (nullable)
        comentario — free-text notes
    """

    __tablename__ = "instancia_encuentro"

    __table_args__ = (
        CheckConstraint(
            "estado IN ('Programado','Realizado','Cancelado')",
            name="ck_instancia_encuentro_estado_valid",
        ),
    )

    slot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("slot_encuentro.id", ondelete="RESTRICT"),
        nullable=True,
        comment="NULL for unique encounters (RN-13.2)",
    )

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materias.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fecha: Mapped[date] = mapped_column(Date, nullable=False)

    hora: Mapped[time] = mapped_column(Time, nullable=False)

    titulo: Mapped[str] = mapped_column(String(300), nullable=False)

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EstadoInstancia.Programado,
        server_default="Programado",
    )

    meet_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    video_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Recording URL — set after meeting is realizado",
    )

    comentario: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<InstanciaEncuentro id={self.id} tenant_id={self.tenant_id} "
            f"fecha={self.fecha} estado={self.estado!r}>"
        )

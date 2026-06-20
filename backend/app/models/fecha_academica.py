"""
app/models/fecha_academica.py — FechaAcademica domain entity (E15).

Represents a scheduled evaluative instance (parcial, TP, coloquio, etc.)
for a materia × cohorte combination.

TipoFechaAcademica is a StrEnum — stored as VARCHAR(20) + CheckConstraint,
NOT a PG ENUM type. Consistent with EstadoTarea (C-16) and EstadoGuardia (C-13).

Clave natural: (tenant_id, materia_id, cohorte_id, tipo, numero).
Unique partial index in migration (WHERE deleted_at IS NULL).

Implemented: C-17 (programas-y-fechas-academicas)
"""
from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class TipoFechaAcademica(StrEnum):
    """Valid tipos for a FechaAcademica.

    StrEnum → VARCHAR storage; no PG ENUM migration required.
    Consistent with EstadoTarea (C-16).
    """

    Parcial = "Parcial"
    TP = "TP"
    Coloquio = "Coloquio"
    Recuperatorio = "Recuperatorio"


class FechaAcademica(BaseTenantModel):
    """Scheduled evaluative instance for materia × cohorte (E15).

    Columns beyond BaseTenantModel:
        materia_id — FK → materias.id RESTRICT
        cohorte_id — FK → cohortes.id RESTRICT
        tipo       — TipoFechaAcademica (VARCHAR + CheckConstraint)
        numero     — instance number >= 1 (1st parcial, 2nd parcial, etc.)
        periodo    — optional period descriptor (e.g. "2026-1")
        fecha      — calendar date (DATE column, not timestamp)
        titulo     — descriptive title (required)
    """

    __tablename__ = "fecha_academica"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('Parcial','TP','Coloquio','Recuperatorio')",
            name="ck_fecha_academica_tipo_valid",
        ),
        CheckConstraint(
            "numero >= 1",
            name="ck_fecha_academica_numero_positivo",
        ),
    )

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materias.id", ondelete="RESTRICT"),
        nullable=False,
    )

    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohortes.id", ondelete="RESTRICT"),
        nullable=False,
    )

    tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    numero: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    periodo: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    fecha: Mapped[object] = mapped_column(
        Date,
        nullable=False,
    )

    titulo: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<FechaAcademica id={self.id} tenant_id={self.tenant_id} "
            f"materia_id={self.materia_id} tipo={self.tipo!r} numero={self.numero}>"
        )

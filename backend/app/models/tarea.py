"""
app/models/tarea.py — Tarea domain entity (E12).

Represents an internal task with assignment, delegation and state machine.
Soft delete, timestamps and tenant isolation from BaseTenantModel.

EstadoTarea is StrEnum (VARCHAR + CHECK) — NOT PG ENUM type.
Consistent with EstadoGuardia (C-13).

Implemented: C-16 (tareas-internas)
"""
from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class EstadoTarea(StrEnum):
    """Valid states for a Tarea.

    StrEnum → VARCHAR storage, no PG ENUM migration required.
    Transitions enforced by TareaService (D2).
    """

    Pendiente = "Pendiente"
    EnProgreso = "En progreso"
    Resuelta = "Resuelta"
    Cancelada = "Cancelada"


class Tarea(BaseTenantModel):
    """Internal task entity (E12).

    Columns beyond BaseTenantModel:
        materia_id   — nullable FK to materias.id (institutional-level task when NULL)
        asignado_a   — FK to usuarios.id (current assignee)
        asignado_por — FK to usuarios.id (original assigner; set from JWT, never updated)
        estado       — current state (EstadoTarea; CheckConstraint)
        descripcion  — task description text
        contexto_id  — nullable UUID opaque poly-ref (no FK, best-effort reference)
    """

    __tablename__ = "tarea"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('Pendiente','En progreso','Resuelta','Cancelada')",
            name="ck_tarea_estado_valid",
        ),
    )

    materia_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materias.id", ondelete="RESTRICT"),
        nullable=True,
    )

    asignado_a: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    asignado_por: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EstadoTarea.Pendiente,
        server_default="Pendiente",
    )

    descripcion: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    contexto_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Tarea id={self.id} tenant_id={self.tenant_id} "
            f"estado={self.estado!r} asignado_a={self.asignado_a}>"
        )

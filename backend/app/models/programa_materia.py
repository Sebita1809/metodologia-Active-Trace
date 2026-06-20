"""
app/models/programa_materia.py — ProgramaMateria domain entity (E16).

Represents the official programme document for a materia within a specific
carrera × cohorte combination. One vivo programme per combo per tenant.

Soft delete + append-only replacement: if a combo already has a vivo
programme, the service soft-deletes it before inserting a new one.

referencia_archivo is a fully opaque string — no binary upload logic here.

Implemented: C-17 (programas-y-fechas-academicas)
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class ProgramaMateria(BaseTenantModel):
    """Official programme document for a materia × carrera × cohorte combo (E16).

    Columns beyond BaseTenantModel:
        materia_id         — FK → materias.id RESTRICT
        carrera_id         — FK → carreras.id RESTRICT
        cohorte_id         — FK → cohortes.id RESTRICT
        titulo             — descriptive title (required)
        referencia_archivo — opaque string pointing to an external storage service
    """

    __tablename__ = "programa_materia"

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

    titulo: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    referencia_archivo: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ProgramaMateria id={self.id} tenant_id={self.tenant_id} "
            f"materia_id={self.materia_id} carrera_id={self.carrera_id} "
            f"cohorte_id={self.cohorte_id}>"
        )

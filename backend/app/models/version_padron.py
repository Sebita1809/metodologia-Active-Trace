"""
app/models/version_padron.py — VersionPadron domain entity.

Cabecera de una versión del padrón de alumnos. Cada carga genera una
nueva VersionPadron; solo una puede estar activa por (tenant, materia, cohorte).
La restricción "una activa" se garantiza vía índice único parcial en la DB
y transaccionalmente en PadronService.

Campos:
  materia_id   — FK a materias.id (RESTRICT)
  cohorte_id   — FK a cohortes.id (RESTRICT)
  cargado_por  — FK a usuarios.id (RESTRICT); quién realizó la carga
  cargado_at   — timestamp de la carga (UTC)
  activa        — True = versión en uso; False = versión histórica
  origen        — "archivo" | "moodle"

PII: ninguna en esta tabla.
__repr__: nunca expone PII.

Implemented: C-09 (padron-ingesta-moodle)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class VersionPadron(BaseTenantModel):
    """Cabecera de una versión del padrón de alumnos.

    Columns beyond BaseTenantModel:
        materia_id   — FK to materias.id (RESTRICT)
        cohorte_id   — FK to cohortes.id (RESTRICT)
        cargado_por  — FK to usuarios.id (RESTRICT)
        cargado_at   — UTC timestamp of the load
        activa        — whether this is the current active version
        origen        — "archivo" | "moodle"
    """

    __tablename__ = "version_padron"

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohortes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    cargado_por: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    cargado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    activa: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    origen: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    def __repr__(self) -> str:
        """No PII in repr."""
        return (
            f"<VersionPadron id={self.id} tenant_id={self.tenant_id} "
            f"materia_id={self.materia_id} cohorte_id={self.cohorte_id} "
            f"activa={self.activa} origen={self.origen!r}>"
        )

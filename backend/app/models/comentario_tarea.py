"""
app/models/comentario_tarea.py — ComentarioTarea domain entity (E12).

Append-only comment thread associated with a Tarea.
creado_at is server-side (func.now()); never set from caller.
autor_id ALWAYS from JWT — never from request body (D7).

Soft delete available via BaseTenantModel for consistency,
but UX is append-only (comments are never edited or deleted by users).

Implemented: C-16 (tareas-internas)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class ComentarioTarea(BaseTenantModel):
    """Append-only comment on a Tarea (E12).

    Columns beyond BaseTenantModel:
        tarea_id  — FK to tarea.id RESTRICT (owning task)
        autor_id  — FK to usuarios.id RESTRICT (always from JWT)
        texto     — comment text
        creado_at — server-side creation timestamp (set once on INSERT)
    """

    __tablename__ = "comentario_tarea"

    tarea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tarea.id", ondelete="RESTRICT"),
        nullable=False,
    )

    autor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    texto: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    creado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Server-side creation timestamp; set once on INSERT",
    )

    def __repr__(self) -> str:
        return (
            f"<ComentarioTarea id={self.id} tarea_id={self.tarea_id} "
            f"autor_id={self.autor_id}>"
        )

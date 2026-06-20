"""
app/models/mensaje.py — Mensaje (internal messaging) domain entity.

Internal messages between registered users of the same tenant, organized
by thread_id. Distinct from Comunicacion (outbound email queue to students).

Security notes:
  - __repr__ NEVER exposes cuerpo (message body).
  - remitente_id is ALWAYS set from the JWT in the service layer.
  - Filtered by tenant_id + participant in the repository layer.

Implemented: C-20 (perfil-y-mensajeria-interna)
"""
from __future__ import annotations

import uuid

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class Mensaje(BaseTenantModel):
    """Internal message between two registered users of the same tenant.

    Columns:
        thread_id       — UUID grouping messages into a conversation thread
        remitente_id    — FK to usuarios; always set from JWT (never from body)
        destinatario_id — FK to usuarios
        asunto          — subject line; present on root message, nullable on replies
        cuerpo          — message body (plaintext operational text, not PII)
        leido_at        — NULL until the recipient reads the thread
        creado_at       — server-side timestamp on INSERT (via BaseTenantModel.created_at)
    """

    __tablename__ = "mensajes"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    remitente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    destinatario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    asunto: Mapped[str | None] = mapped_column(Text, nullable=True)
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)

    leido_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    def __repr__(self) -> str:
        """NEVER expose cuerpo in repr."""
        return (
            f"<Mensaje id={self.id} thread_id={self.thread_id} "
            f"remitente_id={self.remitente_id} destinatario_id={self.destinatario_id}>"
        )

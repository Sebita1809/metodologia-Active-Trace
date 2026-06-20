"""
app/models/comunicacion.py — Comunicacion domain entity (E21).

Stores outgoing communications in a stateful queue. State machine (RN-15):
  Pendiente → Enviando    (worker picks the message)
  Pendiente → Cancelado   (manual cancellation)
  Enviando  → Enviado     (channel confirms OK)
  Enviando  → Error       (channel fails)

All other transitions are invalid (enforced in the service layer via
comunicacion_estado.py, not here — model only stores the field).

PII: `destinatario` (email) is ALWAYS stored as AES-256-GCM ciphertext.
     Encryption/decryption lives in the service layer (CryptoService).

Approval flag (D-02): `aprobado_at` / `aprobado_por` are orthogonal to the
lifecycle. When a tenant requires approval, the worker only dispatches
Pendiente messages that have aprobado_at IS NOT NULL.

Implemented: C-12 (comunicaciones-cola-worker)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class EstadoComunicacion(StrEnum):
    """Valid states for a Comunicacion (RN-15).

    Using str+Enum allows the value to be stored/serialised as a plain
    string (VARCHAR) in PostgreSQL, which avoids migrations when states
    need to be added in future changes.

    States:
        Pendiente  — created, waiting to be dispatched
        Enviando   — worker is dispatching it right now
        Enviado    — channel confirmed delivery
        Error      — channel failed (terminal for this version)
        Cancelado  — cancelled before dispatch
    """

    Pendiente = "Pendiente"
    Enviando = "Enviando"
    Enviado = "Enviado"
    Error = "Error"
    Cancelado = "Cancelado"


class Comunicacion(BaseTenantModel):
    """Outgoing communication record — one row per recipient per batch (lote).

    Columns beyond BaseTenantModel:
        enviado_por   — FK to usuarios.id; the actor who enqueued the message
        materia_id    — FK to materias.id; context for the communication
        destinatario  — AES-256-GCM ciphertext of the recipient email (PII)
        asunto        — message subject (plain text)
        cuerpo        — message body (may contain rendered template)
        estado        — current state (EstadoComunicacion), default Pendiente
        lote_id       — groups all messages created in one encolar_lote call
        enviado_at    — UTC timestamp set when the message reaches Enviado
        aprobado_at   — UTC timestamp set when an approver approves (nullable)
        aprobado_por  — FK to usuarios.id; the approver (nullable)
    """

    __tablename__ = "comunicacion"

    enviado_por: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materias.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # PII: stored as AES-256-GCM ciphertext — see D-03 in design.md
    destinatario: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="PII cifrada AES-256-GCM (email del alumno destinatario)",
    )

    asunto: Mapped[str] = mapped_column(String(500), nullable=False)

    cuerpo: Mapped[str] = mapped_column(String(10000), nullable=False)

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EstadoComunicacion.Pendiente,
        server_default="Pendiente",
    )

    lote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    enviado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Approval flag (orthogonal to lifecycle — D-02)
    aprobado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    aprobado_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
        default=None,
    )

    def __repr__(self) -> str:
        return (
            f"<Comunicacion id={self.id} tenant_id={self.tenant_id} "
            f"estado={self.estado!r} lote_id={self.lote_id}>"
        )

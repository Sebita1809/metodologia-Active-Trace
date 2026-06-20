"""
app/models/acknowledgment_aviso.py — AcknowledgmentAviso domain entity.

Records when a user has acknowledged (read-confirmed) a notice that requires ACK.
The UNIQUE constraint on (aviso_id, usuario_id) prevents duplicate acknowledgments.

Soft delete, timestamps and tenant isolation from BaseTenantModel.

Implemented: C-15 (avisos-y-acknowledgment)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class AcknowledgmentAviso(BaseTenantModel):
    """Record of a user's acknowledgment of a notice.

    Columns:
        aviso_id       — FK to aviso.id (NOT NULL)
        usuario_id     — FK to usuarios.id (NOT NULL)
        confirmado_at  — UTC timestamp when acknowledgment was created (server_default=now())

    Constraints:
        UNIQUE (aviso_id, usuario_id) — one acknowledgment per user per aviso
    """

    __tablename__ = "acknowledgment_aviso"
    __table_args__ = (
        UniqueConstraint("aviso_id", "usuario_id", name="uq_ack_aviso_usuario"),
    )

    aviso_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("aviso.id", ondelete="RESTRICT"),
        nullable=False,
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    confirmado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

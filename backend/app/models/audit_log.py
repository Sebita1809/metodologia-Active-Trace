"""AuditLog model — append-only audit trail for all domain operations."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_log"
    __mapper_args__ = {"polymorphic_identity": "audit_log"}
    __table_args__ = (
        Index("ix_audit_log_tenant_fecha", "tenant_id", "created_at"),
        Index("ix_audit_log_actor", "actor_id"),
        Index("ix_audit_log_accion", "accion"),
    )

    # Override: NOT NULL, no FK (logical reference only)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )

    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    impersonado_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True
    )
    materia_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    accion: Mapped[str] = mapped_column(String(50), nullable=False)
    detalle: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    filas_afectadas: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

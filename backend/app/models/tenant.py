"""Tenant model — root entity for multi-tenant isolation."""

import enum
import uuid

from sqlalchemy import JSON, Boolean, Integer, String, Uuid, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TenantEstado(str, enum.Enum):
    ACTIVO = "Activo"
    INACTIVO = "Inactivo"


class Tenant(BaseModel):
    __tablename__ = "tenant"
    __mapper_args__ = {"polymorphic_identity": "tenant"}

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("tenant.id", ondelete="SET NULL"),
        nullable=True,
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    codigo: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    estado: Mapped[TenantEstado] = mapped_column(
        String(20), default=TenantEstado.ACTIVO, nullable=False
    )
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)

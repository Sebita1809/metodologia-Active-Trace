"""
app/models/tenant.py — Tenant entity: the root of row-level multi-tenant isolation.

Tenant is the only top-level entity that does NOT inherit BaseTenantModel
(it has no tenant_id — it IS the tenant). Every other domain model FK-references
tenants.id via BaseTenantModel.tenant_id.

Decision reference: ADR-002 (row-level tenant isolation), C-02 design D1.

Implemented: C-02 (core-models-y-tenancy)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Tenant(Base):
    """Tenant — root entity for multi-tenant isolation.

    Columns:
        id         — UUID PK (gen_random_uuid)
        slug       — short URL-safe identifier, unique across the system
        nombre     — human-readable name for the institution
        activo     — whether the tenant accepts new sessions (default True)
        created_at — UTC timestamp set on INSERT
        updated_at — UTC timestamp updated on every UPDATE
        deleted_at — NULL=alive; NOT NULL=soft-deleted
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id!s:.8} slug={self.slug!r} activo={self.activo}>"

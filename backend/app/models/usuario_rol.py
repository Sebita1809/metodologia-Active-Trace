"""
app/models/usuario_rol.py — UsuarioRol assignment entity.

Links a User to a Rol within a tenant, with temporal validity.
An assignment is active if: vigente_desde <= now < vigente_hasta (or vigente_hasta IS NULL).
Expired assignments are kept for audit history (never hard-deleted).

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class UsuarioRol(BaseTenantModel):
    """Temporal assignment of a Rol to a User within a tenant.

    Inherits: id (UUID PK), tenant_id (FK), created_at, updated_at, deleted_at.

    Columns:
        user_id        — FK → users.id
        rol_id         — FK → roles.id
        vigente_desde  — UTC datetime when the assignment became active
        vigente_hasta  — UTC datetime when the assignment expires (NULL = open-ended)

    Index: (tenant_id, user_id) — fast lookup of all roles for a user in a tenant.
    """

    __tablename__ = "usuario_rol"

    __table_args__ = (
        Index("ix_usuario_rol_tenant_user", "tenant_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    rol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )

    vigente_desde: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    vigente_hasta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    def __repr__(self) -> str:
        return (
            f"<UsuarioRol user={self.user_id!s:.8} rol={self.rol_id!s:.8}"
            f" desde={self.vigente_desde} hasta={self.vigente_hasta} tenant={self.tenant_id!s:.8}>"
        )

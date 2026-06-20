"""
app/models/rol_permiso.py — RolPermiso N:N join entity.

Links a Rol to a Permiso with an `alcance` marker (global | propio).
The matrix is stored as data, never hardcoded.

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class AlcanceEnum(str, enum.Enum):
    """Scope marker for a role → permission assignment.

    global — the permission applies to all resources in the tenant.
    propio — the permission applies only to the user's own resources.
    """

    global_ = "global"
    propio = "propio"

    # Override __str__ so SQLAlchemy stores the plain value ("global", "propio")
    def __str__(self) -> str:
        return self.value


class RolPermiso(BaseTenantModel):
    """Association between a Rol and a Permiso with an alcance marker.

    Inherits: id (UUID PK), tenant_id (FK), created_at, updated_at, deleted_at.

    Columns:
        rol_id    — FK → roles.id
        permiso_id — FK → permisos.id
        alcance   — 'global' | 'propio' (default 'global')

    Unique: (tenant_id, rol_id, permiso_id) — one assignment per pair per tenant.
    """

    __tablename__ = "rol_permiso"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "rol_id", "permiso_id",
            name="uq_rol_permiso_tenant_rol_permiso",
        ),
    )

    rol_id: Mapped[object] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )

    permiso_id: Mapped[object] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permisos.id", ondelete="CASCADE"),
        nullable=False,
    )

    alcance: Mapped[AlcanceEnum] = mapped_column(
        SAEnum(AlcanceEnum, name="alcance_enum", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=AlcanceEnum.global_,
        server_default="global",
    )

    def __repr__(self) -> str:
        return (
            f"<RolPermiso rol={self.rol_id!s:.8} permiso={self.permiso_id!s:.8}"
            f" alcance={self.alcance} tenant={self.tenant_id!s:.8}>"
        )

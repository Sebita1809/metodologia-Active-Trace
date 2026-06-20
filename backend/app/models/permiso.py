"""
app/models/permiso.py — Permiso domain entity.

A Permiso represents an atomic capability in the format `modulo:accion`.
The clave column is the canonical key referenced by endpoint guards.
Each permiso is unique per tenant.

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class Permiso(BaseTenantModel):
    """Atomic capability in the RBAC catalog, keyed by `modulo:accion`.

    Inherits: id (UUID PK), tenant_id (FK), created_at, updated_at, deleted_at.

    Columns:
        clave       — canonical key `modulo:accion`, unique within tenant
        modulo      — module name (left-hand side of the colon)
        accion      — action name (right-hand side of the colon)
        descripcion — optional human-readable description
    """

    __tablename__ = "permisos"

    __table_args__ = (
        UniqueConstraint("tenant_id", "clave", name="uq_permisos_tenant_clave"),
    )

    clave: Mapped[str] = mapped_column(String(100), nullable=False)
    modulo: Mapped[str] = mapped_column(String(50), nullable=False)
    accion: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<Permiso id={self.id!s:.8} clave={self.clave!r} tenant={self.tenant_id!s:.8}>"

"""
app/models/rol.py — Rol domain entity.

Each Rol belongs to a tenant and represents a named function within the system.
The 7 domain roles (ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS)
are seeded by the migration; the catalog is extensible per tenant.

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class Rol(BaseTenantModel):
    """A named function/role within a tenant's RBAC catalog.

    Inherits: id (UUID PK), tenant_id (FK), created_at, updated_at, deleted_at.

    Columns:
        nombre      — role name, unique within the tenant
        descripcion — optional human-readable description
    """

    __tablename__ = "roles"

    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_roles_tenant_nombre"),
    )

    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<Rol id={self.id!s:.8} nombre={self.nombre!r} tenant={self.tenant_id!s:.8}>"

"""Rol model — roles for fine-grained RBAC.

Seed roles (ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS)
are global catalog entries with tenant_id=NULL.
Tenant-specific roles are created at runtime with a real tenant_id.
"""

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Rol(BaseModel):
    __tablename__ = "rol"
    __mapper_args__ = {"polymorphic_identity": "rol"}
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_rol_tenant_nombre"),
    )

    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)

"""RolPermiso model — many-to-many assignment of permissions to roles.

The optional :attr:`alcance` column stores scope metadata (e.g. ``"propio"``)
to indicate that the permission only applies to the user's own resources.
"""

import uuid

from sqlalchemy import ForeignKey, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class RolPermiso(BaseModel):
    __tablename__ = "rol_permiso"
    __mapper_args__ = {"polymorphic_identity": "rol_permiso"}
    __table_args__ = (
        UniqueConstraint("rol_id", "permiso_id", name="uq_rol_permiso"),
    )

    rol_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("rol.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permiso_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("permiso.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alcance: Mapped[str | None] = mapped_column(String(50), nullable=True)

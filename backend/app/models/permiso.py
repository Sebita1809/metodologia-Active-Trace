"""Permiso model — fine-grained permissions catalog (global, no tenant scope).

Each permission is identified by a unique ``codigo`` in ``modulo:accion`` format
(e.g. ``calificaciones:importar``). The :attr:`modulo` and :attr:`accion` columns
enable grouped lookups (e.g. all actions in ``calificaciones``).
"""

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Permiso(BaseModel):
    __tablename__ = "permiso"
    __mapper_args__ = {"polymorphic_identity": "permiso"}
    __table_args__ = (
        Index("ix_permiso_modulo_accion", "modulo", "accion"),
    )

    codigo: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    modulo: Mapped[str] = mapped_column(String(50), nullable=False)
    accion: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)

"""EntradaPadron model — individual student entry within a version of the roster."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class EntradaPadron(BaseModel):
    __tablename__ = "entrada_padron"

    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("version_padron.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(500), nullable=False)
    comision: Mapped[str | None] = mapped_column(String(100), nullable=True)
    regional: Mapped[str | None] = mapped_column(String(255), nullable=True)

    version = relationship("VersionPadron", back_populates="entradas")
    usuario = relationship("Usuario")

    def __repr__(self) -> str:
        return (
            f"<EntradaPadron id={self.id} version_id={self.version_id} "
            f"email={self.email[:16]}...>"
        )

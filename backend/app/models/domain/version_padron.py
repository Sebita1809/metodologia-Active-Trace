"""VersionPadron model — snapshot version of student roster for a subject+cohort."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class VersionPadron(BaseModel):
    __tablename__ = "version_padron"

    materia_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("materia.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cohorte.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    activa: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    origen: Mapped[str] = mapped_column(String(20), nullable=False)
    cargado_por: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False
    )
    cargado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    materia = relationship("Materia")
    cohorte = relationship("Cohorte")
    cargador = relationship("Usuario", foreign_keys=[cargado_por])
    entradas = relationship("EntradaPadron", back_populates="version")

    def __repr__(self) -> str:
        return (
            f"<VersionPadron id={self.id} materia_id={self.materia_id} "
            f"cohorte_id={self.cohorte_id} activa={self.activa}>"
        )

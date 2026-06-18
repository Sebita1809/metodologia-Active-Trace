"""Asignacion model — role assignment with academic context and validity."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Asignacion(BaseModel):
    __tablename__ = "asignacion"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rol: Mapped[str] = mapped_column(String(100), nullable=False)
    materia_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("materia.id", ondelete="RESTRICT"), nullable=True
    )
    carrera_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("carrera.id", ondelete="RESTRICT"), nullable=True
    )
    cohorte_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("cohorte.id", ondelete="RESTRICT"), nullable=True
    )
    comisiones: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    responsable_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True
    )
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)

    @property
    def estado_vigencia(self) -> str:
        today = datetime.now(timezone.utc).date()
        if self.desde <= today and (self.hasta is None or self.hasta >= today):
            return "vigente"
        return "vencida"

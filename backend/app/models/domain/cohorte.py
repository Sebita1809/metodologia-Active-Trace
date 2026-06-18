"""Cohorte model — cohort/course edition within a degree program."""

import uuid

from sqlalchemy import Date, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import EstadoGenerico
from app.models.base import BaseModel


class Cohorte(BaseModel):
    carrera_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("carrera.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    vig_desde: Mapped[str] = mapped_column(Date, nullable=False)
    vig_hasta: Mapped[str | None] = mapped_column(Date, nullable=True)
    estado: Mapped[EstadoGenerico] = mapped_column(
        String(20), default=EstadoGenerico.ACTIVA, nullable=False
    )

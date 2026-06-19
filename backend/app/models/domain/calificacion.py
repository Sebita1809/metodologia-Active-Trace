"""Calificacion model — student grades for evaluable activities."""
import uuid
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Numeric, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class OrigenCalificacion(str, enum.Enum):
    IMPORTADO = "Importado"
    MANUAL = "Manual"


class Calificacion(BaseModel):
    __tablename__ = "calificacion"

    entrada_padron_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("entrada_padron.id", ondelete="CASCADE"), nullable=False
    )
    materia_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("materia.id", ondelete="CASCADE"), nullable=False
    )
    actividad: Mapped[str] = mapped_column(String(255), nullable=False)
    nota_numerica: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    nota_textual: Mapped[str | None] = mapped_column(String(100), nullable=True)
    origen: Mapped[OrigenCalificacion] = mapped_column(
        Enum(OrigenCalificacion, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OrigenCalificacion.IMPORTADO,
    )
    importado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

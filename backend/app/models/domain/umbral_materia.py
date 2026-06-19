"""UmbralMateria model — per-teacher per-subject grading threshold."""
import uuid

from sqlalchemy import ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class UmbralMateria(BaseModel):
    __tablename__ = "umbral_materia"

    asignacion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("asignacion.id", ondelete="CASCADE"), nullable=False
    )
    materia_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("materia.id", ondelete="CASCADE"), nullable=False
    )
    umbral_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

"""Materia model — subject in the academic catalogue."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import EstadoGenerico
from app.models.base import BaseModel


class Materia(BaseModel):
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[EstadoGenerico] = mapped_column(
        String(20), default=EstadoGenerico.ACTIVA, nullable=False
    )

"""Usuario model — academic identity with PII encrypted at rest."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import EstadoGenerico
from app.models.base import BaseModel


class Usuario(BaseModel):
    __tablename__ = "usuario"

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(500), nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dni: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cuil: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cbu: Mapped[str | None] = mapped_column(String(500), nullable=True)
    alias_cbu: Mapped[str | None] = mapped_column(String(500), nullable=True)
    banco: Mapped[str | None] = mapped_column(String(255), nullable=True)
    regional: Mapped[str | None] = mapped_column(String(255), nullable=True)
    legajo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    legajo_profesional: Mapped[str | None] = mapped_column(String(100), nullable=True)
    facturador: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    estado: Mapped[EstadoGenerico] = mapped_column(
        String(20), default=EstadoGenerico.ACTIVA, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Usuario id={self.id} email_hash={self.email_hash[:16]}...>"

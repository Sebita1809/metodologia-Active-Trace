"""
app/models/entrada_padron.py — EntradaPadron domain entity.

Cada fila del padrón dentro de una VersionPadron. Un alumno puede
aparecer en el padrón sin tener cuenta en el sistema (usuario_id nullable).

PII:
  email — almacenado como ciphertext AES-256-GCM. Cifrado/descifrado
          EXCLUSIVAMENTE en la capa de servicio (PadronService).
          __repr__ NUNCA expone email ni usuario_id de forma que
          permita identificar a la persona.

Campos:
  version_id  — FK a version_padron.id (RESTRICT)
  usuario_id  — FK a usuarios.id (RESTRICT, nullable); NULL si el alumno no tiene cuenta
  nombre      — nombre de pila (texto plano)
  apellidos   — apellidos (texto plano)
  email       — ciphertext AES-256-GCM del email normalizado
  comision    — comisión asignada (texto plano, nullable)
  regional    — regional de la institución (texto plano, nullable)

Implemented: C-09 (padron-ingesta-moodle)
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class EntradaPadron(BaseTenantModel):
    """Fila del padrón de alumnos vinculada a una VersionPadron.

    Columns beyond BaseTenantModel:
        version_id  — FK to version_padron.id (RESTRICT)
        usuario_id  — FK to usuarios.id (RESTRICT, nullable)
        nombre      — plaintext first name
        apellidos   — plaintext last name(s)
        email       — AES-256-GCM ciphertext of normalized email (PII)
        comision    — comision label (plaintext, nullable)
        regional    — regional branch (plaintext, nullable)
    """

    __tablename__ = "entrada_padron"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("version_padron.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(200), nullable=False)

    # PII — stored as AES-256-GCM ciphertext; decrypted ONLY in service layer
    email: Mapped[str] = mapped_column(Text, nullable=False)

    comision: Mapped[str | None] = mapped_column(String(100), nullable=True)
    regional: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        """NEVER expose email or any PII in repr."""
        return (
            f"<EntradaPadron id={self.id} tenant_id={self.tenant_id} "
            f"version_id={self.version_id}>"
        )

"""
app/models/usuario.py — Usuario domain entity.

Represents a person profile with encrypted PII. Each tenant has its own
isolated set of usuarios. Email uniqueness is enforced via HMAC-SHA256 hash.

PII fields (email, dni, cuil, cbu, alias_cbu) are stored as AES-256-GCM
ciphertext — encryption/decryption happens ONLY in the Service layer.

Security notes:
  - __repr__ NEVER exposes PII fields.
  - email_hash is a deterministic HMAC of normalized email (lowercase+strip).
  - email_hash is NEVER included in API responses.

Implemented: C-07 (usuarios-y-asignaciones)
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseTenantModel


class Usuario(BaseTenantModel):
    """Person profile with encrypted PII.

    Columns:
        nombre               — display first name (plaintext)
        apellidos            — display last name (plaintext)
        email                — AES-256-GCM ciphertext of normalized email
        email_hash           — HMAC-SHA256 of normalized email; enforces uniqueness per tenant
        dni                  — AES-256-GCM ciphertext (nullable)
        cuil                 — AES-256-GCM ciphertext (nullable)
        cbu                  — AES-256-GCM ciphertext (nullable)
        alias_cbu            — AES-256-GCM ciphertext (nullable)
        banco                — bank name (plaintext, nullable)
        regional             — regional branch (plaintext, nullable)
        legajo               — administrative file number (plaintext, nullable)
        legajo_profesional   — professional file number (plaintext, nullable)
        facturador           — whether user can issue invoices (default False)
        estado               — "Activo" | "Inactivo" (default "Activo")
    """

    __tablename__ = "usuarios"

    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(200), nullable=False)

    # PII — stored as AES-256-GCM ciphertext; decrypted ONLY in service layer
    email: Mapped[str] = mapped_column(Text, nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Optional PII — nullable ciphertexts
    dni: Mapped[str | None] = mapped_column(Text, nullable=True)
    cuil: Mapped[str | None] = mapped_column(Text, nullable=True)
    cbu: Mapped[str | None] = mapped_column(Text, nullable=True)
    alias_cbu: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Non-PII optional fields
    banco: Mapped[str | None] = mapped_column(String(100), nullable=True)
    regional: Mapped[str | None] = mapped_column(String(100), nullable=True)
    legajo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    legajo_profesional: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # C-20: self-service profile fields
    sexo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    modalidad_cobro: Mapped[str | None] = mapped_column(String(20), nullable=True)

    facturador: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Activo")

    # Relationship — eager loading controlled by repository
    # Must specify foreign_keys because Asignacion has two FKs to usuarios
    # (usuario_id and responsable_id), and we want the usuario_id relationship.
    asignaciones: Mapped[list["Asignacion"]] = relationship(
        "Asignacion",
        foreign_keys="Asignacion.usuario_id",
        lazy="select",
    )

    def __repr__(self) -> str:
        """NEVER expose PII fields in repr."""
        return f"<Usuario id={self.id} tenant_id={self.tenant_id}>"

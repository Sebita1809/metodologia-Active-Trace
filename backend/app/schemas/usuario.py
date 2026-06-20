"""
app/schemas/usuario.py — Pydantic v2 DTOs for the Usuario API.

Security rules:
  - email_hash NEVER appears in UsuarioResponse or any response schema.
  - All schemas use extra='forbid' to reject undeclared fields.

Implemented: C-07 (usuarios-y-asignaciones)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# UsuarioRolItem
# ---------------------------------------------------------------------------

class UsuarioRolItem(BaseModel):
    """A single role assignment extracted from Asignacion."""
    rol: str
    materia: str | None = None
    vigencia: str | None = None


# ---------------------------------------------------------------------------
# UsuarioCreate
# ---------------------------------------------------------------------------

class UsuarioCreate(_Base):
    """Body for POST /api/admin/usuarios — PII in plaintext (encrypted by service)."""
    nombre: str = Field(min_length=1, max_length=200)
    apellidos: str = Field(min_length=1, max_length=200)
    email: EmailStr
    dni: str | None = Field(default=None, max_length=20)
    cuil: str | None = Field(default=None, max_length=20)
    cbu: str | None = Field(default=None, max_length=30)
    alias_cbu: str | None = Field(default=None, max_length=100)
    banco: str | None = Field(default=None, max_length=100)
    regional: str | None = Field(default=None, max_length=100)
    legajo: str | None = Field(default=None, max_length=50)
    legajo_profesional: str | None = Field(default=None, max_length=50)
    sexo: str | None = Field(default=None, max_length=50)
    modalidad_cobro: Literal["Factura", "Liquidacion"] | None = None
    facturador: bool = False
    estado: Literal["Activo", "Inactivo"] = "Activo"


# ---------------------------------------------------------------------------
# UsuarioUpdate
# ---------------------------------------------------------------------------

class UsuarioUpdate(_Base):
    """Body for PATCH /api/admin/usuarios/{id} — all fields optional (PATCH semantics)."""
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    apellidos: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    dni: str | None = Field(default=None, max_length=20)
    cuil: str | None = Field(default=None, max_length=20)
    cbu: str | None = Field(default=None, max_length=30)
    alias_cbu: str | None = Field(default=None, max_length=100)
    banco: str | None = Field(default=None, max_length=100)
    regional: str | None = Field(default=None, max_length=100)
    legajo: str | None = Field(default=None, max_length=50)
    legajo_profesional: str | None = Field(default=None, max_length=50)
    sexo: str | None = Field(default=None, max_length=50)
    modalidad_cobro: Literal["Factura", "Liquidacion"] | None = None
    facturador: bool | None = None
    estado: Literal["Activo", "Inactivo"] | None = None


# ---------------------------------------------------------------------------
# UsuarioResponse
# ---------------------------------------------------------------------------

class UsuarioResponse(_Base):
    """Response DTO — PII decrypted by service; email_hash NEVER included."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    nombre: str
    apellidos: str
    email: str          # decrypted plaintext
    dni: str | None
    cuil: str | None
    cbu: str | None
    alias_cbu: str | None
    banco: str | None
    regional: str | None
    legajo: str | None
    legajo_profesional: str | None
    sexo: str | None
    modalidad_cobro: str | None
    facturador: bool
    estado: str
    roles: list[UsuarioRolItem] = []
    created_at: datetime
    updated_at: datetime

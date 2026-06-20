"""
app/schemas/perfil.py — Pydantic v2 DTOs for the self-service profile API.

Security rules:
  - email_hash NEVER appears in PerfilResponse.
  - PerfilUpdate does NOT declare `cuil` — sending it raises HTTP 422.
  - All schemas use extra='forbid' to reject undeclared fields.
  - `modalidad_cobro` must be 'Factura' or 'Liquidacion' (or None).

Implemented: C-20 (perfil-y-mensajeria-interna)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class PerfilResponse(_Base):
    """Response for GET /api/perfil — PII decrypted; email_hash NEVER included."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    nombre: str
    apellidos: str
    email: str
    dni: str | None
    cuil: str | None          # read-only from this endpoint
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
    created_at: datetime
    updated_at: datetime


class PerfilUpdate(_Base):
    """Body for PATCH /api/perfil — editable fields only.

    cuil is intentionally ABSENT: extra='forbid' makes sending it a 422.
    """
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    apellidos: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    sexo: str | None = Field(default=None, max_length=50)
    banco: str | None = Field(default=None, max_length=100)
    cbu: str | None = Field(default=None, max_length=30)
    alias_cbu: str | None = Field(default=None, max_length=100)
    regional: str | None = Field(default=None, max_length=100)
    legajo_profesional: str | None = Field(default=None, max_length=50)
    modalidad_cobro: Literal["Factura", "Liquidacion"] | None = None

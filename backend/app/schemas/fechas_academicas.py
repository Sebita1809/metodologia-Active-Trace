"""
app/schemas/fechas_academicas.py — Pydantic schemas for FechaAcademica (C-17).

Schemas:
  FechaAcademicaCreate  — input for creating a new fecha (no tenant_id)
  FechaAcademicaUpdate  — partial update (fecha, titulo, periodo only)
  FechaAcademicaResponse — full response including all persisted fields
  FragmentoLmsResponse   — LMS fragment (materia_id, cohorte_id, formato, contenido)

All schemas use ConfigDict(extra='forbid') — rejects undeclared fields.
tenant_id is NEVER accepted in input schemas; it is derived from the JWT.

Implemented: C-17 (programas-y-fechas-academicas)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.fecha_academica import TipoFechaAcademica


class FechaAcademicaCreate(BaseModel):
    """Input schema for creating a new fecha académica.

    tenant_id intentionally excluded — derived from JWT session.
    numero must be >= 1 (validated here; also enforced by DB CheckConstraint).
    """

    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: TipoFechaAcademica
    numero: int
    fecha: date
    titulo: str
    periodo: str | None = None

    @field_validator("numero")
    @classmethod
    def numero_positivo(cls, v: int) -> int:
        if v < 1:
            raise ValueError("numero must be >= 1")
        return v


class FechaAcademicaUpdate(BaseModel):
    """Partial update schema — only fecha, titulo and periodo can be changed."""

    model_config = ConfigDict(extra="forbid")

    fecha: date | None = None
    titulo: str | None = None
    periodo: str | None = None


class FechaAcademicaResponse(BaseModel):
    """Full response schema for a FechaAcademica record."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: str
    numero: int
    periodo: str | None = None
    fecha: date
    titulo: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class FragmentoLmsResponse(BaseModel):
    """LMS fragment response — formatted content ready to paste in the LMS."""

    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    formato: str  # "html" or "texto"
    contenido: str

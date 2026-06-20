"""
app/schemas/programas.py — Pydantic schemas for ProgramaMateria (C-17).

Schemas:
  ProgramaCreate  — input for creating/replacing a programme (no tenant_id)
  ProgramaResponse — full response including all persisted fields
  ProgramaFiltros  — optional query filters for listing

All schemas use ConfigDict(extra='forbid') — rejects undeclared fields.
tenant_id is NEVER accepted in the input schemas; it is derived from the JWT.

Implemented: C-17 (programas-y-fechas-academicas)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProgramaCreate(BaseModel):
    """Input schema for creating or replacing a programme.

    tenant_id intentionally excluded — it is always derived from the JWT session.
    """

    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    titulo: str
    referencia_archivo: str


class ProgramaResponse(BaseModel):
    """Full response schema for a ProgramaMateria record."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    titulo: str
    referencia_archivo: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class ProgramaFiltros(BaseModel):
    """Optional filters for listing programmes."""

    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID | None = None
    carrera_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None

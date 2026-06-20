"""
app/schemas/materia.py — Pydantic v2 DTOs for the Materia catalog API.

All schemas use `extra='forbid'` (project rule — no undeclared fields accepted).

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# MateriaCreate
# ---------------------------------------------------------------------------

class MateriaCreate(_Base):
    """Body for POST /api/admin/materias"""
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=200)
    estado: Literal["Activa", "Inactiva"] = "Activa"


# ---------------------------------------------------------------------------
# MateriaUpdate
# ---------------------------------------------------------------------------

class MateriaUpdate(_Base):
    """Body for PATCH /api/admin/materias/{id} — all fields optional (PATCH semantics)."""
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    estado: Literal["Activa", "Inactiva"] | None = None


# ---------------------------------------------------------------------------
# MateriaResponse
# ---------------------------------------------------------------------------

class MateriaResponse(_Base):
    """Response DTO for a single Materia."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    codigo: str
    nombre: str
    estado: str
    created_at: datetime
    updated_at: datetime

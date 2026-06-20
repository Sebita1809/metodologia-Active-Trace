"""
app/schemas/cohorte.py — Pydantic v2 DTOs for the Cohorte catalog API.

All schemas use `extra='forbid'` (project rule — no undeclared fields accepted).

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# CohorteCreate
# ---------------------------------------------------------------------------

class CohorteCreate(_Base):
    """Body for POST /api/admin/cohortes"""
    carrera_id: uuid.UUID
    nombre: str = Field(min_length=1, max_length=100)
    anio: int = Field(ge=1900, le=2100)
    vig_desde: date
    vig_hasta: date | None = None
    estado: Literal["Activa", "Inactiva"] = "Activa"


# ---------------------------------------------------------------------------
# CohorteUpdate
# ---------------------------------------------------------------------------

class CohorteUpdate(_Base):
    """Body for PATCH /api/admin/cohortes/{id} — all fields optional (PATCH semantics)."""
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    anio: int | None = Field(default=None, ge=1900, le=2100)
    vig_desde: date | None = None
    vig_hasta: date | None = None
    estado: Literal["Activa", "Inactiva"] | None = None


# ---------------------------------------------------------------------------
# CohorteResponse
# ---------------------------------------------------------------------------

class CohorteResponse(_Base):
    """Response DTO for a single Cohorte."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    carrera_id: uuid.UUID
    nombre: str
    anio: int
    vig_desde: date
    vig_hasta: date | None
    estado: str
    created_at: datetime
    updated_at: datetime

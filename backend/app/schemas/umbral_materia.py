"""
app/schemas/umbral_materia.py — Pydantic v2 schemas for umbral_materia endpoints.

All schemas use ConfigDict(extra='forbid') as per project rules.

Implemented: C-10 (calificaciones-y-umbral)
"""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------

class _StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# UmbralMateriaRead — response schema
# ---------------------------------------------------------------------------

class UmbralMateriaRead(_StrictBase):
    """Response schema for an umbral_materia record."""

    id: uuid.UUID
    asignacion_id: uuid.UUID
    materia_id: uuid.UUID
    umbral_pct: int
    valores_aprobatorios: list[str]

    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# UmbralMateriaUpsert — request schema
# ---------------------------------------------------------------------------

class UmbralMateriaUpsert(_StrictBase):
    """Request body for creating or updating an umbral_materia record.

    Defaults match the business rules from RN-01/RN-02:
      umbral_pct=60, valores_aprobatorios=["Satisfactorio", "Supera lo esperado"]
    """

    umbral_pct: int = Field(default=60, ge=0, le=100)
    valores_aprobatorios: list[str] = Field(
        default_factory=lambda: ["Satisfactorio", "Supera lo esperado"]
    )

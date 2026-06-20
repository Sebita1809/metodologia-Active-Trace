"""
app/schemas/avisos.py — Pydantic v2 DTOs for the Avisos API (C-15).

All schemas use extra='forbid' to reject undeclared fields.
Model validators enforce context-field consistency (alcance ↔ materia_id/cohorte_id/rol_destino).

Implemented: C-15 (avisos-y-acknowledgment)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# AvisoCreate
# ---------------------------------------------------------------------------

class AvisoCreate(_Base):
    """Body for POST /api/avisos/ — create a new aviso.

    Validation:
      - alcance=PorMateria  → materia_id required
      - alcance=PorCohorte  → cohorte_id required
      - alcance=PorRol      → rol_destino required
    """

    alcance: str = Field(..., description="Global | PorMateria | PorCohorte | PorRol")
    materia_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    rol_destino: str | None = None
    severidad: str = Field(default="Info", description="Info | Advertencia | Critico")
    titulo: str = Field(..., min_length=1, max_length=300)
    cuerpo: str = Field(..., min_length=1, max_length=10000)
    inicio_en: datetime
    fin_en: datetime
    orden: int = Field(default=0)
    activo: bool = Field(default=True)
    requiere_ack: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_alcance_fields(self) -> Self:
        """Enforce that required context field is present for each alcance."""
        if self.alcance == "PorMateria" and self.materia_id is None:
            raise ValueError("materia_id es requerido cuando alcance=PorMateria")
        if self.alcance == "PorCohorte" and self.cohorte_id is None:
            raise ValueError("cohorte_id es requerido cuando alcance=PorCohorte")
        if self.alcance == "PorRol" and self.rol_destino is None:
            raise ValueError("rol_destino es requerido cuando alcance=PorRol")
        return self


# ---------------------------------------------------------------------------
# AvisoUpdate
# ---------------------------------------------------------------------------

class AvisoUpdate(_Base):
    """Body for PATCH /api/avisos/{id} — partial update of an aviso.

    All fields optional. Same alcance consistency rule applies when alcance is provided.
    """

    alcance: str | None = None
    materia_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    rol_destino: str | None = None
    severidad: str | None = None
    titulo: str | None = Field(default=None, min_length=1, max_length=300)
    cuerpo: str | None = Field(default=None, min_length=1, max_length=10000)
    inicio_en: datetime | None = None
    fin_en: datetime | None = None
    orden: int | None = None
    activo: bool | None = None
    requiere_ack: bool | None = None

    @model_validator(mode="after")
    def validate_alcance_fields(self) -> Self:
        """Enforce context field consistency when alcance is updated."""
        if self.alcance == "PorMateria" and self.materia_id is None:
            raise ValueError("materia_id es requerido cuando alcance=PorMateria")
        if self.alcance == "PorCohorte" and self.cohorte_id is None:
            raise ValueError("cohorte_id es requerido cuando alcance=PorCohorte")
        if self.alcance == "PorRol" and self.rol_destino is None:
            raise ValueError("rol_destino es requerido cuando alcance=PorRol")
        return self


# ---------------------------------------------------------------------------
# AvisoResponse — full aviso detail (used by admin endpoints)
# ---------------------------------------------------------------------------

class AvisoResponse(_Base):
    """Full aviso representation returned by admin endpoints.

    Includes total_acks count (computed by repository).
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    alcance: str
    materia_id: uuid.UUID | None
    cohorte_id: uuid.UUID | None
    rol_destino: str | None
    severidad: str
    titulo: str
    cuerpo: str
    inicio_en: datetime
    fin_en: datetime
    orden: int
    activo: bool
    requiere_ack: bool
    created_at: datetime
    updated_at: datetime
    total_acks: int = Field(default=0, description="Total acknowledgments for this aviso")


# ---------------------------------------------------------------------------
# AvisoListItem — subset for mis-avisos (authenticated user's notice feed)
# ---------------------------------------------------------------------------

class AvisoListItem(_Base):
    """Aviso representation in the 'mis-avisos' feed (no total_acks exposed)."""

    id: uuid.UUID
    alcance: str
    severidad: str
    titulo: str
    cuerpo: str
    inicio_en: datetime
    fin_en: datetime
    orden: int
    activo: bool
    requiere_ack: bool


# ---------------------------------------------------------------------------
# AckResponse — acknowledgment creation result
# ---------------------------------------------------------------------------

class AckResponse(_Base):
    """Response from POST /api/avisos/{id}/ack."""

    aviso_id: uuid.UUID
    usuario_id: uuid.UUID
    confirmado_at: datetime

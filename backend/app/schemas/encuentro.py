"""
app/schemas/encuentro.py — Pydantic v2 schemas for slots and encuentros (C-13).

All schemas use ConfigDict(extra='forbid') — extra fields are rejected.
Request schemas: data from the client → validated, never contain identity fields.
Response schemas: data to the client → safe to expose.

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import uuid
from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# SlotEncuentro schemas
# ---------------------------------------------------------------------------

class SlotRecurrenteRequest(BaseModel):
    """Request body for POST /api/v1/slots (recurrent mode, RN-13.1)."""

    model_config = ConfigDict(extra="forbid")

    asignacion_id: uuid.UUID
    materia_id: uuid.UUID
    titulo: str = Field(..., min_length=1, max_length=300)
    dia_semana: str = Field(
        ...,
        description=(
            "Día de la semana: Lunes | Martes | Miércoles | "
            "Jueves | Viernes | Sábado | Domingo"
        ),
    )
    fecha_inicio: date
    cant_semanas: int = Field(..., ge=1, le=52)
    hora: time
    meet_url: str | None = Field(default=None, max_length=500)
    vig_desde: date | None = None
    vig_hasta: date | None = None


class SlotEncuentroRead(BaseModel):
    """Response schema for SlotEncuentro."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    asignacion_id: uuid.UUID
    materia_id: uuid.UUID
    titulo: str
    dia_semana: str | None
    fecha_inicio: date | None
    cant_semanas: int
    hora: time | None
    meet_url: str | None
    vig_desde: date | None
    vig_hasta: date | None


# ---------------------------------------------------------------------------
# InstanciaEncuentro schemas
# ---------------------------------------------------------------------------

class EncuentroUnicoRequest(BaseModel):
    """Request body for POST /api/v1/encuentros (unique mode, RN-13.2)."""

    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    titulo: str = Field(..., min_length=1, max_length=300)
    fecha_unica: date
    hora: time
    meet_url: str | None = Field(default=None, max_length=500)


class EditarInstanciaRequest(BaseModel):
    """Request body for PATCH /api/v1/encuentros/{id} (RN-14)."""

    model_config = ConfigDict(extra="forbid")

    estado: str | None = Field(
        default=None,
        description="Programado | Realizado | Cancelado",
    )
    meet_url: str | None = Field(default=None, max_length=500)
    video_url: str | None = Field(default=None, max_length=500)
    comentario: str | None = Field(default=None, max_length=2000)


class InstanciaEncuentroRead(BaseModel):
    """Response schema for InstanciaEncuentro."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    slot_id: uuid.UUID | None
    materia_id: uuid.UUID
    fecha: date
    hora: time
    titulo: str
    estado: str
    meet_url: str | None
    video_url: str | None
    comentario: str | None


# ---------------------------------------------------------------------------
# Compound response for slot creation
# ---------------------------------------------------------------------------

class SlotCreadoResponse(BaseModel):
    """Response for POST /api/v1/slots: slot + generated instancias."""

    model_config = ConfigDict(extra="forbid")

    slot: SlotEncuentroRead
    instancias: list[InstanciaEncuentroRead]

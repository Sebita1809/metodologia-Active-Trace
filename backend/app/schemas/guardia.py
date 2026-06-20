"""
app/schemas/guardia.py — Pydantic v2 schemas for Guardia (C-13).

All schemas use ConfigDict(extra='forbid') — extra fields are rejected.
Request schemas: client data → validated, no identity fields allowed.
Response schemas: data to client → safe to expose.

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GuardiaRequest(BaseModel):
    """Request body for POST /api/v1/guardias."""

    model_config = ConfigDict(extra="forbid")

    asignacion_id: uuid.UUID
    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    dia: str = Field(
        ...,
        description=(
            "Día de la semana: Lunes | Martes | Miércoles | "
            "Jueves | Viernes | Sábado | Domingo"
        ),
    )
    horario: str = Field(
        ...,
        max_length=50,
        description="Free-text time range, e.g. '14:00–14:45'",
    )
    estado: str | None = Field(
        default=None,
        description="Pendiente | Realizada | Cancelada — defaults to Pendiente",
    )
    comentarios: str | None = Field(default=None, max_length=2000)


class GuardiaRead(BaseModel):
    """Response schema for Guardia."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    asignacion_id: uuid.UUID
    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    dia: str
    horario: str
    estado: str
    comentarios: str | None
    creada_at: datetime

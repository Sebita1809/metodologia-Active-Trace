"""
app/schemas/calificacion.py — Pydantic v2 schemas for calificaciones endpoints.

All schemas use ConfigDict(extra='forbid') as per project rules.

Implemented: C-10 (calificaciones-y-umbral)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------

class _StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Enum: origen
# ---------------------------------------------------------------------------

class OrigenEnum(str, Enum):
    importado = "Importado"
    manual = "Manual"


# ---------------------------------------------------------------------------
# CalificacionRead — response schema
# ---------------------------------------------------------------------------

class CalificacionRead(_StrictBase):
    """Response schema for a single calificacion record."""

    id: uuid.UUID
    entrada_padron_id: uuid.UUID
    materia_id: uuid.UUID
    actividad: str
    nota_numerica: Decimal | None
    nota_textual: str | None
    aprobado: bool
    origen: OrigenEnum
    importado_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# Import preview / confirm
# ---------------------------------------------------------------------------

class ActividadDetectada(_StrictBase):
    """A detected activity from an LMS grades export."""

    nombre: str
    tipo: str  # "numerica" or "textual"


class ImportPreviewResponse(_StrictBase):
    """Response for the import preview endpoint — no DB writes."""

    actividades_numericas: list[str]
    actividades_textuales: list[str]
    alumnos_detectados: int


class ImportConfirmRequest(_StrictBase):
    """Request body for the import confirm endpoint.

    asignacion_id and actividades_seleccionadas are business data.
    Identity and tenant come exclusively from the JWT.
    """

    asignacion_id: uuid.UUID
    actividades_seleccionadas: list[str]


# ---------------------------------------------------------------------------
# Finalizacion preview
# ---------------------------------------------------------------------------

class FinalizacionItem(_StrictBase):
    """A single item in the finalizacion preview — textual activities only."""

    alumno_email: str
    actividad: str


class FinalizacionPreviewResponse(_StrictBase):
    """Response for the finalizacion preview endpoint."""

    items: list[FinalizacionItem]

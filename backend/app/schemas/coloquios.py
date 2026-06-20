"""
app/schemas/coloquios.py — Pydantic v2 schemas for coloquios endpoints.

All schemas use ConfigDict(extra='forbid') as per project rules.

Implemented: C-14 (evaluaciones-y-coloquios)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------

class _StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Evaluacion schemas
# ---------------------------------------------------------------------------

class EvaluacionCreate(_StrictBase):
    """Request body for creating a new evaluacion.

    materia_id, cohorte_id, tipo, instancia, dias_disponibles, cupo_por_dia
    are business data. tenant_id comes exclusively from the JWT.
    """

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: str
    instancia: str
    dias_disponibles: int
    cupo_por_dia: int

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: str) -> str:
        valid = {"Parcial", "TP", "Coloquio", "Recuperatorio"}
        if v not in valid:
            raise ValueError(f"tipo must be one of {valid}")
        return v

    @field_validator("dias_disponibles")
    @classmethod
    def validate_dias(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("dias_disponibles must be positive")
        return v

    @field_validator("cupo_por_dia")
    @classmethod
    def validate_cupo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("cupo_por_dia must be positive")
        return v


class EvaluacionRead(_StrictBase):
    """Response schema for a single evaluacion record."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: str
    estado: str
    instancia: str
    dias_disponibles: int
    cupo_por_dia: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class EvaluacionConMetricas(_StrictBase):
    """Evaluacion with computed cupos_libres per day."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: str
    estado: str
    instancia: str
    dias_disponibles: int
    cupo_por_dia: int
    created_at: datetime
    updated_at: datetime
    # Computed
    cupos_libres_hoy: int

    model_config = ConfigDict(extra="forbid", from_attributes=False)


class MetricasPanel(_StrictBase):
    """Aggregated metrics for the coloquios dashboard panel."""

    total_evaluaciones: int
    total_reservas_activas: int
    total_resultados: int
    evaluaciones_cerradas: int


# ---------------------------------------------------------------------------
# Padron import schemas
# ---------------------------------------------------------------------------

class PadronAlumnoItem(_StrictBase):
    """A single alumno entry in the padron import."""

    alumno_id: uuid.UUID


class ImportarPadronRequest(_StrictBase):
    """Request body for bulk-importing alumnos into an evaluacion."""

    alumnos: list[PadronAlumnoItem]


class ImportarPadronResponse(_StrictBase):
    """Response for the padron import endpoint."""

    importados: int
    omitidos: int


# ---------------------------------------------------------------------------
# ReservaEvaluacion schemas
# ---------------------------------------------------------------------------

class ReservarRequest(_StrictBase):
    """Request body for creating a reserva.

    alumno_id comes from JWT — NOT from body.
    fecha_hora is the desired slot.
    """

    fecha_hora: datetime


class ReservaEvaluacionRead(_StrictBase):
    """Response schema for a single reserva_evaluacion record."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    evaluacion_id: uuid.UUID
    alumno_id: uuid.UUID
    fecha_hora: datetime
    estado: str
    created_at: datetime

    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# ResultadoEvaluacion schemas
# ---------------------------------------------------------------------------

class RegistrarResultadoRequest(_StrictBase):
    """Request body for registering a resultado.

    alumno_id and nota_final are business data.
    tenant_id comes from JWT.
    """

    alumno_id: uuid.UUID
    nota_final: str


class ResultadoEvaluacionRead(_StrictBase):
    """Response schema for a single resultado_evaluacion record."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    evaluacion_id: uuid.UUID
    alumno_id: uuid.UUID
    nota_final: str
    created_at: datetime

    model_config = ConfigDict(extra="forbid", from_attributes=True)

"""Pydantic schemas for grade import and threshold configuration."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ── Calificacion ─────────────────────────────────────────────────


class CalificacionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entrada_padron_id: uuid.UUID
    actividad: str
    nota_numerica: float | None = None
    nota_textual: str | None = None


class CalificacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: uuid.UUID
    tenant_id: uuid.UUID
    entrada_padron_id: uuid.UUID
    materia_id: uuid.UUID
    actividad: str
    nota_numerica: float | None = None
    nota_textual: str | None = None
    origen: str
    importado_at: datetime
    created_at: datetime
    updated_at: datetime
    aprobado: bool | None = None


class CalificacionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calificaciones: list[CalificacionResponse]
    total: int


# ── Import ──────────────────────────────────────────────────────


class ImportPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_token: str
    actividades_detectadas: list[dict]
    total_filas: int
    sample_rows: list[dict]


class ImportConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_token: str
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    selected_actividades: list[str]


class ImportConfirmResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calificaciones_creadas: int
    estudiantes: int


# ── Umbral ──────────────────────────────────────────────────────


class UmbralConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    materia_id: uuid.UUID
    asignacion_id: uuid.UUID
    umbral_pct: int | None = None
    valores_aprobatorios: list[str] | None = None


class UmbralConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: uuid.UUID
    asignacion_id: uuid.UUID
    materia_id: uuid.UUID
    umbral_pct: int
    valores_aprobatorios: list[str] | None = None


__all__ = [
    "CalificacionCreate",
    "CalificacionResponse",
    "CalificacionListResponse",
    "ImportPreviewResponse",
    "ImportConfirmRequest",
    "ImportConfirmResponse",
    "UmbralConfigUpdate",
    "UmbralConfigResponse",
]

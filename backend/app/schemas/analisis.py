"""
app/schemas/analisis.py — Pydantic v2 schemas for analisis endpoints.

All schemas use ConfigDict(extra='forbid') as per project rules.

Implemented: C-11 (analisis-atrasados-reportes)
Updated:     C-23 (monitor-general) — MonitorGeneralItem, MonitorGeneralResponse
"""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class _StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# 1. Atrasados
# ---------------------------------------------------------------------------

class AlumnoAtrasado(_StrictBase):
    alumno_id: uuid.UUID
    nombre: str
    apellidos: str
    actividades_faltantes: list[str]
    actividades_reprobadas: list[str]


class AtrasadosResponse(_StrictBase):
    atrasados: list[AlumnoAtrasado]
    sin_padron: bool


# ---------------------------------------------------------------------------
# 2. Ranking
# ---------------------------------------------------------------------------

class RankingItem(_StrictBase):
    alumno_id: uuid.UUID
    nombre: str
    apellidos: str
    aprobadas: int


class RankingResponse(_StrictBase):
    items: list[RankingItem]


# ---------------------------------------------------------------------------
# 3. Notas finales
# ---------------------------------------------------------------------------

class NotaFinalItem(_StrictBase):
    alumno_id: uuid.UUID
    nombre: str
    apellidos: str
    aprobadas: int
    total_actividades: int
    porcentaje_aprobacion: float


class NotasFinalesResponse(_StrictBase):
    items: list[NotaFinalItem]


# ---------------------------------------------------------------------------
# 4. Reporte
# ---------------------------------------------------------------------------

class ReporteAsignacion(_StrictBase):
    total_alumnos: int
    total_atrasados: int
    pct_aprobacion_general: float
    total_actividades: int
    tiene_datos: bool


# ---------------------------------------------------------------------------
# 5. Monitor general (F2.7) — C-23
# ---------------------------------------------------------------------------

class MonitorGeneralItem(_StrictBase):
    alumno_id: uuid.UUID
    nombre: str
    apellidos: str
    email: str
    materia: str
    comision: str | None
    cohorte: str
    actividades_aprobadas: int
    actividades_totales: int
    estado: str  # "al_dia" | "atrasado" | "sin_datos"


class MonitorGeneralResponse(_StrictBase):
    items: list[MonitorGeneralItem]
    total: int

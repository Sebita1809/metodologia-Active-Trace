"""
app/schemas/equipo.py — Pydantic v2 DTOs for the Equipo API (C-08).

All schemas use extra='forbid' to reject undeclared fields.
estado_vigencia is a derived field (computed by service, never persisted).

Implemented: C-08 (equipos-docentes)
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# EquipoContextRef — shared context reference (materia + optional carrera/cohorte)
# ---------------------------------------------------------------------------

class EquipoContextRef(_Base):
    """Reference to an academic context for team operations."""
    materia_id: uuid.UUID
    carrera_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# MiEquipoItem — single assignment in the "mis equipos" response
# ---------------------------------------------------------------------------

class MiEquipoItem(_Base):
    """One assignment returned by GET /api/equipos/mis-equipos."""
    id: uuid.UUID
    usuario_id: uuid.UUID
    rol: str
    materia_id: uuid.UUID | None
    carrera_id: uuid.UUID | None
    cohorte_id: uuid.UUID | None
    comisiones: list[str]
    desde: date
    hasta: date | None
    estado_vigencia: Literal["Vigente", "Vencida"]
    responsable_id: uuid.UUID | None


# ---------------------------------------------------------------------------
# AsignacionMasivaRequest / AsignacionMasivaResponse
# ---------------------------------------------------------------------------

class AsignacionMasivaRequest(_Base):
    """Body for POST /api/equipos/asignaciones/masiva."""
    usuario_ids: list[uuid.UUID] = Field(min_length=1)
    rol: str
    materia_id: uuid.UUID | None = None
    carrera_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    comisiones: list[str] = Field(default_factory=list)
    desde: date
    hasta: date | None = None


class AsignacionMasivaResponse(_Base):
    """Response from POST /api/equipos/asignaciones/masiva."""
    asignadas: int


# ---------------------------------------------------------------------------
# ClonarEquipoRequest / ClonarEquipoResponse
# ---------------------------------------------------------------------------

class ClonarEquipoRequest(_Base):
    """Body for POST /api/equipos/asignaciones/clonar."""
    origen: EquipoContextRef
    destino: EquipoContextRef
    desde: date
    hasta: date | None = None


class ClonarEquipoResponse(_Base):
    """Response from POST /api/equipos/asignaciones/clonar."""
    clonadas: int


# ---------------------------------------------------------------------------
# ModificarVigenciaRequest / ModificarVigenciaResponse
# ---------------------------------------------------------------------------

class ModificarVigenciaRequest(_Base):
    """Body for PATCH /api/equipos/asignaciones/vigencia."""
    filtro: EquipoContextRef
    desde: date
    hasta: date | None = None


class ModificarVigenciaResponse(_Base):
    """Response from PATCH /api/equipos/asignaciones/vigencia."""
    modificadas: int


# ---------------------------------------------------------------------------
# UsuarioBusquedaItem — autocomplete result (no PII exposed)
# ---------------------------------------------------------------------------

class UsuarioBusquedaItem(_Base):
    """Single user result from GET /api/equipos/usuarios/buscar."""
    id: uuid.UUID
    nombre: str
    apellidos: str

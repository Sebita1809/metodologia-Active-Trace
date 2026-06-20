"""
app/schemas/asignacion.py — Pydantic v2 DTOs for the Asignacion API.

estado_vigencia is a derived field (computed by service, never persisted).
All schemas use extra='forbid' to reject undeclared fields.

Implemented: C-07 (usuarios-y-asignaciones)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Business role enum — distinct from RBAC system roles
RolNegocioEnum = Literal["PROFESOR", "TUTOR", "COORDINADOR", "NEXO", "ADMIN", "FINANZAS"]

ROL_NEGOCIO_VALUES: tuple[str, ...] = (
    "PROFESOR", "TUTOR", "COORDINADOR", "NEXO", "ADMIN", "FINANZAS"
)


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# AsignacionCreate
# ---------------------------------------------------------------------------

class AsignacionCreate(_Base):
    """Body for POST /api/asignaciones."""
    usuario_id: uuid.UUID
    rol: RolNegocioEnum
    materia_id: uuid.UUID | None = None
    carrera_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    comisiones: list[str] = Field(default_factory=list)
    responsable_id: uuid.UUID | None = None
    desde: date
    hasta: date | None = None


# ---------------------------------------------------------------------------
# AsignacionUpdate
# ---------------------------------------------------------------------------

class AsignacionUpdate(_Base):
    """Body for PATCH /api/asignaciones/{id} — all fields optional."""
    rol: RolNegocioEnum | None = None
    materia_id: uuid.UUID | None = None
    carrera_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    comisiones: list[str] | None = None
    responsable_id: uuid.UUID | None = None
    desde: date | None = None
    hasta: date | None = None


# ---------------------------------------------------------------------------
# AsignacionResponse
# ---------------------------------------------------------------------------

class AsignacionResponse(_Base):
    """Response DTO — includes derived estado_vigencia."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID
    rol: str
    materia_id: uuid.UUID | None
    carrera_id: uuid.UUID | None
    cohorte_id: uuid.UUID | None
    comisiones: list[str]
    responsable_id: uuid.UUID | None
    desde: date
    hasta: date | None
    estado_vigencia: Literal["Vigente", "Vencida"]
    created_at: datetime
    updated_at: datetime

"""Pydantic schemas for Asignacion entity."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AsignacionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    usuario_id: uuid.UUID
    rol: str
    materia_id: uuid.UUID | None = None
    carrera_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    comisiones: list[str] | None = None
    responsable_id: uuid.UUID | None = None
    desde: date
    hasta: date | None = None


class AsignacionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rol: str | None = None
    materia_id: uuid.UUID | None = None
    carrera_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    comisiones: list[str] | None = None
    responsable_id: uuid.UUID | None = None
    desde: date | None = None
    hasta: date | None = None


class AsignacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
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
    estado_vigencia: str
    created_at: datetime
    updated_at: datetime


__all__ = [
    "AsignacionCreate",
    "AsignacionUpdate",
    "AsignacionResponse",
]

"""Pydantic schemas for academic structure entities: Carrera, Cohorte, Materia."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CarreraCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: str
    nombre: str


class CarreraUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str | None = None
    estado: str | None = None


class CarreraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: uuid.UUID
    tenant_id: uuid.UUID
    codigo: str
    nombre: str
    estado: str
    created_at: datetime
    updated_at: datetime


class CohorteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    carrera_id: uuid.UUID
    nombre: str
    anio: int
    vig_desde: date
    vig_hasta: date | None = None


class CohorteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str | None = None
    carrera_id: uuid.UUID | None = None
    vig_hasta: date | None = None


class CohorteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: uuid.UUID
    tenant_id: uuid.UUID
    carrera_id: uuid.UUID
    nombre: str
    anio: int
    vig_desde: date
    vig_hasta: date | None
    estado: str
    created_at: datetime
    updated_at: datetime


class MateriaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: str
    nombre: str


class MateriaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str | None = None
    estado: str | None = None


class MateriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: uuid.UUID
    tenant_id: uuid.UUID
    codigo: str
    nombre: str
    estado: str
    created_at: datetime
    updated_at: datetime


__all__ = [
    "CarreraCreate",
    "CarreraUpdate",
    "CarreraResponse",
    "CohorteCreate",
    "CohorteUpdate",
    "CohorteResponse",
    "MateriaCreate",
    "MateriaUpdate",
    "MateriaResponse",
]

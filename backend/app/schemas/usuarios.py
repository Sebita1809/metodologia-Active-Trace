"""Pydantic schemas for Usuario entity."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UsuarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str
    apellidos: str
    email: str
    dni: str | None = None
    cuil: str | None = None
    cbu: str | None = None
    alias_cbu: str | None = None
    banco: str | None = None
    regional: str | None = None
    legajo: str | None = None
    legajo_profesional: str | None = None
    facturador: bool = False


class UsuarioUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str | None = None
    apellidos: str | None = None
    email: str | None = None
    dni: str | None = None
    cuil: str | None = None
    cbu: str | None = None
    alias_cbu: str | None = None
    banco: str | None = None
    regional: str | None = None
    legajo: str | None = None
    legajo_profesional: str | None = None
    facturador: bool | None = None


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: uuid.UUID
    tenant_id: uuid.UUID
    nombre: str
    apellidos: str
    email: str
    dni: str | None
    cuil: str | None
    cbu: str | None
    alias_cbu: str | None
    banco: str | None
    regional: str | None
    legajo: str | None
    legajo_profesional: str | None
    facturador: bool
    estado: str
    created_at: datetime
    updated_at: datetime


class UsuarioListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str | None = None


__all__ = [
    "UsuarioCreate",
    "UsuarioUpdate",
    "UsuarioResponse",
    "UsuarioListParams",
]

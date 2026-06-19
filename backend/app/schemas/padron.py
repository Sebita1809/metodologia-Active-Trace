"""Pydantic schemas for padron module: versiones and entradas del padrón."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class VersionPadronResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    activa: bool
    origen: str
    cargado_por: uuid.UUID
    cargado_at: datetime
    created_at: datetime
    updated_at: datetime


class VersionPadronListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    activa: bool
    origen: str
    cargado_por: uuid.UUID
    cargado_at: datetime
    total_entradas: int | None = None


class EntradaPadronResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: uuid.UUID
    version_id: uuid.UUID
    usuario_id: uuid.UUID | None
    nombre: str
    apellidos: str
    email: str
    comision: str | None
    regional: str | None


class EntradaPadronCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str
    apellidos: str
    email: str
    comision: str | None = None
    regional: str | None = None


class VersionPadronCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    origen: str = "archivo"
    entradas: list[EntradaPadronCreate]

    @field_validator("entradas")
    @classmethod
    def validate_entradas_non_empty(cls, v: list) -> list:
        if len(v) < 1:
            raise ValueError("entradas must have at least 1 item")
        return v


class PadronPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_token: str
    column_mapping: dict[str, str]
    total_rows: int
    sample_rows: list[dict]
    errores: list[str]
    columnas_faltantes: list[str]


class PadronImportConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_token: str
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID


class PadronImportConfirmResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_id: uuid.UUID
    total_entradas: int
    entradas_con_usuario: int
    entradas_sin_usuario: int


class PadronClearDataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool = True
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    versiones_eliminadas: int


class PadronSyncMoodleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    moodle_course_id: int


class PadronSyncMoodleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_id: uuid.UUID
    total_entradas: int
    origen: str = "moodle"


__all__ = [
    "VersionPadronResponse",
    "VersionPadronListResponse",
    "EntradaPadronResponse",
    "EntradaPadronCreate",
    "VersionPadronCreate",
    "PadronPreviewResponse",
    "PadronImportConfirmRequest",
    "PadronImportConfirmResponse",
    "PadronClearDataResponse",
    "PadronSyncMoodleRequest",
    "PadronSyncMoodleResponse",
]

"""
app/schemas/padron.py — Pydantic v2 schemas for padron endpoints.

All schemas use ConfigDict(extra='forbid') as per project rules.
Email is NEVER included in error messages or logs — only position/row info.

Implemented: C-09 (padron-ingesta-moodle)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------

class _StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# EntradaPadron (individual padrón row — with decrypted email for responses)
# ---------------------------------------------------------------------------

class EntradaPadronResponse(_StrictBase):
    """Response schema for a single padrón entry.

    Email is included in plaintext (decrypted by the service before returning).
    """

    id: uuid.UUID
    version_id: uuid.UUID
    usuario_id: uuid.UUID | None
    nombre: str
    apellidos: str
    email: str  # decrypted — NEVER log this field
    comision: str | None
    regional: str | None
    created_at: datetime

    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# VersionPadron (version header)
# ---------------------------------------------------------------------------

class VersionPadronResponse(_StrictBase):
    """Response schema for a padrón version header."""

    id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    cargado_por: uuid.UUID
    cargado_at: datetime
    activa: bool
    origen: str
    created_at: datetime

    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

class EntradaParseada(_StrictBase):
    """A single parsed row from an uploaded file (before confirmation).

    Email is included here because the user needs to verify the data.
    The service ensures this only flows to the requesting user's response.
    """

    fila: int = Field(..., description="1-based row number in the source file")
    nombre: str
    apellidos: str
    email: str  # plaintext — NEVER log this field
    comision: str | None = None
    regional: str | None = None


class ErrorParseo(_StrictBase):
    """A parse error for a single row — NEVER includes email value."""

    fila: int = Field(..., description="1-based row number where the error occurred")
    columna: str | None = Field(None, description="Column name if known")
    mensaje: str = Field(..., description="Human-readable error description (no PII)")


class PadronPreviewResponse(_StrictBase):
    """Response for the preview endpoint — parsed entries + errors, nothing persisted."""

    entradas: list[EntradaParseada]
    errores: list[ErrorParseo]
    total_filas: int
    total_errores: int


# ---------------------------------------------------------------------------
# Confirmar (create active version from file)
# ---------------------------------------------------------------------------

class ConfirmarPadronRequest(_StrictBase):
    """Request body for the confirm endpoint.

    materia_id and cohorte_id are business data (not identity).
    Identity/tenant comes exclusively from the JWT.
    """

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID


# ---------------------------------------------------------------------------
# Sync Moodle
# ---------------------------------------------------------------------------

class SyncMoodleRequest(_StrictBase):
    """Request body for the sync-moodle endpoint."""

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    curso_ref: str = Field(..., description="Moodle course reference (e.g. shortname or id)")


# ---------------------------------------------------------------------------
# Vaciar
# ---------------------------------------------------------------------------

class VaciarPadronRequest(_StrictBase):
    """Request body for the vaciar (DELETE) endpoint."""

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID


# ---------------------------------------------------------------------------
# Confirmar response
# ---------------------------------------------------------------------------

class ConfirmarPadronResponse(_StrictBase):
    """Response for the confirmar endpoint."""

    version: VersionPadronResponse
    entradas_cargadas: int
    entradas_sin_match: int  # entries with usuario_id = NULL

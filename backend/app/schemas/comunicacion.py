"""
app/schemas/comunicacion.py — Pydantic v2 schemas for comunicaciones endpoints.

All schemas use ConfigDict(extra='forbid') as per project rules.

Schemas:
  ComunicacionRead        — response schema (destinatario is decrypted email)
  PreviewRequest          — body for POST /preview
  PreviewResponse         — response for POST /preview
  EncolarLoteRequest      — body for POST / (encolar lote)
  EncolarLoteResponse     — response for POST /
  AprobarLoteRequest      — body for POST /aprobar (by lote)
  AprobarItemRequest      — body for POST /aprobar (individual item)
  CancelarLoteRequest     — body for POST /cancelar (by lote)
  CancelarItemRequest     — body for POST /cancelar (individual item)
  ColaQuery               — query params for GET /

Implemented: C-12 (comunicaciones-cola-worker)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.comunicacion import EstadoComunicacion


# ---------------------------------------------------------------------------
# Shared strict base
# ---------------------------------------------------------------------------

class _StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# ComunicacionRead — response schema
# ---------------------------------------------------------------------------

class ComunicacionRead(_StrictBase):
    """Response schema for a single Comunicacion record.

    `destinatario` is the decrypted email (plaintext) — decryption happens in
    the service layer before constructing this schema.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    enviado_por: uuid.UUID
    materia_id: uuid.UUID
    destinatario: str          # decrypted email in responses
    asunto: str
    cuerpo: str
    estado: str                # EstadoComunicacion value
    lote_id: uuid.UUID
    enviado_at: datetime | None
    aprobado_at: datetime | None
    aprobado_por: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# Preview (RN-16 — render without persisting)
# ---------------------------------------------------------------------------

class DestinatarioPreview(_StrictBase):
    """A single recipient for preview rendering."""

    email: str
    variables: dict[str, str]


class PreviewRequest(_StrictBase):
    """Request body for POST /preview.

    materia_id is business data; identity comes from the JWT.
    """

    materia_id: uuid.UUID
    asunto: str
    cuerpo: str
    destinatarios: list[DestinatarioPreview]


class RenderResult(_StrictBase):
    """Rendered result for a single recipient in the preview."""

    email: str
    asunto_renderizado: str
    cuerpo_renderizado: str


class PreviewResponse(_StrictBase):
    """Response for POST /preview — list of per-recipient renders."""

    resultados: list[RenderResult]


# ---------------------------------------------------------------------------
# Encolar lote
# ---------------------------------------------------------------------------

class DestinatarioLote(_StrictBase):
    """A single recipient in a batch enqueue request."""

    email: str
    variables: dict[str, str]


class EncolarLoteRequest(_StrictBase):
    """Request body for POST / (encolar lote).

    Identity (enviado_por, tenant_id) comes EXCLUSIVELY from the JWT.
    """

    materia_id: uuid.UUID
    asunto: str
    cuerpo: str
    destinatarios: list[DestinatarioLote]


class EncolarLoteResponse(_StrictBase):
    """Response for POST / — summary of enqueued batch."""

    lote_id: uuid.UUID
    cantidad: int


# ---------------------------------------------------------------------------
# Aprobar
# ---------------------------------------------------------------------------

class AprobarLoteRequest(_StrictBase):
    """Approve all Pendiente messages in a lote."""

    lote_id: uuid.UUID


class AprobarItemRequest(_StrictBase):
    """Approve a single Comunicacion by its id."""

    comunicacion_id: uuid.UUID


# ---------------------------------------------------------------------------
# Cancelar
# ---------------------------------------------------------------------------

class CancelarLoteRequest(_StrictBase):
    """Cancel all Pendiente messages in a lote."""

    lote_id: uuid.UUID


class CancelarItemRequest(_StrictBase):
    """Cancel a single Comunicacion by its id."""

    comunicacion_id: uuid.UUID


# ---------------------------------------------------------------------------
# ColaQuery — query params for GET /
# ---------------------------------------------------------------------------

class ColaQuery(_StrictBase):
    """Optional filters for listing the communication queue."""

    lote_id: uuid.UUID | None = None
    estado: EstadoComunicacion | None = None

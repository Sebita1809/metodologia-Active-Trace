"""
app/schemas/mensaje.py — Pydantic v2 DTOs for the internal inbox API.

Security rules:
  - MensajeCreate does NOT include remitente_id (fixed from JWT).
  - RespuestaCreate does NOT include asunto (inherited from thread) or remitente_id.
  - All schemas use extra='forbid'.

Implemented: C-20 (perfil-y-mensajeria-interna)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class MensajeCreate(_Base):
    """Body for POST /api/inbox — send an initial message (new thread)."""
    destinatario_id: uuid.UUID
    asunto: str | None = Field(default=None, max_length=500)
    cuerpo: str = Field(min_length=1)


class RespuestaCreate(_Base):
    """Body for POST /api/inbox/{thread_id}/responder.

    asunto and remitente_id are intentionally absent: both are derived
    server-side (inherited from thread and JWT respectively).
    """
    cuerpo: str = Field(min_length=1)


class MensajeResponse(_Base):
    """Response DTO for a single message."""
    id: uuid.UUID
    thread_id: uuid.UUID
    remitente_id: uuid.UUID
    destinatario_id: uuid.UUID
    asunto: str | None
    cuerpo: str
    leido_at: datetime | None
    created_at: datetime


class ThreadResponse(_Base):
    """Response DTO for a full thread (list of messages)."""
    thread_id: uuid.UUID
    asunto: str | None
    mensajes: list[MensajeResponse]


class ThreadSummaryResponse(_Base):
    """Response DTO for a thread summary in the inbox listing."""
    thread_id: uuid.UUID
    asunto: str | None
    mensajes: list[MensajeResponse]

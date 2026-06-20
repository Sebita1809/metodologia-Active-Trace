"""
app/schemas/tareas.py — Pydantic v2 DTOs for the Tareas API (C-16).

All schemas use extra='forbid' to reject undeclared fields (hard constraint).

Key rules:
  - TareaCreate MUST NOT include asignado_por (set from JWT in service layer).
  - ComentarioTareaCreate MUST NOT include autor_id (set from JWT in service layer).
  - EstadoTarea imported from models (single source of truth).

Implemented: C-16 (tareas-internas)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.tarea import EstadoTarea


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# TareaCreate
# ---------------------------------------------------------------------------

class TareaCreate(_Base):
    """Body for POST /api/v1/tareas/ — create a new tarea.

    IMPORTANT: asignado_por is NOT in this schema.
    It is always derived from the JWT in the service layer.
    """

    asignado_a: uuid.UUID = Field(..., description="UUID of the user being assigned the task")
    descripcion: str = Field(..., min_length=1, description="Task description")
    materia_id: uuid.UUID | None = Field(
        default=None,
        description="Optional FK to materia (NULL for institutional-level tasks)",
    )
    contexto_id: uuid.UUID | None = Field(
        default=None,
        description="Optional opaque poly-ref UUID (no FK enforced)",
    )


# ---------------------------------------------------------------------------
# TareaDelegar
# ---------------------------------------------------------------------------

class TareaDelegar(_Base):
    """Body for PATCH /api/v1/tareas/{id}/delegar — delegate task to another user.

    Updates asignado_a; preserves asignado_por (original assigner).
    """

    nuevo_asignado_a: uuid.UUID = Field(
        ..., description="UUID of the new assignee"
    )


# ---------------------------------------------------------------------------
# TareaCambioEstado
# ---------------------------------------------------------------------------

class TareaCambioEstado(_Base):
    """Body for PATCH /api/v1/tareas/{id}/estado — change task state.

    Service layer validates the state machine transition.
    """

    nuevo_estado: EstadoTarea = Field(..., description="Target state for the task")


# ---------------------------------------------------------------------------
# TareaResponse
# ---------------------------------------------------------------------------

class TareaResponse(_Base):
    """Full tarea representation returned by all tarea endpoints."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID | None
    asignado_a: uuid.UUID
    asignado_por: uuid.UUID
    estado: str
    descripcion: str
    contexto_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


# ---------------------------------------------------------------------------
# TareaFiltros
# ---------------------------------------------------------------------------

class TareaFiltros(_Base):
    """Query parameters for GET /api/v1/tareas/ — list with optional filters."""

    estado: EstadoTarea | None = Field(default=None)
    asignado_a: uuid.UUID | None = Field(default=None)
    asignado_por: uuid.UUID | None = Field(default=None)
    materia_id: uuid.UUID | None = Field(default=None)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# ComentarioTareaCreate
# ---------------------------------------------------------------------------

class ComentarioTareaCreate(_Base):
    """Body for POST /api/v1/tareas/{id}/comentarios — add a comment.

    IMPORTANT: autor_id is NOT in this schema.
    It is always derived from the JWT in the service layer.
    """

    texto: str = Field(..., min_length=1, description="Comment text")


# ---------------------------------------------------------------------------
# ComentarioTareaResponse
# ---------------------------------------------------------------------------

class ComentarioTareaResponse(_Base):
    """Full comment representation returned by the comment endpoints."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    tarea_id: uuid.UUID
    autor_id: uuid.UUID
    texto: str
    creado_at: datetime
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

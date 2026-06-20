"""
app/schemas/auditoria.py — DTOs for C-19 panel de auditoría y métricas de uso.

All schemas use model_config = ConfigDict(extra='forbid') per project rules.

Implemented: C-19 (panel-auditoria-metricas)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# 2.1 — Acciones por día (serie temporal)
# ---------------------------------------------------------------------------

class AccionesPorDiaItem(BaseModel):
    """One day in the actions-per-day time series."""

    model_config = ConfigDict(extra="forbid")

    dia: datetime
    """Truncated to day (date_trunc('day', fecha_hora))."""

    total: int
    """Count of audit actions on this day."""


class AccionesPorDiaResponse(BaseModel):
    """Response wrapper for the acciones-por-dia panel endpoint."""

    model_config = ConfigDict(extra="forbid")

    items: list[AccionesPorDiaItem]


# ---------------------------------------------------------------------------
# 2.2 — Comunicaciones por docente (distribución por estado)
# ---------------------------------------------------------------------------

class ComunicacionesPorDocenteItem(BaseModel):
    """Communication status counts for one actor (docente).

    Counts are per-state as derived from COMUNICACION_* action codes.
    A state key is absent if count is zero.
    """

    model_config = ConfigDict(extra="forbid")

    actor_id: uuid.UUID
    pendiente: int = 0
    enviando: int = 0
    enviado: int = 0
    fallido: int = 0
    cancelado: int = 0


class ComunicacionesPorDocenteResponse(BaseModel):
    """Response wrapper for comunicaciones-por-docente panel endpoint."""

    model_config = ConfigDict(extra="forbid")

    items: list[ComunicacionesPorDocenteItem]


# ---------------------------------------------------------------------------
# 2.3 — Interacciones por docente × materia
# ---------------------------------------------------------------------------

class InteraccionesDocenteMateriaItem(BaseModel):
    """Interaction count for one actor × materia pair.

    materia_id is None when the audit record had no materia context (sin materia).
    """

    model_config = ConfigDict(extra="forbid")

    actor_id: uuid.UUID
    materia_id: uuid.UUID | None
    """None represents the 'sin materia' bucket."""

    total: int


class InteraccionesDocenteMateriaResponse(BaseModel):
    """Response wrapper for interacciones-docente-materia panel endpoint."""

    model_config = ConfigDict(extra="forbid")

    items: list[InteraccionesDocenteMateriaItem]


# ---------------------------------------------------------------------------
# 2.4 — Últimas acciones (reuses AuditLogResponse shape)
# ---------------------------------------------------------------------------

class AuditLogItemResponse(BaseModel):
    """Single audit log record as returned by panel and log endpoints.

    Aligns with the AuditLogResponse defined in the router (C-05) but lives
    in schemas/ so it can be imported by the service layer and new router.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    fecha_hora: datetime
    actor_id: uuid.UUID
    impersonado_id: uuid.UUID | None
    materia_id: uuid.UUID | None
    accion: str
    detalle: dict | None
    filas_afectadas: int
    ip: str | None
    user_agent: str | None


class UltimasAccionesResponse(BaseModel):
    """Response wrapper for últimas-acciones panel endpoint."""

    model_config = ConfigDict(extra="forbid")

    items: list[AuditLogItemResponse]


# ---------------------------------------------------------------------------
# 2.5 — Query/filtros del log completo
# ---------------------------------------------------------------------------

class LogFiltradoQuery(BaseModel):
    """Query parameters for the filtered audit log endpoint.

    All fields are optional — None means no constraint on that field.
    """

    model_config = ConfigDict(extra="forbid")

    desde: datetime | None = None
    """Filter records with fecha_hora >= desde."""

    hasta: datetime | None = None
    """Filter records with fecha_hora <= hasta."""

    materia_id: uuid.UUID | None = None
    """Filter by exact materia_id."""

    usuario_id: uuid.UUID | None = None
    """Filter by actor_id. In 'propio' scope, intersected with coordinator team."""

    accion: str | None = None
    """Filter by exact action code (e.g. COMUNICACION_ENVIAR)."""

    estado: str | None = None
    """Filter by communication state name (e.g. 'Fallido'). Maps to COMUNICACION_* codes."""

    limit: Annotated[int, Field(ge=1, le=1000)] = 100
    offset: Annotated[int, Field(ge=0)] = 0


class LogFiltradoResponse(BaseModel):
    """Response wrapper for filtered audit log endpoint."""

    model_config = ConfigDict(extra="forbid")

    items: list[AuditLogItemResponse]
    total_returned: int

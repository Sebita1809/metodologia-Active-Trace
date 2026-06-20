"""
api/v1/routers/auditoria.py — Audit log query endpoints.

Routes (C-05):
  GET /api/v1/auditoria/       — list audit records (paginated, legacy)

Routes (C-19 — panel and filtered log):
  GET /api/v1/auditoria/panel/acciones-por-dia        — daily action counts
  GET /api/v1/auditoria/panel/comunicaciones-por-docente — comm state per actor
  GET /api/v1/auditoria/panel/interacciones-docente-materia — interactions per actor×materia
  GET /api/v1/auditoria/panel/ultimas-acciones        — latest N actions
  GET /api/v1/auditoria/log                           — filtered paginated log

All endpoints require auditoria:ver.
Scope semantics:
  - alcance "propio"  → COORDINADOR: scoped to their team (resolved in Service)
  - alcance "global"  → ADMIN/FINANZAS: all records for the tenant

Identity and tenant always from the JWT session (current_user) — never from params.

Implemented: C-05 (audit-log)
Updated:     C-19 (panel-auditoria-metricas) — panel and filtered log endpoints
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.repositories.audit_log import AuditLogRepository
from app.schemas.auditoria import (
    AccionesPorDiaResponse,
    ComunicacionesPorDocenteResponse,
    InteraccionesDocenteMateriaResponse,
    LogFiltradoQuery,
    LogFiltradoResponse,
    UltimasAccionesResponse,
)
from app.services.auditoria_service import AuditoriaService

router = APIRouter(tags=["auditoria"])

# Both endpoints accept propio or global — the service enforces differences.
_require_auditoria = require_permission("auditoria:ver", scope="propio")


# ---------------------------------------------------------------------------
# Response schemas (C-05 legacy — kept for backwards compatibility)
# ---------------------------------------------------------------------------

class AuditLogResponse(BaseModel):
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


# ---------------------------------------------------------------------------
# C-05: Legacy list endpoint
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[AuditLogResponse])
async def listar_auditoria(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    perm: PermisoConcedido = Depends(_require_auditoria),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[AuditLogResponse]:
    """Return audit records for the current tenant.

    Scope-aware:
      - alcance "propio" → only records where actor_id == current user
      - alcance "global" → all records for the tenant
    """
    repo = AuditLogRepository(session=session, tenant_id=current_user.tenant_id)

    # Apply scope filter based on the granted permission (D-08)
    actor_filter: uuid.UUID | None = None
    if perm.alcance == "propio":
        actor_filter = current_user.user_id

    records = await repo.listar(actor_id=actor_filter, limit=limit, offset=offset)
    return [AuditLogResponse.model_validate(r) for r in records]


# ---------------------------------------------------------------------------
# C-19: Panel endpoints
# ---------------------------------------------------------------------------

@router.get("/panel/acciones-por-dia", response_model=AccionesPorDiaResponse)
async def panel_acciones_por_dia(
    desde: datetime = Query(..., description="Start of date range (inclusive)"),
    hasta: datetime = Query(..., description="End of date range (inclusive)"),
    perm: PermisoConcedido = Depends(_require_auditoria),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AccionesPorDiaResponse:
    """Daily action counts in a date range.

    Scope-aware: COORDINADOR (propio) sees only their team; ADMIN/FINANZAS (global)
    see the whole tenant.

    Identity and tenant always from JWT session.
    """
    service = AuditoriaService(session=session, tenant_id=current_user.tenant_id)
    return await service.panel_acciones_por_dia(
        desde=desde,
        hasta=hasta,
        alcance=perm.alcance,
        coordinador_id=current_user.user_id,
    )


@router.get(
    "/panel/comunicaciones-por-docente",
    response_model=ComunicacionesPorDocenteResponse,
)
async def panel_comunicaciones_por_docente(
    perm: PermisoConcedido = Depends(_require_auditoria),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ComunicacionesPorDocenteResponse:
    """Communication state distribution per actor (docente).

    Counts COMUNICACION_* actions grouped by actor and state.
    Scope-aware.
    """
    service = AuditoriaService(session=session, tenant_id=current_user.tenant_id)
    return await service.panel_comunicaciones_por_docente(
        alcance=perm.alcance,
        coordinador_id=current_user.user_id,
    )


@router.get(
    "/panel/interacciones-docente-materia",
    response_model=InteraccionesDocenteMateriaResponse,
)
async def panel_interacciones_docente_materia(
    perm: PermisoConcedido = Depends(_require_auditoria),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InteraccionesDocenteMateriaResponse:
    """Interaction counts per actor × materia.

    Rows with materia_id=None represent the 'sin materia' bucket.
    Scope-aware.
    """
    service = AuditoriaService(session=session, tenant_id=current_user.tenant_id)
    return await service.panel_interacciones_docente_materia(
        alcance=perm.alcance,
        coordinador_id=current_user.user_id,
    )


@router.get("/panel/ultimas-acciones", response_model=UltimasAccionesResponse)
async def panel_ultimas_acciones(
    limit: int = Query(default=200, ge=1, le=1000),
    perm: PermisoConcedido = Depends(_require_auditoria),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UltimasAccionesResponse:
    """Return the latest N audit records ordered by fecha_hora desc.

    Default limit is 200; maximum is 1000 (capped at repository level).
    Scope-aware.
    """
    service = AuditoriaService(session=session, tenant_id=current_user.tenant_id)
    return await service.panel_ultimas_acciones(
        limit=limit,
        alcance=perm.alcance,
        coordinador_id=current_user.user_id,
    )


# ---------------------------------------------------------------------------
# C-19: Filtered log endpoint
# ---------------------------------------------------------------------------

@router.get("/log", response_model=LogFiltradoResponse)
async def log_filtrado(
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
    materia_id: uuid.UUID | None = Query(default=None),
    usuario_id: uuid.UUID | None = Query(default=None),
    accion: str | None = Query(default=None),
    estado: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    perm: PermisoConcedido = Depends(_require_auditoria),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LogFiltradoResponse:
    """Filtered, paginated audit log.

    All filters are optional and combinable:
      - desde / hasta: date range on fecha_hora
      - materia_id: filter by materia
      - usuario_id: filter by actor (in 'propio' scope, intersected with team)
      - accion: exact action code
      - estado: communication state name (Pendiente/Enviando/Enviado/Fallido/Cancelado)
      - limit / offset: pagination

    Scope-aware: identity and tenant from JWT session only.
    """
    query = LogFiltradoQuery(
        desde=desde,
        hasta=hasta,
        materia_id=materia_id,
        usuario_id=usuario_id,
        accion=accion,
        estado=estado,
        limit=limit,
        offset=offset,
    )
    service = AuditoriaService(session=session, tenant_id=current_user.tenant_id)
    return await service.log_filtrado(
        query=query,
        alcance=perm.alcance,
        coordinador_id=current_user.user_id,
    )

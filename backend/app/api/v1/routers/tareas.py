"""
api/v1/routers/tareas.py — Internal task (tarea) endpoints (C-16).

Routes (all under /api/v1/tareas, all require tareas:gestionar):
  POST   /                      → crear_tarea (201)
  GET    /mias                   → mis_tareas (200)
  GET    /                      → listar_admin with filters + pagination (200)
  PATCH  /{id}/estado           → cambiar_estado (200)
  PATCH  /{id}/delegar          → delegar_tarea (200)
  POST   /{id}/comentarios      → agregar_comentario (201)
  GET    /{id}/comentarios      → listar_comentarios (200)

No business logic in this router — all delegated to TareaService.
Identity (tenant_id, user_id) ALWAYS from JWT via get_current_user.

Implemented: C-16 (tareas-internas)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.models.tarea import EstadoTarea
from app.schemas.tareas import (
    ComentarioTareaCreate,
    ComentarioTareaResponse,
    TareaCreate,
    TareaCambioEstado,
    TareaDelegar,
    TareaFiltros,
    TareaResponse,
)
from app.services.tarea_service import TareaService

router = APIRouter(tags=["tareas"])

_require_gestionar = require_permission("tareas:gestionar", scope="global")


def _get_tarea_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TareaService:
    """Build TareaService scoped to the authenticated user's tenant."""
    return TareaService(session=session, tenant_id=current_user.tenant_id)


# ---------------------------------------------------------------------------
# POST / — create tarea
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=TareaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_tarea(
    body: TareaCreate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: TareaService = Depends(_get_tarea_svc),
) -> TareaResponse:
    """Create a new internal task.

    Requires tareas:gestionar permission.
    asignado_por is always derived from the JWT — never from the request body.
    """
    return await svc.crear_tarea(body, current_user)


# ---------------------------------------------------------------------------
# GET /mias — my tasks
# ---------------------------------------------------------------------------

@router.get(
    "/mias",
    response_model=list[TareaResponse],
)
async def mis_tareas(
    _perm: PermisoConcedido = Depends(_require_gestionar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: TareaService = Depends(_get_tarea_svc),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[TareaResponse]:
    """Return tasks assigned to the authenticated user (F8.1).

    Requires tareas:gestionar permission.
    Filter: asignado_a = JWT user.
    """
    return await svc.mis_tareas(current_user, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# GET / — admin list with filters
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=list[TareaResponse],
)
async def listar_tareas_admin(
    _perm: PermisoConcedido = Depends(_require_gestionar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: TareaService = Depends(_get_tarea_svc),
    estado: EstadoTarea | None = Query(default=None),
    asignado_a: uuid.UUID | None = Query(default=None),
    asignado_por: uuid.UUID | None = Query(default=None),
    materia_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[TareaResponse]:
    """List all tenant tareas with optional filters and pagination (F8.3).

    Requires tareas:gestionar permission.
    COORDINADOR/ADMIN use this to see all tenant tasks.
    """
    filtros = TareaFiltros(
        estado=estado,
        asignado_a=asignado_a,
        asignado_por=asignado_por,
        materia_id=materia_id,
        limit=limit,
        offset=offset,
    )
    return await svc.listar_admin(filtros, current_user)


# ---------------------------------------------------------------------------
# PATCH /{id}/estado — change state
# ---------------------------------------------------------------------------

@router.patch(
    "/{tarea_id}/estado",
    response_model=TareaResponse,
)
async def cambiar_estado_tarea(
    tarea_id: uuid.UUID,
    body: TareaCambioEstado,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: TareaService = Depends(_get_tarea_svc),
) -> TareaResponse:
    """Change the state of a tarea, enforcing the state machine.

    Requires tareas:gestionar permission.
    Raises 409 if the transition is invalid.
    Raises 404 if the tarea does not exist in this tenant.
    """
    return await svc.cambiar_estado(tarea_id, body.nuevo_estado, current_user)


# ---------------------------------------------------------------------------
# PATCH /{id}/delegar — delegate
# ---------------------------------------------------------------------------

@router.patch(
    "/{tarea_id}/delegar",
    response_model=TareaResponse,
)
async def delegar_tarea(
    tarea_id: uuid.UUID,
    body: TareaDelegar,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: TareaService = Depends(_get_tarea_svc),
) -> TareaResponse:
    """Delegate a tarea to another user.

    Requires tareas:gestionar permission.
    asignado_por is preserved; only asignado_a changes.
    Raises 422 if nuevo_asignado_a is not in this tenant.
    """
    return await svc.delegar_tarea(tarea_id, body, current_user)


# ---------------------------------------------------------------------------
# POST /{id}/comentarios — add comment
# ---------------------------------------------------------------------------

@router.post(
    "/{tarea_id}/comentarios",
    response_model=ComentarioTareaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def agregar_comentario(
    tarea_id: uuid.UUID,
    body: ComentarioTareaCreate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: TareaService = Depends(_get_tarea_svc),
) -> ComentarioTareaResponse:
    """Add a comment to a tarea (F8.2).

    Requires tareas:gestionar permission.
    autor_id is always derived from the JWT — never from the request body.
    Raises 404 if the tarea does not exist in this tenant.
    """
    return await svc.agregar_comentario(tarea_id, body, current_user)


# ---------------------------------------------------------------------------
# GET /{id}/comentarios — list comment thread
# ---------------------------------------------------------------------------

@router.get(
    "/{tarea_id}/comentarios",
    response_model=list[ComentarioTareaResponse],
)
async def listar_comentarios(
    tarea_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: TareaService = Depends(_get_tarea_svc),
) -> list[ComentarioTareaResponse]:
    """Return the chronological comment thread for a tarea (F8.2).

    Requires tareas:gestionar permission.
    Ordered by creado_at ascending.
    Raises 404 if the tarea does not exist in this tenant.
    """
    return await svc.listar_comentarios(tarea_id, current_user)

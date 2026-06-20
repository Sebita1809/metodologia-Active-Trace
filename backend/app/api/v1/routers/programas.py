"""
api/v1/routers/programas.py — ProgramaMateria endpoints (C-17).

Routes (all under /api/v1/programas, all require estructura:gestionar):
  POST   /        → asociar_programa (create or replace) (201)
  GET    /        → listar programas with optional filters (200)
  GET    /combo   → obtener_por_combo via query params (200)

No business logic in this router — all delegated to ProgramaMateriaService.
Identity (tenant_id) ALWAYS from JWT via get_current_user.

Implemented: C-17 (programas-y-fechas-academicas)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.programas import ProgramaCreate, ProgramaFiltros, ProgramaResponse
from app.services.programa_materia_service import ProgramaMateriaService

router = APIRouter(tags=["programas"])

_require_gestionar = require_permission("estructura:gestionar", scope="global")


def _get_programa_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProgramaMateriaService:
    """Build ProgramaMateriaService scoped to the authenticated user's tenant."""
    return ProgramaMateriaService(session=session, tenant_id=current_user.tenant_id)


# ---------------------------------------------------------------------------
# POST / — create or replace programme
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=ProgramaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def asociar_programa(
    body: ProgramaCreate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: ProgramaMateriaService = Depends(_get_programa_svc),
) -> ProgramaResponse:
    """Create or replace the programme for a materia × carrera × cohorte combo.

    Requires estructura:gestionar permission.
    If a vivo programme already exists for the combo, it is soft-deleted
    and a new one is created (append-only audit trail).
    tenant_id is always derived from the JWT — never from the request body.
    """
    return await svc.asociar_programa(body)


# ---------------------------------------------------------------------------
# GET /combo — get programme by combo
# ---------------------------------------------------------------------------

@router.get(
    "/combo",
    response_model=ProgramaResponse,
)
async def obtener_programa_por_combo(
    materia_id: uuid.UUID = Query(...),
    carrera_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: ProgramaMateriaService = Depends(_get_programa_svc),
) -> ProgramaResponse:
    """Return the vivo programme for the given combo.

    Requires estructura:gestionar permission.
    Returns 404 if no vivo programme exists for the combo.
    """
    return await svc.obtener_por_combo(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
    )


# ---------------------------------------------------------------------------
# GET / — list programmes with optional filters
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=list[ProgramaResponse],
)
async def listar_programas(
    materia_id: uuid.UUID | None = Query(default=None),
    carrera_id: uuid.UUID | None = Query(default=None),
    cohorte_id: uuid.UUID | None = Query(default=None),
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: ProgramaMateriaService = Depends(_get_programa_svc),
) -> list[ProgramaResponse]:
    """List all vivo programmes for this tenant with optional filters.

    Requires estructura:gestionar permission.
    Filters: materia_id, carrera_id, cohorte_id (all optional).
    """
    filtros = ProgramaFiltros(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
    )
    return await svc.listar(filtros)

"""
api/v1/routers/equipos.py — Equipo management endpoints.

Routes (all under /api/equipos):
  GET  /mis-equipos                — authenticated user sees own assignments (no extra perm)
  GET  /usuarios/buscar            — user autocomplete (requires equipos:asignar)
  POST /asignaciones/masiva        — bulk assign (requires equipos:asignar), HTTP 201
  POST /asignaciones/clonar        — clone team (requires equipos:asignar), HTTP 201
  PATCH /asignaciones/vigencia     — bulk update dates (requires equipos:asignar), HTTP 200
  GET  /asignaciones/exportar      — CSV export (requires equipos:asignar), StreamingResponse

No business logic in this router — all delegated to EquipoService.

Implemented: C-08 (equipos-docentes)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.equipo import (
    AsignacionMasivaRequest,
    AsignacionMasivaResponse,
    ClonarEquipoRequest,
    ClonarEquipoResponse,
    MiEquipoItem,
    ModificarVigenciaRequest,
    ModificarVigenciaResponse,
    UsuarioBusquedaItem,
)
from app.services.equipo_service import EquipoService

router = APIRouter(tags=["equipos"])

_require_asignar = require_permission("equipos:asignar", scope="global")


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EquipoService:
    """Build EquipoService scoped to the authenticated user's tenant."""
    return EquipoService(session=session, tenant_id=current_user.tenant_id)


@router.get("/mis-equipos", response_model=list[MiEquipoItem])
async def get_mis_equipos(
    estado_vigencia: str | None = Query(default=None),
    materia_id: uuid.UUID | None = Query(default=None),
    rol: str | None = Query(default=None),
    carrera_id: uuid.UUID | None = Query(default=None),
    cohorte_id: uuid.UUID | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    svc: EquipoService = Depends(_get_svc),
) -> list[MiEquipoItem]:
    """Return assignments for the authenticated user.

    Identity comes from JWT — query params cannot override it.
    No extra permission required: every authenticated user can see their own teams.
    """
    return await svc.get_mis_equipos(
        current_user,
        estado_vigencia=estado_vigencia,
        materia_id=materia_id,
        rol=rol,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
    )


@router.get("/usuarios/buscar", response_model=list[UsuarioBusquedaItem])
async def buscar_usuarios(
    q: str = Query(...),
    _perm: PermisoConcedido = Depends(_require_asignar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: EquipoService = Depends(_get_svc),
) -> list[UsuarioBusquedaItem]:
    """Autocomplete users by nombre/apellidos.

    Returns only id, nombre, apellidos — no PII ciphertexts.
    Raises HTTP 422 if len(q) < 2.
    """
    return await svc.buscar_usuarios(current_user, q)


@router.post(
    "/asignaciones/masiva",
    response_model=AsignacionMasivaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def asignar_masiva(
    body: AsignacionMasivaRequest,
    _perm: PermisoConcedido = Depends(_require_asignar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: EquipoService = Depends(_get_svc),
) -> AsignacionMasivaResponse:
    """Bulk-assign a role to multiple users in one transaction."""
    return await svc.asignar_masiva(current_user, body)


@router.post(
    "/asignaciones/clonar",
    response_model=ClonarEquipoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def clonar_equipo(
    body: ClonarEquipoRequest,
    _perm: PermisoConcedido = Depends(_require_asignar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: EquipoService = Depends(_get_svc),
) -> ClonarEquipoResponse:
    """Clone vigent assignments from origin context to destination context."""
    return await svc.clonar_equipo(current_user, body)


@router.patch(
    "/asignaciones/vigencia",
    response_model=ModificarVigenciaResponse,
    status_code=status.HTTP_200_OK,
)
async def modificar_vigencia(
    body: ModificarVigenciaRequest,
    _perm: PermisoConcedido = Depends(_require_asignar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: EquipoService = Depends(_get_svc),
) -> ModificarVigenciaResponse:
    """Bulk-update desde/hasta for all matching assignments."""
    return await svc.modificar_vigencia(current_user, body)


@router.get("/asignaciones/exportar")
async def exportar_equipo(
    materia_id: uuid.UUID | None = Query(default=None),
    carrera_id: uuid.UUID | None = Query(default=None),
    cohorte_id: uuid.UUID | None = Query(default=None),
    _perm: PermisoConcedido = Depends(_require_asignar),
    current_user: CurrentUser = Depends(get_current_user),
    svc: EquipoService = Depends(_get_svc),
) -> StreamingResponse:
    """Stream CSV export of assignments.

    Returns StreamingResponse with Content-Type text/csv.
    """
    generator = await svc.exportar_equipo(
        current_user,
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
    )
    return StreamingResponse(
        generator,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=equipos.csv"},
    )

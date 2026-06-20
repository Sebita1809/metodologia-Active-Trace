"""
api/v1/routers/fechas_academicas.py — FechaAcademica endpoints (C-17).

Routes (all under /api/v1/fechas-academicas, all require estructura:gestionar):
  POST   /                → crear_fecha (201)
  GET    /                → listar por materia × cohorte (200)
  PATCH  /{id}            → actualizar fecha, titulo, periodo (200)
  DELETE /{id}            → soft-delete (204)
  GET    /fragmento-lms   → generate LMS fragment (200)

No business logic in this router — all delegated to FechaAcademicaService.
Identity (tenant_id) ALWAYS from JWT via get_current_user.

IMPORTANT: /fragmento-lms MUST be registered before /{id} to avoid
FastAPI routing ambiguity (literal path takes precedence over parameter).

Implemented: C-17 (programas-y-fechas-academicas)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.fechas_academicas import (
    FechaAcademicaCreate,
    FechaAcademicaResponse,
    FechaAcademicaUpdate,
    FragmentoLmsResponse,
)
from app.services.fecha_academica_service import FechaAcademicaService

router = APIRouter(tags=["fechas-academicas"])

_require_gestionar = require_permission("estructura:gestionar", scope="global")


def _get_fecha_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FechaAcademicaService:
    """Build FechaAcademicaService scoped to the authenticated user's tenant."""
    return FechaAcademicaService(session=session, tenant_id=current_user.tenant_id)


# ---------------------------------------------------------------------------
# POST / — create fecha
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=FechaAcademicaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_fecha(
    body: FechaAcademicaCreate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: FechaAcademicaService = Depends(_get_fecha_svc),
) -> FechaAcademicaResponse:
    """Create a new academic date.

    Requires estructura:gestionar permission.
    tenant_id is always derived from the JWT — never from the request body.
    Raises 409 if the combo (materia_id, cohorte_id, tipo, numero) already exists.
    """
    return await svc.crear_fecha(body)


# ---------------------------------------------------------------------------
# GET /fragmento-lms — generate LMS fragment (before /{id} to avoid ambiguity)
# ---------------------------------------------------------------------------

@router.get(
    "/fragmento-lms",
    response_model=FragmentoLmsResponse,
)
async def generar_fragmento_lms(
    materia_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: FechaAcademicaService = Depends(_get_fecha_svc),
) -> FragmentoLmsResponse:
    """Generate an HTML fragment listing academic dates for the LMS.

    Requires estructura:gestionar permission.
    Returns a formatted HTML string — no call to any external LMS API is made.
    If no dates exist for the combo, returns an empty contenido string (not an error).
    """
    return await svc.generar_fragmento_lms(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
    )


# ---------------------------------------------------------------------------
# GET / — list by materia × cohorte
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=list[FechaAcademicaResponse],
)
async def listar_fechas(
    materia_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: FechaAcademicaService = Depends(_get_fecha_svc),
) -> list[FechaAcademicaResponse]:
    """List all vivo academic dates for a materia × cohorte, ordered by fecha asc.

    Requires estructura:gestionar permission.
    Returns an empty list if no dates exist for the combo.
    """
    return await svc.listar_por_materia_cohorte(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
    )


# ---------------------------------------------------------------------------
# PATCH /{id} — partial update
# ---------------------------------------------------------------------------

@router.patch(
    "/{fecha_id}",
    response_model=FechaAcademicaResponse,
)
async def actualizar_fecha(
    fecha_id: uuid.UUID,
    body: FechaAcademicaUpdate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: FechaAcademicaService = Depends(_get_fecha_svc),
) -> FechaAcademicaResponse:
    """Update fecha, titulo and/or periodo of an academic date.

    Requires estructura:gestionar permission.
    Only provided (non-null) fields are updated.
    Raises 404 if not found in this tenant.
    """
    return await svc.actualizar_fecha(fecha_id, body)


# ---------------------------------------------------------------------------
# DELETE /{id} — soft-delete
# ---------------------------------------------------------------------------

@router.delete(
    "/{fecha_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar_fecha(
    fecha_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: FechaAcademicaService = Depends(_get_fecha_svc),
) -> None:
    """Soft-delete an academic date (never hard delete).

    Requires estructura:gestionar permission.
    Raises 404 if not found in this tenant.
    """
    await svc.eliminar_fecha(fecha_id)

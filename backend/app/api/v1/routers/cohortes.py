"""
api/v1/routers/cohortes.py — Cohorte catalog administration endpoints.

Routes (all under /api/admin/cohortes):
  POST   /       — create cohorte (requires estructura:gestionar)
  GET    /       — list cohortes (open; optional ?carrera_id= filter)
  GET    /{id}   — get cohorte (open within tenant)
  PATCH  /{id}   — update cohorte (requires estructura:gestionar)
  DELETE /{id}   — soft-delete cohorte (requires estructura:gestionar), returns 204

No business logic in this router — all delegated to CohorteService.

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.cohorte import CohorteCreate, CohorteResponse, CohorteUpdate
from app.services.cohorte_service import CohorteService

router = APIRouter(tags=["estructura"])

_require_gestionar = require_permission("estructura:gestionar", scope="global")


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CohorteService:
    """Build CohorteService scoped to the authenticated user's tenant."""
    return CohorteService(session=session, tenant_id=current_user.tenant_id)


@router.post("/", response_model=CohorteResponse, status_code=status.HTTP_201_CREATED)
async def create_cohorte(
    body: CohorteCreate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: CohorteService = Depends(_get_svc),
) -> CohorteResponse:
    try:
        cohorte = await svc.create(
            carrera_id=body.carrera_id,
            nombre=body.nombre,
            anio=body.anio,
            vig_desde=body.vig_desde,
            vig_hasta=body.vig_hasta,
            estado=body.estado,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return CohorteResponse.model_validate(cohorte)


@router.get("/", response_model=list[CohorteResponse])
async def list_cohortes(
    carrera_id: uuid.UUID | None = Query(default=None),
    svc: CohorteService = Depends(_get_svc),
) -> list[CohorteResponse]:
    cohortes = await svc.list(carrera_id=carrera_id)
    return [CohorteResponse.model_validate(c) for c in cohortes]


@router.get("/{cohorte_id}", response_model=CohorteResponse)
async def get_cohorte(
    cohorte_id: uuid.UUID,
    svc: CohorteService = Depends(_get_svc),
) -> CohorteResponse:
    cohorte = await svc.get(cohorte_id)
    if cohorte is None:
        raise HTTPException(status_code=404, detail="Cohorte not found")
    return CohorteResponse.model_validate(cohorte)


@router.patch("/{cohorte_id}", response_model=CohorteResponse)
async def update_cohorte(
    cohorte_id: uuid.UUID,
    body: CohorteUpdate,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: CohorteService = Depends(_get_svc),
) -> CohorteResponse:
    try:
        cohorte = await svc.update(
            cohorte_id,
            nombre=body.nombre,
            anio=body.anio,
            vig_desde=body.vig_desde,
            vig_hasta=body.vig_hasta,
            estado=body.estado,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if cohorte is None:
        raise HTTPException(status_code=404, detail="Cohorte not found")
    return CohorteResponse.model_validate(cohorte)


@router.delete("/{cohorte_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_cohorte(
    cohorte_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc: CohorteService = Depends(_get_svc),
) -> None:
    deleted = await svc.delete(cohorte_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Cohorte not found")

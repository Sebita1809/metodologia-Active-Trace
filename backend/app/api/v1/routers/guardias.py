"""
api/v1/routers/guardias.py — Guardias endpoints (C-13).

Routes:
  POST  /api/v1/guardias — register a Guardia (TUTOR); require encuentros:gestionar
  GET   /api/v1/guardias — list/export (COORDINADOR/ADMIN); require encuentros:gestionar global

Rules enforced:
  - Identity and tenant ALWAYS from JWT (get_current_user) — never from body/params.
  - No business logic in this router — all delegated to GuardiaService.
  - Fail-closed: missing permission → HTTP 403.
  - ValueError / DomainError from service → HTTP 422.

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import PermisoConcedido, get_current_user, get_db, require_permission
from app.models.guardia import EstadoGuardia
from app.schemas.guardia import GuardiaRead, GuardiaRequest

router = APIRouter(tags=["guardias"])

_require_gestionar = require_permission("encuentros:gestionar")
_require_gestionar_global = require_permission("encuentros:gestionar", "global")


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Build GuardiaService scoped to the authenticated user's tenant."""
    from app.services.guardia_service import GuardiaService  # noqa: PLC0415
    return GuardiaService(session=session, tenant_id=current_user.tenant_id)


# ---------------------------------------------------------------------------
# Task 9.5 — POST /guardias
# ---------------------------------------------------------------------------

@router.post(
    "/guardias",
    response_model=GuardiaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar guardia (TUTOR)",
)
async def registrar_guardia(
    body: GuardiaRequest,
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc=Depends(_get_svc),
) -> GuardiaRead:
    """Register a Guardia for a TUTOR's asignacion.

    creada_at is set server-side — not from the request body.
    Identity and tenant come exclusively from the JWT.
    """
    try:
        guardia = await svc.registrar(
            asignacion_id=body.asignacion_id,
            materia_id=body.materia_id,
            carrera_id=body.carrera_id,
            cohorte_id=body.cohorte_id,
            dia=body.dia,
            horario=body.horario,
            estado=body.estado or EstadoGuardia.Pendiente,
            comentarios=body.comentarios,
        )
        return GuardiaRead.model_validate(guardia, from_attributes=True)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


# ---------------------------------------------------------------------------
# Task 9.5 — GET /guardias
# ---------------------------------------------------------------------------

@router.get(
    "/guardias",
    response_model=list[GuardiaRead],
    summary="Listar guardias del tenant (COORDINADOR/ADMIN)",
)
async def listar_guardias(
    asignacion_id: uuid.UUID | None = Query(
        default=None,
        description="Filter by asignacion_id",
    ),
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_gestionar_global),
    svc=Depends(_get_svc),
) -> list[GuardiaRead]:
    """List active guardias for this tenant (COORDINADOR/ADMIN only).

    TUTOR gets 403 (global scope required — fail-closed).
    Identity and tenant come exclusively from the JWT.
    """
    guardias = await svc.listar(asignacion_id=asignacion_id)
    return [GuardiaRead.model_validate(g, from_attributes=True) for g in guardias]

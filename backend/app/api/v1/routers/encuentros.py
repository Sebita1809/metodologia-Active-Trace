"""
api/v1/routers/encuentros.py — Encuentros endpoints (C-13).

Routes:
  POST   /api/v1/slots                — create recurring slot (RN-13.1)
  POST   /api/v1/encuentros           — create unique encuentro (RN-13.2)
  PATCH  /api/v1/encuentros/{id}      — edit instancia (RN-14)
  GET    /api/v1/encuentros/html      — ?materia_id=X HTML fragment
  GET    /api/v1/admin/encuentros     — admin transversal view

Rules enforced:
  - Identity and tenant ALWAYS from JWT (get_current_user) — never from body/params.
  - No business logic in this router — all delegated to EncuentroService.
  - Fail-closed: missing permission → HTTP 403.
  - ValueError / DomainError from service → HTTP 422.
  - require_permission("encuentros:gestionar") on every endpoint.

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import PermisoConcedido, get_current_user, get_db, require_permission
from app.schemas.encuentro import (
    EditarInstanciaRequest,
    EncuentroUnicoRequest,
    InstanciaEncuentroRead,
    SlotCreadoResponse,
    SlotEncuentroRead,
    SlotRecurrenteRequest,
)

router = APIRouter(tags=["encuentros"])

_require_gestionar = require_permission("encuentros:gestionar")


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Build EncuentroService scoped to the authenticated user's tenant."""
    from app.services.encuentro_service import EncuentroService  # noqa: PLC0415
    return EncuentroService(session=session, tenant_id=current_user.tenant_id)


# ---------------------------------------------------------------------------
# Task 9.1 — POST /slots (RN-13.1)
# ---------------------------------------------------------------------------

@router.post(
    "/slots",
    response_model=SlotCreadoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear slot recurrente de encuentros (RN-13.1)",
)
async def crear_slot(
    body: SlotRecurrenteRequest,
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc=Depends(_get_svc),
) -> SlotCreadoResponse:
    """Create a recurring slot and generate N InstanciaEncuentro rows.

    Identity and tenant come exclusively from the JWT.
    Raises 422 on RN-13 violations (both or neither mode set, cant_semanas out of range).
    """
    try:
        slot, instancias = await svc.crear_slot_recurrente(
            asignacion_id=body.asignacion_id,
            materia_id=body.materia_id,
            titulo=body.titulo,
            dia_semana=body.dia_semana,
            fecha_inicio=body.fecha_inicio,
            cant_semanas=body.cant_semanas,
            hora=body.hora,
            meet_url=body.meet_url,
            vig_desde=body.vig_desde,
            vig_hasta=body.vig_hasta,
            current_user_id=current_user.user_id,
            current_user_roles=current_user.roles,
        )
        return SlotCreadoResponse(
            slot=SlotEncuentroRead.model_validate(slot, from_attributes=True),
            instancias=[
                InstanciaEncuentroRead.model_validate(i, from_attributes=True)
                for i in instancias
            ],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


# ---------------------------------------------------------------------------
# Task 9.2 — POST /encuentros (RN-13.2)
# ---------------------------------------------------------------------------

@router.post(
    "/encuentros",
    response_model=InstanciaEncuentroRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear encuentro único (RN-13.2)",
)
async def crear_encuentro_unico(
    body: EncuentroUnicoRequest,
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc=Depends(_get_svc),
) -> InstanciaEncuentroRead:
    """Create a single InstanciaEncuentro with slot_id=NULL.

    Identity and tenant come exclusively from the JWT.
    """
    try:
        instancia = await svc.crear_encuentro_unico(
            materia_id=body.materia_id,
            titulo=body.titulo,
            fecha_unica=body.fecha_unica,
            hora=body.hora,
            meet_url=body.meet_url,
            current_user_id=current_user.user_id,
            current_user_roles=current_user.roles,
        )
        return InstanciaEncuentroRead.model_validate(instancia, from_attributes=True)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


# ---------------------------------------------------------------------------
# Task 9.2 — PATCH /encuentros/{id} (RN-14)
# ---------------------------------------------------------------------------

@router.patch(
    "/encuentros/{instancia_id}",
    response_model=InstanciaEncuentroRead,
    summary="Editar instancia de encuentro (RN-14 — no afecta slot ni otras instancias)",
)
async def editar_instancia(
    instancia_id: uuid.UUID,
    body: EditarInstanciaRequest,
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc=Depends(_get_svc),
) -> InstanciaEncuentroRead:
    """Edit a single InstanciaEncuentro (estado, meet_url, video_url, comentario).

    The slot and sibling instancias are NEVER touched (RN-14).
    Identity and tenant come exclusively from the JWT.
    """
    try:
        instancia = await svc.editar_instancia(
            instancia_id,
            estado=body.estado,
            meet_url=body.meet_url,
            video_url=body.video_url,
            comentario=body.comentario,
        )
        return InstanciaEncuentroRead.model_validate(instancia, from_attributes=True)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


# ---------------------------------------------------------------------------
# Task 9.3 — GET /encuentros/html
# ---------------------------------------------------------------------------

@router.get(
    "/encuentros/html",
    response_class=HTMLResponse,
    summary="Fragmento HTML del calendario de encuentros para el aula virtual",
)
async def html_encuentros(
    materia_id: uuid.UUID = Query(..., description="UUID de la materia"),
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_gestionar),
    svc=Depends(_get_svc),
) -> str:
    """Return an HTML fragment with the meeting calendar for a materia.

    Identity and tenant come exclusively from the JWT.
    """
    html = await svc.generar_html_asignacion(materia_id)
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# Task 9.4 — GET /admin/encuentros (transversal within tenant)
# ---------------------------------------------------------------------------

@router.get(
    "/admin/encuentros",
    response_model=list[InstanciaEncuentroRead],
    summary="Listar todas las instancias de encuentro del tenant (COORDINADOR/ADMIN)",
)
async def admin_listar_encuentros(
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(require_permission("encuentros:gestionar", "global")),
    svc=Depends(_get_svc),
) -> list[InstanciaEncuentroRead]:
    """Return all active instancias for this tenant.

    Only COORDINADOR/ADMIN (global scope) can access this endpoint.
    PROFESOR gets 403 (fail-closed).
    Identity and tenant come exclusively from the JWT.
    """
    instancias = await svc.listar_admin_encuentros()
    return [
        InstanciaEncuentroRead.model_validate(i, from_attributes=True)
        for i in instancias
    ]

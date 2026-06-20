"""
api/v1/routers/padron.py — Padron (versioned student roster) endpoints.

Routes (all under /api/padron):
  POST   /preview       — parse file, return preview (no DB write) [padron:cargar]
  POST   /confirmar     — create active version from file (201) [padron:cargar]
  POST   /sync-moodle   — sync from Moodle WS on-demand [padron:cargar]; 502 on failure
  GET    /              — get active padrón for (materia, cohorte) [padron:ver]
  GET    /versiones     — get version history [padron:ver]
  DELETE /              — vaciar scope (soft-delete) [padron:vaciar]

Rules enforced:
  - Identity and tenant ALWAYS from JWT (get_current_user) — never from body/params.
  - materia_id / cohorte_id are business data, not identity.
  - MoodleIntegrationError → HTTP 502.
  - No business logic in this router — all delegated to PadronService.

Implemented: C-09 (padron-ingesta-moodle)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.integrations.moodle_ws import MoodleIntegrationError, MoodleWSClient
from app.schemas.padron import (
    ConfirmarPadronResponse,
    PadronPreviewResponse,
    SyncMoodleRequest,
    VaciarPadronRequest,
    VersionPadronResponse,
    EntradaPadronResponse,
)
from app.services.padron_service import PadronService

router = APIRouter(tags=["padron"])

_require_cargar = require_permission("padron:cargar", scope="propio")
_require_ver = require_permission("padron:ver", scope="propio")
_require_vaciar = require_permission("padron:vaciar", scope="propio")


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PadronService:
    """Build PadronService scoped to the authenticated user's tenant."""
    from app.core.config import get_settings  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.services.audit_service import AuditService  # noqa: PLC0415

    settings = get_settings()
    crypto = CryptoService(settings.encryption_key)
    audit_svc = AuditService(session=session, tenant_id=current_user.tenant_id)

    return PadronService(
        session=session,
        tenant_id=current_user.tenant_id,
        crypto=crypto,
        audit_svc=audit_svc,
    )


# ---------------------------------------------------------------------------
# POST /padron/preview
# ---------------------------------------------------------------------------

@router.post(
    "/preview",
    response_model=PadronPreviewResponse,
    summary="Previsualizar padrón desde archivo (sin persistir)",
)
async def preview_padron(
    request: Request,
    file: UploadFile = File(...),
    _perm: PermisoConcedido = Depends(_require_cargar),
    svc: PadronService = Depends(_get_svc),
) -> PadronPreviewResponse:
    """Parse the uploaded file and return a preview. Nothing is persisted."""
    file_data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    return await svc.preview(file_data=file_data, content_type=content_type)


# ---------------------------------------------------------------------------
# POST /padron/confirmar
# ---------------------------------------------------------------------------

@router.post(
    "/confirmar",
    response_model=ConfirmarPadronResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirmar carga de padrón desde archivo",
)
async def confirmar_padron(
    request: Request,
    file: UploadFile = File(...),
    materia_id: uuid.UUID = Form(...),
    cohorte_id: uuid.UUID = Form(...),
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_cargar),
    svc: PadronService = Depends(_get_svc),
) -> ConfirmarPadronResponse:
    """Parse file and create a new active padrón version for (materia, cohorte).

    If a previous active version exists, it is deactivated (not deleted).
    Identity and tenant come exclusively from the JWT.
    """
    file_data = await file.read()
    content_type = file.content_type or "application/octet-stream"

    try:
        return await svc.confirmar(
            current_user=current_user,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            file_data=file_data,
            content_type=content_type,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /padron/sync-moodle
# ---------------------------------------------------------------------------

@router.post(
    "/sync-moodle",
    response_model=ConfirmarPadronResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sincronizar padrón desde Moodle Web Services",
)
async def sync_moodle(
    request: Request,
    body: SyncMoodleRequest,
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_cargar),
    svc: PadronService = Depends(_get_svc),
) -> ConfirmarPadronResponse:
    """Fetch padrón from Moodle LMS and create a new active version.

    Returns HTTP 502 if the Moodle WS is unreachable or returns an error
    after all retries are exhausted.
    """
    from app.core.config import get_settings  # noqa: PLC0415

    settings = get_settings()

    moodle_client = MoodleWSClient(
        base_url=settings.moodle_base_url,
        token=settings.moodle_token,
    )

    try:
        return await svc.sync_moodle(
            current_user=current_user,
            materia_id=body.materia_id,
            cohorte_id=body.cohorte_id,
            moodle_client=moodle_client,
            curso_ref=body.curso_ref,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except MoodleIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Moodle WS no disponible: {exc}",
        )


# ---------------------------------------------------------------------------
# GET /padron
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=list[EntradaPadronResponse],
    summary="Ver padrón activo de (materia, cohorte)",
)
async def ver_padron_activo(
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_ver),
    svc: PadronService = Depends(_get_svc),
) -> list[EntradaPadronResponse]:
    """Return all entries of the currently active padrón version.

    Returns an empty list if no active version exists for (materia, cohorte).
    """
    return await svc.ver_padron_activo(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
    )


# ---------------------------------------------------------------------------
# GET /padron/versiones
# ---------------------------------------------------------------------------

@router.get(
    "/versiones",
    response_model=list[VersionPadronResponse],
    summary="Historial de versiones del padrón para (materia, cohorte)",
)
async def list_versiones(
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_ver),
    svc: PadronService = Depends(_get_svc),
) -> list[VersionPadronResponse]:
    """Return the version history for (materia, cohorte), newest first."""
    return await svc.list_versiones(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
    )


# ---------------------------------------------------------------------------
# DELETE /padron
# ---------------------------------------------------------------------------

@router.delete(
    "/",
    summary="Vaciar padrón (soft-delete scope)",
    status_code=status.HTTP_200_OK,
)
async def vaciar_padron(
    body: VaciarPadronRequest,
    _perm: PermisoConcedido = Depends(_require_vaciar),
    svc: PadronService = Depends(_get_svc),
) -> dict:
    """Soft-delete all padrón versions and entries for (materia, cohorte).

    This is a scope-isolated operation: only the specified (materia, cohorte)
    is affected. Other combinations are never touched.
    """
    eliminadas = await svc.vaciar(
        materia_id=body.materia_id,
        cohorte_id=body.cohorte_id,
    )
    return {"entradas_eliminadas": eliminadas}

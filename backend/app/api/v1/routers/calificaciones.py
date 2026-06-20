"""
api/v1/routers/calificaciones.py — Calificaciones endpoints.

Routes (all under /api/calificaciones):
  POST   /preview              — parse LMS file, return activities (no DB) [calificaciones:importar]
  POST   /import               — confirm import + persist grades [calificaciones:importar]
  POST   /finalizacion-preview — preview textual items from finalization report [calificaciones:importar]
  GET    /                     — list calificaciones for an asignacion [calificaciones:ver]
  PUT    /umbral               — upsert approval threshold [calificaciones:configurar]
  GET    /umbral               — get approval threshold [calificaciones:ver]

Rules enforced:
  - Identity and tenant ALWAYS from JWT (get_current_user) — never from body/params.
  - asignacion_id is business data, not identity.
  - ValueError → HTTP 422.
  - No business logic in this router — all delegated to CalificacionService / UmbralMateriaService.

Implemented: C-10 (calificaciones-y-umbral)
"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.calificacion import (
    CalificacionRead,
    FinalizacionPreviewResponse,
    ImportConfirmRequest,
    ImportPreviewResponse,
)
from app.schemas.umbral_materia import UmbralMateriaRead, UmbralMateriaUpsert
from app.services.calificacion_service import CalificacionService
from app.services.umbral_materia_service import UmbralMateriaService

router = APIRouter(tags=["calificaciones"])

_require_importar = require_permission("calificaciones:importar", scope="propio")
_require_ver = require_permission("calificaciones:ver", scope="propio")
_require_configurar = require_permission("calificaciones:configurar", scope="propio")


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CalificacionService:
    """Build CalificacionService scoped to the authenticated user's tenant."""
    from app.core.config import get_settings  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.services.audit_service import AuditService  # noqa: PLC0415

    settings = get_settings()
    crypto = CryptoService(settings.encryption_key)
    audit_svc = AuditService(session=session, tenant_id=current_user.tenant_id)

    return CalificacionService(
        session=session,
        tenant_id=current_user.tenant_id,
        crypto=crypto,
        audit_svc=audit_svc,
    )


def _get_umbral_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UmbralMateriaService:
    """Build UmbralMateriaService scoped to the authenticated user's tenant."""
    return UmbralMateriaService(
        session=session,
        tenant_id=current_user.tenant_id,
    )


# ---------------------------------------------------------------------------
# POST /calificaciones/preview
# ---------------------------------------------------------------------------

@router.post(
    "/preview",
    response_model=ImportPreviewResponse,
    summary="Previsualizar actividades del archivo LMS (sin persistir)",
)
async def preview_import(
    file: UploadFile = File(...),
    asignacion_id: uuid.UUID = Form(...),
    _perm: PermisoConcedido = Depends(_require_importar),
    svc: CalificacionService = Depends(_get_svc),
) -> ImportPreviewResponse:
    """Parse the uploaded LMS grades file and return detected activities.

    Nothing is persisted. asignacion_id is for context only.
    """
    file_bytes = await file.read()
    filename = file.filename or "upload.xlsx"

    try:
        return await svc.preview_import(file_bytes, filename, asignacion_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /calificaciones/import
# ---------------------------------------------------------------------------

@router.post(
    "/import",
    response_model=list[CalificacionRead],
    status_code=status.HTTP_201_CREATED,
    summary="Confirmar importación de calificaciones desde archivo LMS",
)
async def confirm_import(
    file: UploadFile = File(...),
    request_json: str = Form(..., alias="request"),
    current_user: CurrentUser = Depends(get_current_user),
    _perm: PermisoConcedido = Depends(_require_importar),
    svc: CalificacionService = Depends(_get_svc),
) -> list[CalificacionRead]:
    """Parse LMS file, filter selected activities, persist grades.

    The request body must be sent as a JSON-encoded form field named 'request'.
    Identity and tenant come exclusively from the JWT.
    """
    file_bytes = await file.read()
    filename = file.filename or "upload.xlsx"

    try:
        request_data = json.loads(request_json)
        request = ImportConfirmRequest.model_validate(request_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Request JSON inválido: {exc}",
        )

    try:
        return await svc.confirm_import(file_bytes, filename, request, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /calificaciones/finalizacion-preview
# ---------------------------------------------------------------------------

@router.post(
    "/finalizacion-preview",
    response_model=FinalizacionPreviewResponse,
    summary="Previsualizar items textuales pendientes desde reporte de finalización LMS",
)
async def finalizacion_preview(
    file: UploadFile = File(...),
    asignacion_id: uuid.UUID = Form(...),
    _perm: PermisoConcedido = Depends(_require_importar),
    svc: CalificacionService = Depends(_get_svc),
) -> FinalizacionPreviewResponse:
    """Parse LMS finalization report and return textual activities not yet graded.

    Only textual activities are returned (RN-08).
    """
    file_bytes = await file.read()
    filename = file.filename or "upload.xlsx"

    try:
        return await svc.finalizacion_preview(file_bytes, filename, asignacion_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /calificaciones
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=list[CalificacionRead],
    summary="Listar calificaciones de una asignación",
)
async def list_calificaciones(
    asignacion_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_ver),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CalificacionRead]:
    """Return all calificaciones for the given asignacion_id.

    Resolves entrada_padron_ids via the active padrón version for the asignacion.
    """
    from app.core.config import get_settings  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.services.audit_service import AuditService  # noqa: PLC0415

    settings = get_settings()
    crypto = CryptoService(settings.encryption_key)
    audit_svc = AuditService(session=session, tenant_id=current_user.tenant_id)
    svc = CalificacionService(
        session=session,
        tenant_id=current_user.tenant_id,
        crypto=crypto,
        audit_svc=audit_svc,
    )

    from app.repositories.asignacion_repository import AsignacionRepository  # noqa: PLC0415
    from app.repositories.calificacion_repository import CalificacionRepository  # noqa: PLC0415
    from app.repositories.entrada_padron_repository import EntradaPadronRepository  # noqa: PLC0415
    from app.repositories.version_padron_repository import VersionPadronRepository  # noqa: PLC0415

    asignacion_repo = AsignacionRepository(session=session, tenant_id=current_user.tenant_id)
    asignacion = await asignacion_repo.get(asignacion_id)
    if asignacion is None or asignacion.materia_id is None or asignacion.cohorte_id is None:
        return []

    version_repo = VersionPadronRepository(session=session, tenant_id=current_user.tenant_id)
    version = await version_repo.get_activa(asignacion.materia_id, asignacion.cohorte_id)
    if version is None:
        return []

    entrada_repo = EntradaPadronRepository(session=session, tenant_id=current_user.tenant_id)
    entradas = await entrada_repo.list_by_version(version.id)
    entrada_ids = [e.id for e in entradas]

    cal_repo = CalificacionRepository(session=session, tenant_id=current_user.tenant_id)
    cals = await cal_repo.list_by_entradas(entrada_ids)
    return [CalificacionRead.model_validate(c) for c in cals]


# ---------------------------------------------------------------------------
# PUT /calificaciones/umbral
# ---------------------------------------------------------------------------

@router.put(
    "/umbral",
    response_model=UmbralMateriaRead,
    summary="Configurar umbral de aprobación para una asignación",
)
async def upsert_umbral(
    body: UmbralMateriaUpsert,
    asignacion_id: uuid.UUID,
    materia_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_configurar),
    svc: UmbralMateriaService = Depends(_get_umbral_svc),
) -> UmbralMateriaRead:
    """Create or update the approval threshold for the given asignacion.

    asignacion_id and materia_id are business data.
    Identity and tenant come exclusively from the JWT.
    """
    try:
        return await svc.upsert(
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=body.umbral_pct,
            valores_aprobatorios=body.valores_aprobatorios,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /calificaciones/umbral
# ---------------------------------------------------------------------------

@router.get(
    "/umbral",
    response_model=UmbralMateriaRead,
    summary="Ver umbral de aprobación de una asignación",
)
async def get_umbral(
    asignacion_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_ver),
    svc: UmbralMateriaService = Depends(_get_umbral_svc),
) -> UmbralMateriaRead:
    """Return the approval threshold for the given asignacion.

    Returns defaults (umbral_pct=60, valores_aprobatorios defaults) if not configured.
    """
    return await svc.get(asignacion_id)

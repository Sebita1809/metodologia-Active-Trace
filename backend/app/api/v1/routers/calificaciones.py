"""Endpoints for grade import and threshold configuration.

CLEAN-ARCH: Thin router — delegates all business logic to CalificacionService.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user,
    get_db,
    get_request_metadata,
    RequestMetadata,
    UserContext,
)
from app.core.permissions import require_permission
from app.schemas.calificaciones import (
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportPreviewResponse,
    UmbralConfigResponse,
    UmbralConfigUpdate,
)
from app.services.usuarios.calificacion_service import CalificacionService

router = APIRouter(prefix="/calificaciones", tags=["calificaciones"])


@router.post(
    "/import/preview",
    response_model=ImportPreviewResponse,
    status_code=status.HTTP_200_OK,
)
async def import_preview(
    file: UploadFile = File(...),
    materia_id: uuid.UUID = Form(...),
    cohorte_id: uuid.UUID = Form(...),
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("calificaciones:importar")),
    db: AsyncSession = Depends(get_db),
):
    service = CalificacionService(db, current_user.tenant_id)
    return await service.import_preview(file, materia_id, cohorte_id)


@router.post(
    "/import/confirm",
    response_model=ImportConfirmResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_confirm(
    body: ImportConfirmRequest,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("calificaciones:importar")),
    db: AsyncSession = Depends(get_db),
    metadata: RequestMetadata = Depends(get_request_metadata),
):
    service = CalificacionService(db, current_user.tenant_id)
    return await service.import_confirm(
        preview_token=body.preview_token,
        materia_id=body.materia_id,
        cohorte_id=body.cohorte_id,
        selected_actividades=body.selected_actividades,
        actor_id=current_user.user_id,
        impersonado_id=(
            current_user.impersonated_user_id
            if current_user.is_impersonating
            else None
        ),
        ip=metadata.ip,
        user_agent=metadata.user_agent,
    )


@router.get(
    "/{materia_id}/{cohorte_id}",
    response_model=list,
    status_code=status.HTTP_200_OK,
)
async def list_calificaciones(
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("calificaciones:importar")),
    db: AsyncSession = Depends(get_db),
):
    service = CalificacionService(db, current_user.tenant_id)
    return await service.list(materia_id, cohorte_id)


@router.delete(
    "/{materia_id}/{cohorte_id}",
    status_code=status.HTTP_200_OK,
)
async def clear_calificaciones(
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("calificaciones:importar")),
    db: AsyncSession = Depends(get_db),
    metadata: RequestMetadata = Depends(get_request_metadata),
):
    service = CalificacionService(db, current_user.tenant_id)
    return await service.clear(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        actor_id=current_user.user_id,
        impersonado_id=(
            current_user.impersonated_user_id
            if current_user.is_impersonating
            else None
        ),
        ip=metadata.ip,
        user_agent=metadata.user_agent,
    )


@router.put(
    "/umbral",
    response_model=UmbralConfigResponse,
    status_code=status.HTTP_200_OK,
)
async def update_umbral(
    body: UmbralConfigUpdate,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("calificaciones:importar")),
    db: AsyncSession = Depends(get_db),
):
    service = CalificacionService(db, current_user.tenant_id)
    return await service.update_umbral(body.model_dump(exclude_none=True))

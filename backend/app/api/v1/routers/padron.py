"""Router for padron import, version management, and Moodle sync (C-09)."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, UserContext
from app.core.permissions import require_permission
from app.models.tenant import Tenant
from app.schemas.padron import (
    PadronImportConfirmRequest,
    PadronSyncMoodleRequest,
)
from app.services.padron.padron_import_service import PadronImportService
from app.services.padron.padron_service import PadronService

router = APIRouter(prefix="/padron", tags=["padron"])


async def _check_profesor_scope(
    current_user: UserContext,
    db: AsyncSession,
    materia_id: uuid.UUID,
) -> None:
    """Verify PROFESOR (propio scope) is assigned to the materia."""
    if "PROFESOR" in current_user.roles:
        service = PadronService(db, current_user.tenant_id)
        if not await service.verify_profesor_materia(current_user.user_id, materia_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not assigned to this materia",
            )


@router.post("/import/preview")
async def preview_import(
    file: UploadFile = File(...),
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("padron:importar")),
    db: AsyncSession = Depends(get_db),
):
    """Phase 1: Parse uploaded file and return preview without persisting."""
    service = PadronImportService(db, current_user.tenant_id)
    return await service.preview_file(file)


@router.post("/import/confirm")
async def confirm_import(
    body: PadronImportConfirmRequest,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("padron:importar")),
    db: AsyncSession = Depends(get_db),
):
    """Phase 2: Persist padron from preview token."""
    await _check_profesor_scope(current_user, db, body.materia_id)
    service = PadronImportService(db, current_user.tenant_id)
    return await service.confirm_import(
        preview_token=body.preview_token,
        materia_id=body.materia_id,
        cohorte_id=body.cohorte_id,
        actor_id=current_user.user_id,
    )


@router.get("/{materia_id}/{cohorte_id}")
async def get_active_version(
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("padron:importar")),
    db: AsyncSession = Depends(get_db),
):
    """Get the active version with all entries for a materia+cohorte."""
    await _check_profesor_scope(current_user, db, materia_id)
    service = PadronService(db, current_user.tenant_id)
    return await service.get_active_version(materia_id, cohorte_id)


@router.get("/{materia_id}/{cohorte_id}/versiones")
async def list_versions(
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("padron:importar")),
    db: AsyncSession = Depends(get_db),
):
    """List all versions for a materia+cohorte, ordered by date desc."""
    await _check_profesor_scope(current_user, db, materia_id)
    service = PadronService(db, current_user.tenant_id)
    return await service.list_versions(materia_id, cohorte_id)


@router.post("/{materia_id}/{cohorte_id}/activar/{version_id}")
async def activate_version(
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    version_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("padron:importar")),
    db: AsyncSession = Depends(get_db),
):
    """Activate a version, deactivating any previous active version."""
    await _check_profesor_scope(current_user, db, materia_id)
    service = PadronService(db, current_user.tenant_id)
    return await service.activate_version(version_id, current_user.user_id)


@router.post("/sync/moodle")
async def sync_from_moodle(
    body: PadronSyncMoodleRequest,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("padron:importar")),
    db: AsyncSession = Depends(get_db),
):
    """Sync padron from Moodle WS for a materia+cohorte."""
    await _check_profesor_scope(current_user, db, body.materia_id)

    result = await db.execute(
        select(Tenant.config).where(Tenant.id == current_user.tenant_id)
    )
    tenant_config = result.scalar_one_or_none()
    if not tenant_config or not tenant_config.get("moodle_ws_url") or not tenant_config.get("moodle_ws_token"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant has no Moodle WS configured. Use file import instead.",
        )

    service = PadronService(db, current_user.tenant_id)
    return await service.sync_from_moodle(
        materia_id=body.materia_id,
        cohorte_id=body.cohorte_id,
        moodle_course_id=body.moodle_course_id,
        ws_url=tenant_config["moodle_ws_url"],
        ws_token=tenant_config["moodle_ws_token"],
        actor_id=current_user.user_id,
    )


@router.delete("/{materia_id}/{cohorte_id}")
async def clear_subject_data(
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("padron:importar")),
    db: AsyncSession = Depends(get_db),
):
    """Hard delete all padron data for a materia+cohorte (RN-04)."""
    await _check_profesor_scope(current_user, db, materia_id)
    service = PadronService(db, current_user.tenant_id)
    return await service.clear_subject_data(materia_id, cohorte_id, current_user.user_id)

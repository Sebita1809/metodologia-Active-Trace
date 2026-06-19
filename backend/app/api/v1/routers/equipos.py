"""Router for teaching team operations (C-08)."""
import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_codes import AuditAction
from app.core.dependencies import get_current_user, get_db, UserContext
from app.core.permissions import require_permission
from app.repositories.usuarios.asignacion_repository import AsignacionRepository
from app.services.audit.audit_service import audit_record
from app.services.equipos.equipo_docente_service import EquipoDocenteService
from app.services.equipos.export_service import ExportService

router = APIRouter(prefix="/equipos", tags=["equipos"])


@router.get("/mis-equipos")
async def mis_equipos(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = EquipoDocenteService(db, current_user.tenant_id)
    return await service.get_mis_equipos(current_user.user_id)


@router.get("/materias/{materia_id}")
async def equipo_por_materia(
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID | None = Query(default=None),
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("equipos:asignar")),
    db: AsyncSession = Depends(get_db),
):
    service = EquipoDocenteService(db, current_user.tenant_id)
    return await service.get_equipo_por_materia(materia_id, cohorte_id)


@router.post("/asignacion-masiva", status_code=status.HTTP_201_CREATED)
async def asignacion_masiva(
    body: dict,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("equipos:asignar")),
    db: AsyncSession = Depends(get_db),
):
    service = EquipoDocenteService(db, current_user.tenant_id)
    result = await service.asignacion_masiva(body)
    await audit_record(
        db, current_user.user_id, AuditAction.ASIGNACION_MODIFICAR,
        tenant_id=current_user.tenant_id,
        materia_id=body.get("materia_id"),
        detalle={"accion": "asignacion_masiva", "conteo": len(result)},
    )
    return result


@router.post("/clonar")
async def clonar_equipo(
    body: dict,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("equipos:asignar")),
    db: AsyncSession = Depends(get_db),
):
    service = EquipoDocenteService(db, current_user.tenant_id)
    result = await service.clonar_equipo(body)
    creadas = result["creadas"]
    await audit_record(
        db, current_user.user_id, AuditAction.ASIGNACION_MODIFICAR,
        tenant_id=current_user.tenant_id,
        materia_id=body.get("materia_id"),
        detalle={
            "accion": "clonar",
            "origen": str(body.get("cohorte_origen_id")),
            "destino": str(body.get("cohorte_destino_id")),
            "conteo": result["conteo"],
        },
    )
    return JSONResponse(content=jsonable_encoder(creadas), status_code=200 if len(creadas) == 0 else 201)


@router.patch("/vigencia")
async def modificar_vigencia(
    body: dict,
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("equipos:asignar")),
    db: AsyncSession = Depends(get_db),
):
    service = EquipoDocenteService(db, current_user.tenant_id)
    result = await service.modificar_vigencia(body)
    await audit_record(
        db, current_user.user_id, AuditAction.ASIGNACION_MODIFICAR,
        tenant_id=current_user.tenant_id,
        materia_id=body.get("materia_id"),
        detalle={"accion": "modificar_vigencia", "conteo": result["conteo"]},
    )
    return result


@router.get("/{materia_id}/exportar")
async def exportar_equipo(
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID | None = Query(default=None),
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("equipos:asignar")),
    db: AsyncSession = Depends(get_db),
):
    repo = AsignacionRepository(db, current_user.tenant_id)
    entities = await repo.list_vigentes_por_materia_y_cohorte(materia_id, cohorte_id)
    export_service = ExportService(repo)
    csv_file = await export_service.generar_csv_equipo(entities)
    return StreamingResponse(
        iter([csv_file.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=equipo_{materia_id}.csv"},
    )

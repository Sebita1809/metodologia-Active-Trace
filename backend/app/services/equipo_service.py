"""
app/services/equipo_service.py — EquipoService.

Business logic for team management operations (C-08).

Rules enforced:
  - estado_vigencia is DERIVED — never persisted; computed at read time.
  - usuario_id from JWT (CurrentUser.user_id), never from query params.
  - Audit: ASIGNACION_MODIFICAR on all write operations.
  - buscar_usuarios validates len(q) >= 2, raises HTTPException(422) otherwise.
  - clone_from is transactional; rollback handled by caller session.
  - CSV export uses async generator, no temp files.

Implemented: C-08 (equipos-docentes)
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import date
from typing import Literal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.models.asignacion import Asignacion
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.asignacion import ROL_NEGOCIO_VALUES
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
from app.services.audit_codes import AccionAuditoria
from app.services.audit_service import AuditService


def _compute_estado_vigencia(
    desde: date,
    hasta: date | None,
    hoy: date,
) -> Literal["Vigente", "Vencida"]:
    """Compute the derived vigencia status.

    Vigente: desde <= hoy AND (hasta is None OR hoy <= hasta)
    Vencida: hasta is not None AND hasta < hoy
    """
    if hasta is not None and hasta < hoy:
        return "Vencida"
    return "Vigente"


class EquipoService:
    """Team management operations for teaching assignments.

    All operations scoped to *tenant_id* from JWT — never from request body.
    Audit log is written for all write operations.
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._repo = AsignacionRepository(session=session, tenant_id=tenant_id)
        self._usuario_repo = UsuarioRepository(session=session, tenant_id=tenant_id)
        self._audit_svc = AuditService(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_rol(self, rol: str) -> None:
        """Raise HTTPException(422) if rol is not a valid business role."""
        if rol not in ROL_NEGOCIO_VALUES:
            raise HTTPException(
                status_code=422,
                detail=f"Rol inválido: '{rol}'. Valores permitidos: {', '.join(ROL_NEGOCIO_VALUES)}",
            )

    def _asignacion_to_item(self, a: Asignacion) -> MiEquipoItem:
        """Build MiEquipoItem with derived estado_vigencia."""
        hoy = date.today()
        return MiEquipoItem(
            id=a.id,
            usuario_id=a.usuario_id,
            rol=a.rol,
            materia_id=a.materia_id,
            carrera_id=a.carrera_id,
            cohorte_id=a.cohorte_id,
            comisiones=a.comisiones if a.comisiones is not None else [],
            desde=a.desde,
            hasta=a.hasta,
            estado_vigencia=_compute_estado_vigencia(a.desde, a.hasta, hoy),
            responsable_id=a.responsable_id,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_mis_equipos(
        self,
        current_user: CurrentUser,
        *,
        estado_vigencia: str | None = None,
        materia_id: uuid.UUID | None = None,
        rol: str | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
    ) -> list[MiEquipoItem]:
        """Return assignments for the authenticated user from JWT identity.

        usuario_id is ALWAYS taken from current_user.user_id — never from params.
        """
        asignaciones = await self._repo.list_by_usuario(
            current_user.user_id,
            estado_vigencia=estado_vigencia,
            materia_id=materia_id,
            rol=rol,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
        )
        return [self._asignacion_to_item(a) for a in asignaciones]

    async def buscar_usuarios(
        self,
        current_user: CurrentUser,  # noqa: ARG002 — included for audit/identity traceability
        q: str,
    ) -> list[UsuarioBusquedaItem]:
        """Autocomplete users by nombre/apellidos.

        Raises HTTPException(422) if len(q) < 2.
        Returns UsuarioBusquedaItem list — no PII ciphertexts exposed.
        """
        if len(q) < 2:
            raise HTTPException(
                status_code=422,
                detail="El parámetro 'q' debe tener al menos 2 caracteres.",
            )
        usuarios = await self._usuario_repo.search_by_name(q)
        return [
            UsuarioBusquedaItem(id=u.id, nombre=u.nombre, apellidos=u.apellidos)
            for u in usuarios
        ]

    async def asignar_masiva(
        self,
        current_user: CurrentUser,
        request: AsignacionMasivaRequest,
    ) -> AsignacionMasivaResponse:
        """Bulk-assign a role to multiple users in one transaction.

        Creates one Asignacion per usuario_id in request.usuario_ids.
        Registers ASIGNACION_MODIFICAR audit log with filas_afectadas.
        """
        self._validate_rol(request.rol)

        asignaciones = [
            Asignacion(
                tenant_id=self._tenant_id,
                usuario_id=uid,
                rol=request.rol,
                materia_id=request.materia_id,
                carrera_id=request.carrera_id,
                cohorte_id=request.cohorte_id,
                comisiones=request.comisiones if request.comisiones is not None else [],
                desde=request.desde,
                hasta=request.hasta,
            )
            for uid in request.usuario_ids
        ]

        persisted = await self._repo.bulk_create(asignaciones)
        count = len(persisted)

        await self._audit_svc.registrar(
            current_user,
            AccionAuditoria.ASIGNACION_MODIFICAR,
            filas_afectadas=count,
            ip=None,
            user_agent=None,
        )

        return AsignacionMasivaResponse(asignadas=count)

    async def clonar_equipo(
        self,
        current_user: CurrentUser,
        request: ClonarEquipoRequest,
    ) -> ClonarEquipoResponse:
        """Clone vigent assignments from origin context to destination context.

        1. Reads vigentes from origin via clone_from.
        2. Creates new Asignacion objects with destination context + new dates.
        3. Bulk creates in one flush.
        4. Registers audit log.
        """
        origen_asignaciones = await self._repo.clone_from(
            origen_materia_id=request.origen.materia_id,
            origen_cohorte_id=request.origen.cohorte_id,
        )

        new_asignaciones = [
            Asignacion(
                tenant_id=self._tenant_id,
                usuario_id=src.usuario_id,
                rol=src.rol,
                materia_id=request.destino.materia_id,
                carrera_id=request.destino.carrera_id,
                cohorte_id=request.destino.cohorte_id,
                comisiones=src.comisiones if src.comisiones is not None else [],
                responsable_id=src.responsable_id,
                desde=request.desde,
                hasta=request.hasta,
            )
            for src in origen_asignaciones
        ]

        count = 0
        if new_asignaciones:
            persisted = await self._repo.bulk_create(new_asignaciones)
            count = len(persisted)

        await self._audit_svc.registrar(
            current_user,
            AccionAuditoria.ASIGNACION_MODIFICAR,
            filas_afectadas=count,
            ip=None,
            user_agent=None,
        )

        return ClonarEquipoResponse(clonadas=count)

    async def modificar_vigencia(
        self,
        current_user: CurrentUser,
        request: ModificarVigenciaRequest,
    ) -> ModificarVigenciaResponse:
        """Bulk-update desde/hasta for all matching assignments.

        Returns the number of rows modified.
        hasta=None sets open-ended validity (UPDATE hasta = NULL).
        """
        filas = await self._repo.bulk_update_vigencia(
            materia_id=request.filtro.materia_id,
            carrera_id=request.filtro.carrera_id,
            cohorte_id=request.filtro.cohorte_id,
            desde=request.desde,
            hasta=request.hasta,
        )

        await self._audit_svc.registrar(
            current_user,
            AccionAuditoria.ASIGNACION_MODIFICAR,
            filas_afectadas=filas,
            ip=None,
            user_agent=None,
        )

        return ModificarVigenciaResponse(modificadas=filas)

    async def exportar_equipo(
        self,
        current_user: CurrentUser,  # noqa: ARG002 — included for future audit traceability
        *,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
    ) -> AsyncGenerator[str, None]:
        """Generate CSV rows for streaming export.

        Yields the header line then one line per assignment.
        Computes estado_vigencia per row (not stored).
        No temp files — caller wraps in StreamingResponse.
        """
        rows = await self._repo.list_for_export(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
        )

        async def _generate() -> AsyncGenerator[str, None]:
            yield "usuario_id,nombre,apellidos,rol,materia,carrera,cohorte,comisiones,desde,hasta,estado_vigencia\n"
            hoy = date.today()
            for row in rows:
                estado = _compute_estado_vigencia(row.desde, row.hasta, hoy)
                comisiones_str = "|".join(row.comisiones) if row.comisiones else ""
                hasta_str = str(row.hasta) if row.hasta else ""
                yield (
                    f"{row.usuario_id},{row.nombre},{row.apellidos},{row.rol},"
                    f"{row.materia_nombre or ''},{row.carrera_nombre or ''},"
                    f"{row.cohorte_nombre or ''},{comisiones_str},"
                    f"{row.desde},{hasta_str},{estado}\n"
                )

        return _generate()

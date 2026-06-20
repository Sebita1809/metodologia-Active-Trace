"""
app/services/aviso_service.py — AvisoService.

Business logic for institutional notice board operations (C-15).

Rules enforced:
  - tenant_id from JWT (CurrentUser.tenant_id), never from request body.
  - RBAC enforced at router layer (avisos:publicar for write ops).
  - Soft delete only — never hard delete.
  - listar_para_usuario resolves user cohortes/materias from repositories.

Implemented: C-15 (avisos-y-acknowledgment)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.models.aviso import Aviso
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.aviso_repository import AvisoRepository
from app.schemas.avisos import AvisoCreate, AvisoListItem, AvisoResponse, AvisoUpdate


class AvisoService:
    """Notice board operations for a single tenant.

    All operations scoped to *tenant_id* from JWT — never from request body.
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._repo = AvisoRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_or_404(self, aviso_id: uuid.UUID) -> Aviso:
        """Return the aviso or raise 404 if not found."""
        aviso = await self._repo.get(aviso_id)
        if aviso is None:
            raise HTTPException(status_code=404, detail="Aviso no encontrado")
        return aviso

    def _to_response(self, aviso: Aviso, total_acks: int = 0) -> AvisoResponse:
        """Build AvisoResponse from ORM model + acks count."""
        return AvisoResponse(
            id=aviso.id,
            tenant_id=aviso.tenant_id,
            alcance=aviso.alcance,
            materia_id=aviso.materia_id,
            cohorte_id=aviso.cohorte_id,
            rol_destino=aviso.rol_destino,
            severidad=aviso.severidad,
            titulo=aviso.titulo,
            cuerpo=aviso.cuerpo,
            inicio_en=aviso.inicio_en,
            fin_en=aviso.fin_en,
            orden=aviso.orden,
            activo=aviso.activo,
            requiere_ack=aviso.requiere_ack,
            created_at=aviso.created_at,
            updated_at=aviso.updated_at,
            total_acks=total_acks,
        )

    def _to_list_item(self, aviso: Aviso) -> AvisoListItem:
        """Build AvisoListItem (no acks) for the user-facing feed."""
        return AvisoListItem(
            id=aviso.id,
            alcance=aviso.alcance,
            severidad=aviso.severidad,
            titulo=aviso.titulo,
            cuerpo=aviso.cuerpo,
            inicio_en=aviso.inicio_en,
            fin_en=aviso.fin_en,
            orden=aviso.orden,
            activo=aviso.activo,
            requiere_ack=aviso.requiere_ack,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def crear(
        self,
        data: AvisoCreate,
        current_user: CurrentUser,  # noqa: ARG002 — identity from JWT
    ) -> AvisoResponse:
        """Create a new aviso for this tenant."""
        aviso = Aviso(
            tenant_id=self._tenant_id,
            alcance=data.alcance,
            materia_id=data.materia_id,
            cohorte_id=data.cohorte_id,
            rol_destino=data.rol_destino,
            severidad=data.severidad,
            titulo=data.titulo,
            cuerpo=data.cuerpo,
            inicio_en=data.inicio_en,
            fin_en=data.fin_en,
            orden=data.orden,
            activo=data.activo,
            requiere_ack=data.requiere_ack,
        )
        aviso = await self._repo.create(aviso)
        return self._to_response(aviso, total_acks=0)

    async def actualizar(
        self,
        aviso_id: uuid.UUID,
        data: AvisoUpdate,
        current_user: CurrentUser,  # noqa: ARG002
    ) -> AvisoResponse:
        """Update an existing aviso. Raises 404 if not found."""
        await self._get_or_404(aviso_id)
        update_data = data.model_dump(exclude_none=True)
        updated = await self._repo.update(aviso_id, **update_data)
        if updated is None:
            raise HTTPException(status_code=404, detail="Aviso no encontrado")
        acks = await self._repo.contar_acks(aviso_id)
        return self._to_response(updated, total_acks=acks)

    async def eliminar(
        self,
        aviso_id: uuid.UUID,
        current_user: CurrentUser,  # noqa: ARG002
    ) -> None:
        """Soft-delete an aviso. Raises 404 if not found."""
        deleted = await self._repo.soft_delete(aviso_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Aviso no encontrado")

    async def listar_admin(
        self,
        current_user: CurrentUser,  # noqa: ARG002
    ) -> list[AvisoResponse]:
        """Return all non-deleted avisos for this tenant with total_acks each."""
        avisos = await self._repo.list_admin()
        result = []
        for aviso in avisos:
            acks = await self._repo.contar_acks(aviso.id)
            result.append(self._to_response(aviso, total_acks=acks))
        return result

    async def listar_para_usuario(
        self,
        current_user: CurrentUser,
    ) -> list[AvisoListItem]:
        """Return avisos visible to the authenticated user at this moment.

        Resolves user's cohorte and materia memberships from AsignacionRepository.
        Tenant isolation: user sees only their tenant's avisos.
        """
        asignacion_repo = AsignacionRepository(
            session=self._session,
            tenant_id=self._tenant_id,
        )
        # Get user's assignments to derive cohorte/materia membership
        asignaciones = await asignacion_repo.list_with_filters(
            usuario_id=current_user.user_id
        )

        cohorte_ids = list(
            {a.cohorte_id for a in asignaciones if a.cohorte_id is not None}
        )
        materia_ids = list(
            {a.materia_id for a in asignaciones if a.materia_id is not None}
        )

        # Use first role from JWT roles list (primary role)
        usuario_rol = current_user.roles[0] if current_user.roles else "ALUMNO"
        ahora = datetime.now(tz=timezone.utc)

        avisos = await self._repo.listar_para_usuario(
            usuario_id=current_user.user_id,
            rol=usuario_rol,
            cohorte_ids=cohorte_ids,
            materia_ids=materia_ids,
            ahora=ahora,
        )
        return [self._to_list_item(a) for a in avisos]

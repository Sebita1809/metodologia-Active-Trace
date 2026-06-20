"""
app/services/ack_service.py — AckService.

Business logic for aviso acknowledgment operations (C-15).

Rules enforced:
  - Aviso must be vigente (within its time window) to accept ACK.
  - User must be in the aviso's audience to ACK it.
  - Duplicate ACK raises 409 Conflict.
  - tenant_id from JWT — never from request body.

Implemented: C-15 (avisos-y-acknowledgment)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.repositories.acknowledgment_aviso_repository import AcknowledgmentAvisoRepository
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.aviso_repository import AvisoRepository
from app.schemas.avisos import AckResponse
from app.services.aviso_helpers import aviso_es_vigente, usuario_en_audiencia


class AckService:
    """Acknowledgment operations for aviso notices.

    All operations scoped to *tenant_id* from JWT — never from request body.
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._aviso_repo = AvisoRepository(session=session, tenant_id=tenant_id)
        self._ack_repo = AcknowledgmentAvisoRepository(
            session=session, tenant_id=tenant_id
        )

    async def acusar(
        self,
        aviso_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> AckResponse:
        """Acknowledge a notice for the authenticated user.

        Raises
        ------
        HTTPException(404)
            When the aviso does not exist in this tenant.
        HTTPException(404)
            When the aviso is no longer vigente (expired or not yet started).
        HTTPException(403)
            When the user is not in the aviso's target audience.
        HTTPException(409)
            When the user has already acknowledged this aviso.
        """
        # Load aviso (tenant-scoped)
        aviso = await self._aviso_repo.get(aviso_id)
        if aviso is None:
            raise HTTPException(status_code=404, detail="Aviso no encontrado")

        ahora = datetime.now(tz=timezone.utc)

        # Validate vigencia
        if not aviso_es_vigente(aviso.inicio_en, aviso.fin_en, ahora):
            raise HTTPException(status_code=404, detail="Aviso no está vigente")

        # Resolve user audience membership
        asignacion_repo = AsignacionRepository(
            session=self._session,
            tenant_id=self._tenant_id,
        )
        asignaciones = await asignacion_repo.list_with_filters(
            usuario_id=current_user.user_id
        )
        cohorte_ids = list(
            {a.cohorte_id for a in asignaciones if a.cohorte_id is not None}
        )
        materia_ids = list(
            {a.materia_id for a in asignaciones if a.materia_id is not None}
        )
        usuario_rol = current_user.roles[0] if current_user.roles else "ALUMNO"

        if not usuario_en_audiencia(
            alcance=aviso.alcance,
            rol_destino=aviso.rol_destino,
            cohorte_id=aviso.cohorte_id,
            materia_id=aviso.materia_id,
            usuario_rol=usuario_rol,
            usuario_cohorte_ids=cohorte_ids,
            usuario_materia_ids=materia_ids,
        ):
            raise HTTPException(
                status_code=403,
                detail="El usuario no pertenece a la audiencia de este aviso",
            )

        # Create acknowledgment (raises LookupError on duplicate → 409)
        try:
            ack = await self._ack_repo.create_ack(
                aviso_id=aviso_id,
                usuario_id=current_user.user_id,
                tenant_id=self._tenant_id,
            )
        except LookupError:
            raise HTTPException(
                status_code=409,
                detail="El usuario ya acusó recibo de este aviso",
            )

        return AckResponse(
            aviso_id=ack.aviso_id,
            usuario_id=ack.usuario_id,
            confirmado_at=ack.confirmado_at,
        )

"""
app/repositories/aviso_repository.py — AvisoRepository.

Extends BaseRepository[Aviso] with:
  - list_admin: all active (non-deleted) avisos for a tenant
  - listar_para_usuario: audience-filtered + vigencia-filtered query for user feed
  - contar_acks: count of acknowledgments for a given aviso

Tenant isolation is inherited from BaseRepository (mandatory).
All queries start from _base_query() to guarantee soft-delete filter.

Implemented: C-15 (avisos-y-acknowledgment)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, exists, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acknowledgment_aviso import AcknowledgmentAviso
from app.models.aviso import Aviso
from app.repositories.base import BaseRepository


class AvisoRepository(BaseRepository[Aviso]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Aviso, session=session, tenant_id=tenant_id)

    async def list_admin(self) -> list[Aviso]:
        """Return all active (non-deleted) avisos for this tenant, ordered by orden asc.

        Includes both active=True and active=False avisos (admin can see all).
        Excludes soft-deleted rows (from _base_query).
        """
        stmt = self._base_query().order_by(Aviso.orden.asc(), Aviso.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def listar_para_usuario(
        self,
        usuario_id: uuid.UUID,
        rol: str,
        cohorte_ids: list[uuid.UUID],
        materia_ids: list[uuid.UUID],
        ahora: datetime,
    ) -> list[Aviso]:
        """Return avisos visible to a specific user at *ahora*.

        Filters applied:
          1. Tenant isolation + soft-delete (from _base_query)
          2. activo=True
          3. Vigencia: inicio_en <= ahora <= fin_en
          4. Audience: Global OR (PorRol AND rol_destino=rol) OR
                       (PorCohorte AND cohorte_id IN cohorte_ids) OR
                       (PorMateria AND materia_id IN materia_ids)
          5. If requiere_ack=True: only show if NOT yet acknowledged by usuario_id

        Results ordered by orden ASC.
        """
        # Build audience filter
        audience_conditions = [
            Aviso.alcance == "Global",
            and_(Aviso.alcance == "PorRol", Aviso.rol_destino == rol),
        ]
        if cohorte_ids:
            audience_conditions.append(
                and_(Aviso.alcance == "PorCohorte", Aviso.cohorte_id.in_(cohorte_ids))
            )
        else:
            # No cohorte_ids → PorCohorte never matches
            audience_conditions.append(
                and_(Aviso.alcance == "PorCohorte", False)  # type: ignore[arg-type]
            )
        if materia_ids:
            audience_conditions.append(
                and_(Aviso.alcance == "PorMateria", Aviso.materia_id.in_(materia_ids))
            )
        else:
            audience_conditions.append(
                and_(Aviso.alcance == "PorMateria", False)  # type: ignore[arg-type]
            )

        # ACK subquery: aviso already acknowledged by this user
        ack_exists = exists(
            select(AcknowledgmentAviso.id).where(
                and_(
                    AcknowledgmentAviso.aviso_id == Aviso.id,
                    AcknowledgmentAviso.usuario_id == usuario_id,
                    AcknowledgmentAviso.deleted_at.is_(None),
                )
            )
        )

        stmt = (
            self._base_query()
            .where(Aviso.activo.is_(True))
            .where(Aviso.inicio_en <= ahora)
            .where(Aviso.fin_en >= ahora)
            .where(or_(*audience_conditions))
            .where(
                or_(
                    Aviso.requiere_ack.is_(False),
                    not_(ack_exists),
                )
            )
            .order_by(Aviso.orden.asc())
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def contar_acks(self, aviso_id: uuid.UUID) -> int:
        """Return the total number of non-deleted acknowledgments for *aviso_id*."""
        stmt = (
            select(func.count(AcknowledgmentAviso.id))
            .where(AcknowledgmentAviso.aviso_id == aviso_id)
            .where(AcknowledgmentAviso.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

"""
app/repositories/reserva_evaluacion_repository.py — ReservaEvaluacionRepository.

Extends BaseRepository[ReservaEvaluacion] with domain-specific queries:
  - create_reserva: wraps create() capturing IntegrityError (duplicate active reservation)
  - cambiar_estado: transition estado (Activa → Cancelada)
  - list_by_evaluacion: list all reservas for a specific evaluacion

All queries are scoped to self._tenant_id — no cross-tenant leaks.

Implemented: C-14 (evaluaciones-y-coloquios)
"""
from __future__ import annotations

import uuid

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reserva_evaluacion import ReservaEvaluacion
from app.repositories.base import BaseRepository


class ReservaEvaluacionRepository(BaseRepository[ReservaEvaluacion]):
    """Tenant-scoped repository for ReservaEvaluacion records."""

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=ReservaEvaluacion, session=session, tenant_id=tenant_id)

    async def create_reserva(self, reserva: ReservaEvaluacion) -> ReservaEvaluacion | None:
        """Persist a new reserva, returning None if there is a uniqueness conflict.

        The unique partial index (evaluacion_id, alumno_id) WHERE estado='Activa'
        prevents duplicate active reservations. Catches IntegrityError and returns
        None so the service can raise HTTP 409.

        Parameters
        ----------
        reserva:
            Pre-built ReservaEvaluacion instance with tenant_id already set.
        """
        try:
            return await self.create(reserva)
        except IntegrityError:
            await self._session.rollback()
            return None

    async def cambiar_estado(
        self,
        reserva_id: uuid.UUID,
        nuevo_estado: str,
    ) -> bool:
        """Transition the estado of a reserva to *nuevo_estado*.

        Scoped to this tenant — cannot update cross-tenant records.

        Returns True if a record was found and updated, False otherwise.
        """
        stmt = (
            update(ReservaEvaluacion)
            .where(ReservaEvaluacion.id == reserva_id)
            .where(ReservaEvaluacion.tenant_id == self._tenant_id)
            .where(ReservaEvaluacion.deleted_at.is_(None))
            .values(estado=nuevo_estado)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0  # type: ignore[return-value]

    async def list_by_evaluacion(self, evaluacion_id: uuid.UUID) -> list[ReservaEvaluacion]:
        """Return all active reservas for a specific evaluacion.

        Filters: tenant_id = self._tenant_id AND evaluacion_id = evaluacion_id
        AND deleted_at IS NULL.
        """
        return await self.list(evaluacion_id=evaluacion_id)

    async def get_reserva_activa_alumno(
        self,
        evaluacion_id: uuid.UUID,
        alumno_id: uuid.UUID,
    ) -> ReservaEvaluacion | None:
        """Return the active reserva for *alumno_id* in *evaluacion_id*, or None."""
        stmt = (
            self._base_query()
            .where(ReservaEvaluacion.evaluacion_id == evaluacion_id)
            .where(ReservaEvaluacion.alumno_id == alumno_id)
            .where(ReservaEvaluacion.estado == "Activa")
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

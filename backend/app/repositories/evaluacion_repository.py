"""
app/repositories/evaluacion_repository.py — EvaluacionRepository.

Extends BaseRepository[Evaluacion] with domain-specific queries:
  - contar_reservas_activas_en_fecha: count active reservas for a given date
  - metricas_panel: 4 aggregated counters for the dashboard

All queries are scoped to self._tenant_id — no cross-tenant leaks.

Implemented: C-14 (evaluaciones-y-coloquios)
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluacion import Evaluacion
from app.models.reserva_evaluacion import ReservaEvaluacion
from app.models.resultado_evaluacion import ResultadoEvaluacion
from app.repositories.base import BaseRepository


class EvaluacionRepository(BaseRepository[Evaluacion]):
    """Tenant-scoped repository for Evaluacion records."""

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Evaluacion, session=session, tenant_id=tenant_id)

    async def contar_reservas_activas_en_fecha(
        self,
        evaluacion_id: uuid.UUID,
        fecha: date,
    ) -> int:
        """Count active reservations for *evaluacion_id* on *fecha*.

        Used to check cupo_por_dia before creating a new reservation.
        Scoped to this tenant.

        Parameters
        ----------
        evaluacion_id:
            The evaluacion to check.
        fecha:
            The calendar date to count for.
        """
        stmt = (
            select(func.count())
            .select_from(ReservaEvaluacion)
            .where(ReservaEvaluacion.tenant_id == self._tenant_id)
            .where(ReservaEvaluacion.evaluacion_id == evaluacion_id)
            .where(ReservaEvaluacion.estado == "Activa")
            .where(ReservaEvaluacion.deleted_at.is_(None))
            .where(func.date(ReservaEvaluacion.fecha_hora) == fecha)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def metricas_panel(self) -> dict[str, int]:
        """Return 4 aggregated counters for the coloquios dashboard panel.

        Returns
        -------
        dict with keys:
            total_evaluaciones       — count of all active evaluaciones
            total_reservas_activas   — count of all active reservas
            total_resultados         — count of all resultados
            evaluaciones_cerradas    — count of evaluaciones with estado='Cerrada'
        """
        # Total evaluaciones (active, non-deleted)
        eval_stmt = (
            select(func.count())
            .select_from(Evaluacion)
            .where(Evaluacion.tenant_id == self._tenant_id)
            .where(Evaluacion.deleted_at.is_(None))
        )
        total_evaluaciones = (await self._session.execute(eval_stmt)).scalar_one()

        # Evaluaciones cerradas
        cerradas_stmt = (
            select(func.count())
            .select_from(Evaluacion)
            .where(Evaluacion.tenant_id == self._tenant_id)
            .where(Evaluacion.deleted_at.is_(None))
            .where(Evaluacion.estado == "Cerrada")
        )
        evaluaciones_cerradas = (await self._session.execute(cerradas_stmt)).scalar_one()

        # Total reservas activas
        reservas_stmt = (
            select(func.count())
            .select_from(ReservaEvaluacion)
            .where(ReservaEvaluacion.tenant_id == self._tenant_id)
            .where(ReservaEvaluacion.deleted_at.is_(None))
            .where(ReservaEvaluacion.estado == "Activa")
        )
        total_reservas_activas = (await self._session.execute(reservas_stmt)).scalar_one()

        # Total resultados
        resultados_stmt = (
            select(func.count())
            .select_from(ResultadoEvaluacion)
            .where(ResultadoEvaluacion.tenant_id == self._tenant_id)
            .where(ResultadoEvaluacion.deleted_at.is_(None))
        )
        total_resultados = (await self._session.execute(resultados_stmt)).scalar_one()

        return {
            "total_evaluaciones": total_evaluaciones,
            "total_reservas_activas": total_reservas_activas,
            "total_resultados": total_resultados,
            "evaluaciones_cerradas": evaluaciones_cerradas,
        }

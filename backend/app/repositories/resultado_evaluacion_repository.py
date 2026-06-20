"""
app/repositories/resultado_evaluacion_repository.py — ResultadoEvaluacionRepository.

Extends BaseRepository[ResultadoEvaluacion] with domain-specific queries:
  - create_resultado: wraps create() capturing IntegrityError (duplicate)
  - list_by_evaluacion: list all resultados for a specific evaluacion

All queries are scoped to self._tenant_id — no cross-tenant leaks.

Implemented: C-14 (evaluaciones-y-coloquios)
"""
from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resultado_evaluacion import ResultadoEvaluacion
from app.repositories.base import BaseRepository


class ResultadoEvaluacionRepository(BaseRepository[ResultadoEvaluacion]):
    """Tenant-scoped repository for ResultadoEvaluacion records."""

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=ResultadoEvaluacion, session=session, tenant_id=tenant_id)

    async def create_resultado(
        self, resultado: ResultadoEvaluacion
    ) -> ResultadoEvaluacion | None:
        """Persist a new resultado, returning None if there is a uniqueness conflict.

        The unique index (evaluacion_id, alumno_id) prevents duplicate results.
        Catches IntegrityError and returns None so the service can raise HTTP 409.

        Parameters
        ----------
        resultado:
            Pre-built ResultadoEvaluacion instance with tenant_id already set.
        """
        try:
            return await self.create(resultado)
        except IntegrityError:
            await self._session.rollback()
            return None

    async def list_by_evaluacion(self, evaluacion_id: uuid.UUID) -> list[ResultadoEvaluacion]:
        """Return all resultados for a specific evaluacion.

        Filters: tenant_id = self._tenant_id AND evaluacion_id = evaluacion_id
        AND deleted_at IS NULL.
        """
        return await self.list(evaluacion_id=evaluacion_id)

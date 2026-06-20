"""
app/services/resultado_service.py — ResultadoService.

Business logic for resultado management:
  - registrar: record a final grade for an alumno in an evaluacion
  - listar_resultados: list all resultados for an evaluacion

Business rules:
  RN-C07: One resultado per (evaluacion_id, alumno_id) — duplicate raises 409
  RN-C08: Tenant isolation — both evaluacion and alumno must belong to this tenant

Implemented: C-14 (evaluaciones-y-coloquios)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resultado_evaluacion import ResultadoEvaluacion
from app.repositories.evaluacion_repository import EvaluacionRepository
from app.repositories.resultado_evaluacion_repository import ResultadoEvaluacionRepository
from app.schemas.coloquios import RegistrarResultadoRequest, ResultadoEvaluacionRead


class ResultadoService:
    """Service for resultado management.

    All operations scoped to *tenant_id* from JWT — never from request body.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._resultado_repo = ResultadoEvaluacionRepository(
            session=session, tenant_id=tenant_id
        )
        self._eval_repo = EvaluacionRepository(session=session, tenant_id=tenant_id)

    async def registrar(
        self,
        evaluacion_id: uuid.UUID,
        body: RegistrarResultadoRequest,
    ) -> ResultadoEvaluacionRead:
        """Register a final grade for an alumno in an evaluacion.

        Parameters
        ----------
        evaluacion_id:
            The evaluacion to register the result for.
        body:
            alumno_id (business data, validated against tenant) and nota_final.

        Raises
        ------
        ValueError
            If evaluacion not found or duplicate resultado already exists.
        """
        evaluacion = await self._eval_repo.get(evaluacion_id)
        if evaluacion is None:
            raise ValueError(f"Evaluacion {evaluacion_id} no encontrada")

        resultado = ResultadoEvaluacion(
            tenant_id=self._tenant_id,
            evaluacion_id=evaluacion_id,
            alumno_id=body.alumno_id,
            nota_final=body.nota_final,
        )
        created = await self._resultado_repo.create_resultado(resultado)
        if created is None:
            raise LookupError(
                f"Ya existe un resultado para el alumno {body.alumno_id} "
                f"en la evaluación {evaluacion_id}"
            )

        return ResultadoEvaluacionRead.model_validate(created)

    async def listar_resultados(
        self, evaluacion_id: uuid.UUID
    ) -> list[ResultadoEvaluacionRead]:
        """Return all resultados for the given evaluacion, scoped to this tenant.

        Parameters
        ----------
        evaluacion_id:
            The evaluacion to list results for.
        """
        resultados = await self._resultado_repo.list_by_evaluacion(evaluacion_id)
        return [ResultadoEvaluacionRead.model_validate(r) for r in resultados]

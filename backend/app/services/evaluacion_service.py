"""
app/services/evaluacion_service.py — EvaluacionService.

Business logic for evaluacion management:
  - crear: create a new evaluacion (estado='Activa', tenant from JWT)
  - importar_padron: bulk-register alumnos for an evaluacion (validate tenant)
  - listar_con_metricas: list evaluaciones with cupos_libres_hoy computed
  - metricas_panel: return 4 dashboard counters

No DB access outside repositories. Tenant identity always from JWT.

Implemented: C-14 (evaluaciones-y-coloquios)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluacion import Evaluacion
from app.repositories.evaluacion_repository import EvaluacionRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.coloquios import (
    EvaluacionConMetricas,
    EvaluacionCreate,
    EvaluacionRead,
    ImportarPadronRequest,
    ImportarPadronResponse,
    MetricasPanel,
)
from app.services.coloquio_helpers import cupos_libres


class EvaluacionService:
    """Service for evaluacion management.

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
        self._eval_repo = EvaluacionRepository(session=session, tenant_id=tenant_id)

    async def crear(self, body: EvaluacionCreate) -> EvaluacionRead:
        """Create a new evaluacion with estado='Activa'.

        Parameters
        ----------
        body:
            Validated request body. tipo is already validated by the schema.

        Returns
        -------
        EvaluacionRead
            The created evaluacion record.
        """
        evaluacion = Evaluacion(
            tenant_id=self._tenant_id,
            materia_id=body.materia_id,
            cohorte_id=body.cohorte_id,
            tipo=body.tipo,
            estado="Activa",
            instancia=body.instancia,
            dias_disponibles=body.dias_disponibles,
            cupo_por_dia=body.cupo_por_dia,
        )
        created = await self._eval_repo.create(evaluacion)
        return EvaluacionRead.model_validate(created)

    async def importar_padron(
        self,
        evaluacion_id: uuid.UUID,
        body: ImportarPadronRequest,
    ) -> ImportarPadronResponse:
        """Bulk-register alumnos into an evaluacion by importing a padron list.

        Validates that:
          - The evaluacion exists in this tenant.
          - Each alumno_id belongs to this tenant (via UsuarioRepository).

        Alumnos that don't exist in this tenant are silently omitted (counted
        as 'omitidos').

        Parameters
        ----------
        evaluacion_id:
            The target evaluacion.
        body:
            List of alumno UUIDs to register.
        """
        # Verify evaluacion belongs to this tenant
        evaluacion = await self._eval_repo.get(evaluacion_id)
        if evaluacion is None:
            raise ValueError(f"Evaluacion {evaluacion_id} no encontrada")

        usuario_repo = UsuarioRepository(session=self._session, tenant_id=self._tenant_id)

        importados = 0
        omitidos = 0

        for item in body.alumnos:
            alumno = await usuario_repo.get(item.alumno_id)
            if alumno is None:
                omitidos += 1
                continue
            # alumno validated as belonging to this tenant
            importados += 1

        return ImportarPadronResponse(importados=importados, omitidos=omitidos)

    async def listar_con_metricas(self) -> list[EvaluacionConMetricas]:
        """List all active evaluaciones for this tenant, annotated with cupos_libres_hoy.

        cupos_libres_hoy is computed from the count of active reservas for today.
        """
        today = datetime.now(tz=timezone.utc).date()
        evaluaciones = await self._eval_repo.list()

        result: list[EvaluacionConMetricas] = []
        for ev in evaluaciones:
            count_today = await self._eval_repo.contar_reservas_activas_en_fecha(
                ev.id, today
            )
            libres = cupos_libres(ev.cupo_por_dia, count_today)
            result.append(
                EvaluacionConMetricas(
                    id=ev.id,
                    tenant_id=ev.tenant_id,
                    materia_id=ev.materia_id,
                    cohorte_id=ev.cohorte_id,
                    tipo=ev.tipo,
                    estado=ev.estado,
                    instancia=ev.instancia,
                    dias_disponibles=ev.dias_disponibles,
                    cupo_por_dia=ev.cupo_por_dia,
                    created_at=ev.created_at,
                    updated_at=ev.updated_at,
                    cupos_libres_hoy=libres,
                )
            )

        return result

    async def metricas_panel(self) -> MetricasPanel:
        """Return 4 aggregated counters for the coloquios dashboard panel."""
        metrics = await self._eval_repo.metricas_panel()
        return MetricasPanel(**metrics)

"""
app/services/reserva_service.py — ReservaService.

Business logic for reserva management:
  - reservar: create a new reservation (alumno_id from JWT, validate cupo)
  - cancelar: Activa → Cancelada (only own reservation, only if evaluacion Activa)
  - listar_agenda: list all reservas for an evaluacion

Business rules:
  RN-C03: alumno can only have one active reservation per evaluacion
  RN-C04: cupo_por_dia must not be exceeded for the chosen date
  RN-C05: only the alumno who made the reservation can cancel it
  RN-C06: can only cancel if the evaluacion is still Activa

Identity: alumno_id always from JWT (current_user), never from request body.
Tenant: always from self._tenant_id, never from request body.

Implemented: C-14 (evaluaciones-y-coloquios)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.models.reserva_evaluacion import ReservaEvaluacion
from app.repositories.evaluacion_repository import EvaluacionRepository
from app.repositories.reserva_evaluacion_repository import ReservaEvaluacionRepository
from app.schemas.coloquios import ReservaEvaluacionRead, ReservarRequest
from app.services.coloquio_helpers import hay_cupo


class ReservaService:
    """Service for reservation management.

    All operations scoped to *tenant_id* from JWT — never from request body.
    alumno_id is always taken from current_user (JWT), never from the request.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._reserva_repo = ReservaEvaluacionRepository(
            session=session, tenant_id=tenant_id
        )
        self._eval_repo = EvaluacionRepository(session=session, tenant_id=tenant_id)

    async def reservar(
        self,
        evaluacion_id: uuid.UUID,
        body: ReservarRequest,
        current_user: CurrentUser,
    ) -> ReservaEvaluacionRead:
        """Create a new reservation for *current_user.user_id* in *evaluacion_id*.

        Steps:
          1. Load evaluacion — must exist and be Activa.
          2. Count reservas activas for body.fecha_hora's date.
          3. Check cupo_por_dia — raise ValueError if full.
          4. Create reservation — IntegrityError from duplicate = ValueError.

        alumno_id comes exclusively from current_user (JWT).

        Raises
        ------
        ValueError
            If evaluacion not found, not Activa, cupo exceeded, or duplicate reservation.
        """
        evaluacion = await self._eval_repo.get(evaluacion_id)
        if evaluacion is None:
            raise ValueError(f"Evaluacion {evaluacion_id} no encontrada")
        if evaluacion.estado != "Activa":
            raise ValueError("Solo se puede reservar en evaluaciones con estado Activa")

        fecha = body.fecha_hora.date()
        count_dia = await self._eval_repo.contar_reservas_activas_en_fecha(
            evaluacion_id, fecha
        )

        if not hay_cupo(count_dia, evaluacion.cupo_por_dia):
            raise ValueError(
                f"Sin cupo disponible para el día {fecha}. "
                f"Cupo máximo: {evaluacion.cupo_por_dia}"
            )

        reserva = ReservaEvaluacion(
            tenant_id=self._tenant_id,
            evaluacion_id=evaluacion_id,
            alumno_id=current_user.user_id,  # identity from JWT ONLY
            fecha_hora=body.fecha_hora,
            estado="Activa",
        )
        created = await self._reserva_repo.create_reserva(reserva)
        if created is None:
            raise ValueError(
                "Ya tenés una reserva activa para esta evaluación. "
                "Cancelá la anterior antes de reservar nuevamente."
            )

        return ReservaEvaluacionRead.model_validate(created)

    async def cancelar(
        self,
        evaluacion_id: uuid.UUID,
        reserva_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> bool:
        """Cancel a reservation.

        Rules:
          - Only the alumno who made the reservation can cancel (own only).
          - Only if the parent evaluacion is still Activa.

        Parameters
        ----------
        evaluacion_id:
            Used to verify the evaluacion is Activa.
        reserva_id:
            ID of the reservation to cancel.
        current_user:
            The authenticated user (alumno). alumno_id == current_user.user_id.

        Returns
        -------
        bool
            True if cancelled successfully.

        Raises
        ------
        ValueError
            If evaluacion not Activa, reserva not found, or belongs to another alumno.
        """
        evaluacion = await self._eval_repo.get(evaluacion_id)
        if evaluacion is None:
            raise ValueError(f"Evaluacion {evaluacion_id} no encontrada")
        if evaluacion.estado != "Activa":
            raise ValueError("No se puede cancelar una reserva de una evaluación cerrada")

        reserva = await self._reserva_repo.get(reserva_id)
        if reserva is None:
            raise ValueError(f"Reserva {reserva_id} no encontrada")

        # Ownership check: only own reservation can be cancelled
        if reserva.alumno_id != current_user.user_id:
            raise ValueError("Solo podés cancelar tus propias reservas")

        if reserva.estado != "Activa":
            raise ValueError("La reserva ya fue cancelada")

        updated = await self._reserva_repo.cambiar_estado(reserva_id, "Cancelada")
        return updated

    async def listar_agenda(
        self, evaluacion_id: uuid.UUID
    ) -> list[ReservaEvaluacionRead]:
        """Return all reservas for the given evaluacion, scoped to this tenant.

        Parameters
        ----------
        evaluacion_id:
            The evaluacion to list reservas for.
        """
        reservas = await self._reserva_repo.list_by_evaluacion(evaluacion_id)
        return [ReservaEvaluacionRead.model_validate(r) for r in reservas]

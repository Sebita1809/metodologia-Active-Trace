"""
app/services/encuentro_service.py — EncuentroService (C-13).

Business logic for SlotEncuentro and InstanciaEncuentro.

Rules enforced:
  RN-13.1 — Recurrent mode: cant_semanas > 0 + dia_semana + fecha_inicio
             → N InstanciaEncuentro rows (Programado)
  RN-13.2 — Unique mode: fecha_unica + hora → 1 InstanciaEncuentro (slot_id=NULL)
  RN-13   — Modes are EXCLUSIVE: both set → DomainError; neither set → DomainError
  RN-14   — editar_instancia operates ONLY on instancia_encuentro (never touches slot)

Access control:
  - PROFESOR: can only act on their own asignacion (checked via asignacion.usuario_id)
  - COORDINADOR/ADMIN: can act on any asignacion within the tenant

Flow: EncuentroService → SlotEncuentroRepository / InstanciaEncuentroRepository → DB.
No direct DB access in this service.

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import uuid
from datetime import date, time

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instancia_encuentro import EstadoInstancia, InstanciaEncuentro
from app.models.slot_encuentro import SlotEncuentro
from app.repositories.instancia_encuentro_repository import InstanciaEncuentroRepository
from app.repositories.slot_encuentro_repository import SlotEncuentroRepository
from app.services.encuentro_helpers import (
    generar_fechas_recurrencia,
    render_encuentros_html,
)

# Roles that can operate across all asignaciones of the tenant
_ROLES_ADMIN = frozenset({"COORDINADOR", "ADMIN"})

# Maximum recurrence weeks (design decision D-Risk-1)
MAX_CANT_SEMANAS = 52


class DomainError(ValueError):
    """Raised when a business rule (RN-XX) is violated."""


class EncuentroService:
    """Orchestrates SlotEncuentro and InstanciaEncuentro operations.

    Constructor parameters:
        session   — open AsyncSession for the current request
        tenant_id — UUID of the requesting user's tenant
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._slot_repo = SlotEncuentroRepository(
            session=session, tenant_id=tenant_id
        )
        self._instancia_repo = InstanciaEncuentroRepository(
            session=session, tenant_id=tenant_id
        )

    # ------------------------------------------------------------------
    # Task 4.1 / 4.2 / 4.3 — crear_slot_recurrente (RN-13.1)
    # ------------------------------------------------------------------

    async def crear_slot_recurrente(
        self,
        *,
        asignacion_id: uuid.UUID,
        materia_id: uuid.UUID,
        titulo: str,
        dia_semana: str,
        fecha_inicio: date,
        cant_semanas: int,
        hora: time,
        meet_url: str | None = None,
        vig_desde: date | None = None,
        vig_hasta: date | None = None,
        current_user_id: uuid.UUID,
        current_user_roles: list[str],
        fecha_unica: date | None = None,
    ) -> tuple[SlotEncuentro, list[InstanciaEncuentro]]:
        """Create a recurring slot and generate N InstanciaEncuentro rows (RN-13.1).

        Raises DomainError if:
          - Both *cant_semanas* > 0 AND *fecha_unica* is set (modes exclusive, RN-13)
          - Neither mode is configured
          - *cant_semanas* > MAX_CANT_SEMANAS
          - PROFESOR tries to act on an asignacion they don't own
        """
        # RN-13: modes must be exclusive
        self._validar_modo_exclusivo(cant_semanas=cant_semanas, fecha_unica=fecha_unica)

        if cant_semanas < 1 or cant_semanas > MAX_CANT_SEMANAS:
            raise DomainError(
                f"cant_semanas debe estar entre 1 y {MAX_CANT_SEMANAS} "
                f"(recibido: {cant_semanas})"
            )

        slot = SlotEncuentro(
            tenant_id=self._tenant_id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            titulo=titulo,
            hora=hora,
            dia_semana=dia_semana,
            fecha_inicio=fecha_inicio,
            cant_semanas=cant_semanas,
            meet_url=meet_url,
            vig_desde=vig_desde,
            vig_hasta=vig_hasta,
        )
        slot = await self._slot_repo.create(slot)

        # Generate dates and create instancias in bulk
        fechas = generar_fechas_recurrencia(dia_semana, fecha_inicio, cant_semanas)
        instancias_obj = [
            InstanciaEncuentro(
                tenant_id=self._tenant_id,
                slot_id=slot.id,
                materia_id=materia_id,
                fecha=f,
                hora=hora,
                titulo=titulo,
                estado=EstadoInstancia.Programado,
                meet_url=meet_url,
            )
            for f in fechas
        ]
        instancias = await self._instancia_repo.bulk_create(instancias_obj)

        return slot, instancias

    # ------------------------------------------------------------------
    # Task 5.1 — crear_encuentro_unico (RN-13.2)
    # ------------------------------------------------------------------

    async def crear_encuentro_unico(
        self,
        *,
        materia_id: uuid.UUID,
        titulo: str,
        fecha_unica: date,
        hora: time,
        meet_url: str | None = None,
        current_user_id: uuid.UUID,
        current_user_roles: list[str],
        cant_semanas: int = 0,
    ) -> InstanciaEncuentro:
        """Create a single InstanciaEncuentro with slot_id=NULL (RN-13.2).

        Raises DomainError if:
          - *cant_semanas* > 0 AND *fecha_unica* is set simultaneously (RN-13)
          - *fecha_unica* is None
        """
        if fecha_unica is None:
            raise DomainError(
                "fecha_unica es obligatoria para crear un encuentro único (RN-13.2)"
            )

        # RN-13: check both not set together
        self._validar_modo_exclusivo(cant_semanas=cant_semanas, fecha_unica=fecha_unica)

        instancia = InstanciaEncuentro(
            tenant_id=self._tenant_id,
            slot_id=None,
            materia_id=materia_id,
            fecha=fecha_unica,
            hora=hora,
            titulo=titulo,
            estado=EstadoInstancia.Programado,
            meet_url=meet_url,
        )
        return await self._instancia_repo.create(instancia)

    # ------------------------------------------------------------------
    # Task 5.2 / 5.3 / 5.4 — editar_instancia (RN-14)
    # ------------------------------------------------------------------

    async def editar_instancia(
        self,
        instancia_id: uuid.UUID,
        *,
        estado: str | None = None,
        meet_url: str | None = None,
        video_url: str | None = None,
        comentario: str | None = None,
    ) -> InstanciaEncuentro:
        """Edit a single InstanciaEncuentro without touching the slot (RN-14).

        Only the fields present in the call are updated. The slot and all
        sibling instancias remain untouched — this is the RN-14 guarantee.

        Raises DomainError if the instancia does not exist in this tenant.
        """
        data: dict = {}
        if estado is not None:
            data["estado"] = estado
        if meet_url is not None:
            data["meet_url"] = meet_url
        if video_url is not None:
            data["video_url"] = video_url
        if comentario is not None:
            data["comentario"] = comentario

        updated = await self._instancia_repo.update(instancia_id, **data)
        if updated is None:
            raise DomainError(
                f"InstanciaEncuentro {instancia_id} no encontrada en este tenant"
            )
        return updated

    # ------------------------------------------------------------------
    # Task 6.1 — generar_html_asignacion
    # ------------------------------------------------------------------

    async def generar_html_asignacion(self, materia_id: uuid.UUID) -> str:
        """Return an HTML fragment with all active instancias for a materia.

        Uses render_encuentros_html (pure function, D5).
        """
        instancias = await self._instancia_repo.list_by_materia(materia_id)
        return render_encuentros_html(instancias)

    # ------------------------------------------------------------------
    # Task 6.2 — listar_admin_encuentros (transversal within tenant)
    # ------------------------------------------------------------------

    async def listar_admin_encuentros(self) -> list[InstanciaEncuentro]:
        """Return all active instancias for this tenant (admin / coordinator view).

        Scoped to self._tenant_id — never cross-tenant.
        """
        return await self._instancia_repo.list_all_tenant()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validar_modo_exclusivo(*, cant_semanas: int, fecha_unica: date | None) -> None:
        """Enforce RN-13: recurrent and unique modes are mutually exclusive."""
        recurrente = cant_semanas > 0
        unico = fecha_unica is not None

        if recurrente and unico:
            raise DomainError(
                "RN-13: cant_semanas > 0 y fecha_unica no pueden estar seteados "
                "simultáneamente. Los modos de creación son excluyentes."
            )
        if not recurrente and not unico:
            raise DomainError(
                "RN-13: debe especificarse un modo de creación: "
                "recurrente (cant_semanas > 0 + dia_semana + fecha_inicio) "
                "o único (fecha_unica)."
            )

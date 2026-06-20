"""
app/services/guardia_service.py — GuardiaService (C-13).

Business logic for Guardia (E11).

Rules enforced:
  - TUTOR registers guardias for their asignacion
  - creada_at is set server-side (never from request body)
  - tenant_id always from JWT / constructor (never from body)
  - Soft delete preserves audit trail

Access:
  - POST /guardias → TUTOR (registro)
  - GET  /guardias → COORDINADOR / ADMIN (consulta/export)

Flow: GuardiaService → GuardiaRepository → DB.
No direct DB access in this service.

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guardia import EstadoGuardia, Guardia
from app.repositories.guardia_repository import GuardiaRepository


class DomainError(ValueError):
    """Raised when a business rule is violated."""


class GuardiaService:
    """Orchestrates Guardia lifecycle.

    Constructor parameters:
        session   — open AsyncSession for the current request
        tenant_id — UUID of the requesting user's tenant
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._repo = GuardiaRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Task 7.1 / 7.2 — registrar
    # ------------------------------------------------------------------

    async def registrar(
        self,
        *,
        asignacion_id: uuid.UUID,
        materia_id: uuid.UUID,
        carrera_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        dia: str,
        horario: str,
        estado: str = EstadoGuardia.Pendiente,
        comentarios: str | None = None,
    ) -> Guardia:
        """Register a new Guardia.

        creada_at is set by the DB server_default (func.now()) — not from caller.
        tenant_id comes from the service constructor (JWT), never from the request body.

        Raises DomainError for invalid estado value.
        """
        # Validate estado if provided explicitly
        valid_estados = {e.value for e in EstadoGuardia}
        if estado not in valid_estados:
            raise DomainError(
                f"Estado inválido: {estado!r}. "
                f"Valores aceptados: {sorted(valid_estados)}"
            )

        guardia = Guardia(
            tenant_id=self._tenant_id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            dia=dia,
            horario=horario,
            estado=estado,
            comentarios=comentarios,
        )
        return await self._repo.create(guardia)

    # ------------------------------------------------------------------
    # Task 7.3 — listar
    # ------------------------------------------------------------------

    async def listar(
        self,
        *,
        asignacion_id: uuid.UUID | None = None,
    ) -> list[Guardia]:
        """Return active guardias for this tenant.

        Filters by *asignacion_id* if provided; returns all tenant guardias otherwise.
        Never crosses tenant boundary — scoped to self._tenant_id via repository.
        """
        if asignacion_id is not None:
            return await self._repo.list_by_asignacion(asignacion_id)
        return await self._repo.list()

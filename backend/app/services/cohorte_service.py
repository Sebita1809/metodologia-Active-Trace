"""
app/services/cohorte_service.py — CohorteService.

Business logic for the Cohorte catalog.

Rules enforced:
  - All operations scoped to tenant_id from the authenticated user.
  - Uniqueness on (tenant_id, carrera_id, nombre) → ValueError (409 in router).
  - Carrera must be Activa when creating or activating a Cohorte → HTTPException(422).
  - vig_hasta must be >= vig_desde → HTTPException(422).
  - Soft delete for audit trail.

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cohorte import Cohorte
from app.repositories.carrera_repository import CarreraRepository
from app.repositories.cohorte_repository import CohorteRepository


class CohorteService:
    """CRUD operations for the Cohorte catalog.

    All write methods are scoped to *tenant_id* — the identity comes from
    the JWT-verified CurrentUser, never from request body.
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._repo = CohorteRepository(session=session, tenant_id=tenant_id)
        self._carrera_repo = CarreraRepository(session=session, tenant_id=tenant_id)

    async def create(
        self,
        carrera_id: uuid.UUID,
        nombre: str,
        anio: int,
        vig_desde: date,
        vig_hasta: date | None = None,
        estado: str = "Activa",
    ) -> Cohorte:
        """Create a new Cohorte.

        Raises:
            HTTPException(422): carrera is inactive, or vig_hasta < vig_desde.
            ValueError: duplicate (tenant, carrera, nombre) → router returns 409.
        """
        # Validate carrera is active
        carrera = await self._carrera_repo.get(carrera_id)
        if carrera is None or carrera.estado != "Activa":
            raise HTTPException(
                status_code=422,
                detail="La carrera debe estar Activa para crear una cohorte",
            )

        # Validate date range
        if vig_hasta is not None and vig_hasta < vig_desde:
            raise HTTPException(
                status_code=422,
                detail="vig_hasta debe ser mayor o igual a vig_desde",
            )

        # Validate uniqueness
        existing = await self._repo.get_by_nombre_carrera(nombre, carrera_id)
        if existing:
            raise ValueError(
                f"Cohorte '{nombre}' ya existe para esta carrera en este tenant"
            )

        cohorte = Cohorte(
            tenant_id=self._tenant_id,
            carrera_id=carrera_id,
            nombre=nombre,
            anio=anio,
            vig_desde=vig_desde,
            vig_hasta=vig_hasta,
            estado=estado,
        )
        return await self._repo.create(cohorte)

    async def get(self, cohorte_id: uuid.UUID) -> Cohorte | None:
        """Return Cohorte by ID scoped to this tenant, or None if not found."""
        return await self._repo.get(cohorte_id)

    async def list(self, carrera_id: uuid.UUID | None = None) -> list[Cohorte]:
        """Return all non-deleted Cohortes in this tenant, optionally filtered by carrera."""
        if carrera_id is not None:
            return await self._repo.list_by_carrera(carrera_id)
        return await self._repo.list()

    async def update(
        self,
        cohorte_id: uuid.UUID,
        nombre: str | None = None,
        anio: int | None = None,
        vig_desde: date | None = None,
        vig_hasta: date | None = None,
        estado: str | None = None,
    ) -> Cohorte | None:
        """Update a Cohorte. Returns None if not found.

        Raises:
            HTTPException(422): activating cohorte when its carrera is inactive,
                                 or vig_hasta < vig_desde.
            ValueError: duplicate nombre for same carrera+tenant → 409 in router.
        """
        cohorte = await self._repo.get(cohorte_id)
        if cohorte is None:
            return None

        # If activating the cohorte, validate its carrera is still active
        new_estado = estado if estado is not None else cohorte.estado
        if new_estado == "Activa":
            carrera = await self._carrera_repo.get(cohorte.carrera_id)
            if carrera is None or carrera.estado != "Activa":
                raise HTTPException(
                    status_code=422,
                    detail="La carrera debe estar Activa para activar una cohorte",
                )

        # Validate date range using updated or existing values
        effective_desde = vig_desde if vig_desde is not None else cohorte.vig_desde
        effective_hasta = vig_hasta if vig_hasta is not None else cohorte.vig_hasta
        if effective_hasta is not None and effective_hasta < effective_desde:
            raise HTTPException(
                status_code=422,
                detail="vig_hasta debe ser mayor o igual a vig_desde",
            )

        # Validate uniqueness if nombre changes
        if nombre is not None and nombre != cohorte.nombre:
            existing = await self._repo.get_by_nombre_carrera(nombre, cohorte.carrera_id)
            if existing and existing.id != cohorte_id:
                raise ValueError(
                    f"Cohorte '{nombre}' ya existe para esta carrera en este tenant"
                )

        data: dict = {}
        if nombre is not None:
            data["nombre"] = nombre
        if anio is not None:
            data["anio"] = anio
        if vig_desde is not None:
            data["vig_desde"] = vig_desde
        if vig_hasta is not None:
            data["vig_hasta"] = vig_hasta
        if estado is not None:
            data["estado"] = estado

        return await self._repo.update(cohorte_id, **data)

    async def delete(self, cohorte_id: uuid.UUID) -> bool:
        """Soft-delete a Cohorte. Returns False if not found."""
        return await self._repo.soft_delete(cohorte_id)

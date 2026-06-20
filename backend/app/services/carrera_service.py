"""
app/services/carrera_service.py — CarreraService.

Business logic for the academic program (Carrera) catalog.

Rules enforced:
  - All operations scoped to tenant_id from the authenticated user (never from request body).
  - Soft delete for audit trail.
  - Uniqueness violations on (tenant_id, codigo) surfaced as ValueError
    (translated to 409 by the router).

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.carrera import Carrera
from app.repositories.carrera_repository import CarreraRepository


class CarreraService:
    """CRUD operations for the Carrera catalog.

    All write methods are scoped to *tenant_id* — the identity comes from
    the JWT-verified CurrentUser, never from request body.
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._repo = CarreraRepository(session=session, tenant_id=tenant_id)

    async def create(self, codigo: str, nombre: str, estado: str = "Activa") -> Carrera:
        """Create a new Carrera.

        Raises ValueError if a Carrera with the same codigo already exists in this tenant.
        """
        existing = await self._repo.get_by_codigo(codigo)
        if existing:
            raise ValueError(f"Carrera con código '{codigo}' ya existe en este tenant")
        carrera = Carrera(
            tenant_id=self._tenant_id,
            codigo=codigo,
            nombre=nombre,
            estado=estado,
        )
        return await self._repo.create(carrera)

    async def get(self, carrera_id: uuid.UUID) -> Carrera | None:
        """Return Carrera by ID scoped to this tenant, or None if not found."""
        return await self._repo.get(carrera_id)

    async def list(self) -> list[Carrera]:
        """Return all non-deleted Carreras in this tenant."""
        return await self._repo.list()

    async def update(
        self,
        carrera_id: uuid.UUID,
        codigo: str | None = None,
        nombre: str | None = None,
        estado: str | None = None,
    ) -> Carrera | None:
        """Update a Carrera. Returns None if not found.

        Raises ValueError if the new codigo conflicts with an existing one.
        """
        if codigo is not None:
            existing = await self._repo.get_by_codigo(codigo)
            if existing and existing.id != carrera_id:
                raise ValueError(f"Carrera con código '{codigo}' ya existe en este tenant")

        data: dict = {}
        if codigo is not None:
            data["codigo"] = codigo
        if nombre is not None:
            data["nombre"] = nombre
        if estado is not None:
            data["estado"] = estado

        return await self._repo.update(carrera_id, **data)

    async def delete(self, carrera_id: uuid.UUID) -> bool:
        """Soft-delete a Carrera. Returns False if not found."""
        return await self._repo.soft_delete(carrera_id)

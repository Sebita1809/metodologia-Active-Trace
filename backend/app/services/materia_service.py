"""
app/services/materia_service.py — MateriaService.

Business logic for the Materia catalog.

Rules enforced:
  - All operations scoped to tenant_id from the authenticated user.
  - Uniqueness violations on (tenant_id, codigo) surfaced as ValueError
    (translated to 409 by the router).
  - Soft delete for audit trail.

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.materia import Materia
from app.repositories.materia_repository import MateriaRepository


class MateriaService:
    """CRUD operations for the Materia catalog.

    All write methods are scoped to *tenant_id* — the identity comes from
    the JWT-verified CurrentUser, never from request body.
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._repo = MateriaRepository(session=session, tenant_id=tenant_id)

    async def create(self, codigo: str, nombre: str, estado: str = "Activa") -> Materia:
        """Create a new Materia.

        Raises ValueError if a Materia with the same codigo already exists in this tenant.
        """
        existing = await self._repo.get_by_codigo(codigo)
        if existing:
            raise ValueError(f"Materia con código '{codigo}' ya existe en este tenant")
        materia = Materia(
            tenant_id=self._tenant_id,
            codigo=codigo,
            nombre=nombre,
            estado=estado,
        )
        return await self._repo.create(materia)

    async def get(self, materia_id: uuid.UUID) -> Materia | None:
        """Return Materia by ID scoped to this tenant, or None if not found."""
        return await self._repo.get(materia_id)

    async def list(self) -> list[Materia]:
        """Return all non-deleted Materias in this tenant."""
        return await self._repo.list()

    async def update(
        self,
        materia_id: uuid.UUID,
        codigo: str | None = None,
        nombre: str | None = None,
        estado: str | None = None,
    ) -> Materia | None:
        """Update a Materia. Returns None if not found.

        Raises ValueError if the new codigo conflicts with an existing one.
        """
        if codigo is not None:
            existing = await self._repo.get_by_codigo(codigo)
            if existing and existing.id != materia_id:
                raise ValueError(f"Materia con código '{codigo}' ya existe en este tenant")

        data: dict = {}
        if codigo is not None:
            data["codigo"] = codigo
        if nombre is not None:
            data["nombre"] = nombre
        if estado is not None:
            data["estado"] = estado

        return await self._repo.update(materia_id, **data)

    async def delete(self, materia_id: uuid.UUID) -> bool:
        """Soft-delete a Materia. Returns False if not found."""
        return await self._repo.soft_delete(materia_id)

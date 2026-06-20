"""
app/services/programa_materia_service.py — ProgramaMateriaService (C-17).

Business logic for programme management (F5.3).

Rules enforced:
  - tenant_id always from service constructor (JWT), never from body (D5).
  - Validation: materia_id, carrera_id, cohorte_id must belong to session tenant (D6).
    A cross-tenant reference is treated as "not found" → raises 404.
  - Replace pattern (D1): if a vivo programme exists for the combo, soft-delete
    it first then create a new one (append-only, audit trail preserved).
  - All queries scoped to tenant via ProgramaMateriaRepository.

Governance: BAJO — academic catalogue CRUD; no PII, no money.

Implemented: C-17 (programas-y-fechas-academicas)
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.carrera import Carrera
from app.models.cohorte import Cohorte
from app.models.materia import Materia
from app.models.programa_materia import ProgramaMateria
from app.repositories.base import BaseRepository
from app.repositories.programa_materia_repository import ProgramaMateriaRepository
from app.schemas.programas import ProgramaCreate, ProgramaFiltros, ProgramaResponse


class ProgramaMateriaService:
    """Orchestrates programme lifecycle for a single tenant.

    All operations scoped to *tenant_id* from JWT — never from request body.
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._repo = ProgramaMateriaRepository(session=session, tenant_id=tenant_id)
        # Repos for tenant-scoped FK validation
        self._materia_repo: BaseRepository[Materia] = BaseRepository(
            model=Materia, session=session, tenant_id=tenant_id
        )
        self._carrera_repo: BaseRepository[Carrera] = BaseRepository(
            model=Carrera, session=session, tenant_id=tenant_id
        )
        self._cohorte_repo: BaseRepository[Cohorte] = BaseRepository(
            model=Cohorte, session=session, tenant_id=tenant_id
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_response(self, obj: ProgramaMateria) -> ProgramaResponse:
        """Build ProgramaResponse from ORM model."""
        return ProgramaResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            materia_id=obj.materia_id,
            carrera_id=obj.carrera_id,
            cohorte_id=obj.cohorte_id,
            titulo=obj.titulo,
            referencia_archivo=obj.referencia_archivo,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            deleted_at=obj.deleted_at,
        )

    async def _validar_referencias(
        self,
        materia_id: uuid.UUID,
        carrera_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> None:
        """Validate that materia, carrera and cohorte belong to this tenant.

        Cross-tenant references are treated as "not found" → 404.
        """
        if await self._materia_repo.get(materia_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"Materia {materia_id} no encontrada en este tenant.",
            )
        if await self._carrera_repo.get(carrera_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"Carrera {carrera_id} no encontrada en este tenant.",
            )
        if await self._cohorte_repo.get(cohorte_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"Cohorte {cohorte_id} no encontrada en este tenant.",
            )

    # ------------------------------------------------------------------
    # Task 5.2 — asociar_programa
    # ------------------------------------------------------------------

    async def asociar_programa(self, data: ProgramaCreate) -> ProgramaResponse:
        """Create or replace the programme for a materia × carrera × cohorte combo.

        Replace pattern (D1):
          1. Validate FK references belong to this tenant.
          2. If a vivo programme exists for the combo → soft-delete it.
          3. Create a new programme row.

        The old row is preserved (soft-deleted) for audit trail.
        """
        await self._validar_referencias(data.materia_id, data.carrera_id, data.cohorte_id)

        # Soft-delete any existing vivo programme for this combo
        existing = await self._repo.get_vivo_por_combo(
            materia_id=data.materia_id,
            carrera_id=data.carrera_id,
            cohorte_id=data.cohorte_id,
        )
        if existing is not None:
            await self._repo.soft_delete(existing.id)

        # Create the new programme
        programa = ProgramaMateria(
            tenant_id=self._tenant_id,
            materia_id=data.materia_id,
            carrera_id=data.carrera_id,
            cohorte_id=data.cohorte_id,
            titulo=data.titulo,
            referencia_archivo=data.referencia_archivo,
        )
        programa = await self._repo.create(programa)
        return self._to_response(programa)

    # ------------------------------------------------------------------
    # Task 5.3 — obtener_por_combo
    # ------------------------------------------------------------------

    async def obtener_por_combo(
        self,
        *,
        materia_id: uuid.UUID,
        carrera_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> ProgramaResponse:
        """Return the vivo programme for a combo, or raise 404."""
        programa = await self._repo.get_vivo_por_combo(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
        )
        if programa is None:
            raise HTTPException(
                status_code=404,
                detail="No existe un programa vivo para esta combinación.",
            )
        return self._to_response(programa)

    # ------------------------------------------------------------------
    # Task 5.3 — listar
    # ------------------------------------------------------------------

    async def listar(self, filtros: ProgramaFiltros) -> list[ProgramaResponse]:
        """Return all vivo programmes for this tenant with optional filters."""
        programas = await self._repo.listar(
            materia_id=filtros.materia_id,
            carrera_id=filtros.carrera_id,
            cohorte_id=filtros.cohorte_id,
        )
        return [self._to_response(p) for p in programas]

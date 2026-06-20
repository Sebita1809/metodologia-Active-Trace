"""
app/services/fecha_academica_service.py — FechaAcademicaService (C-17).

Business logic for academic dates management (F5.4).

Rules enforced:
  - tenant_id always from service constructor (JWT), never from body (D5).
  - Validation: materia_id and cohorte_id must belong to session tenant (D6).
    A cross-tenant reference is treated as "not found" → raises 404.
  - Combo uniqueness: (materia_id, cohorte_id, tipo, numero) must be unique
    among vivo rows → raises 409 on duplicate.
  - Partial update: only fecha, titulo and periodo can be changed.
  - Soft-delete: never hard delete (D7).
  - Fragmento LMS (F5.4): assembles formatted HTML string — no LMS API call (D3).

Governance: BAJO — academic catalogue CRUD; no PII, no money.

Implemented: C-17 (programas-y-fechas-academicas)
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cohorte import Cohorte
from app.models.fecha_academica import FechaAcademica
from app.models.materia import Materia
from app.repositories.base import BaseRepository
from app.repositories.fecha_academica_repository import FechaAcademicaRepository
from app.schemas.fechas_academicas import (
    FechaAcademicaCreate,
    FechaAcademicaResponse,
    FechaAcademicaUpdate,
    FragmentoLmsResponse,
)


class FechaAcademicaService:
    """Orchestrates academic-date lifecycle for a single tenant.

    All operations scoped to *tenant_id* from JWT — never from request body.
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._repo = FechaAcademicaRepository(session=session, tenant_id=tenant_id)
        # Repos for tenant-scoped FK validation
        self._materia_repo: BaseRepository[Materia] = BaseRepository(
            model=Materia, session=session, tenant_id=tenant_id
        )
        self._cohorte_repo: BaseRepository[Cohorte] = BaseRepository(
            model=Cohorte, session=session, tenant_id=tenant_id
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_response(self, obj: FechaAcademica) -> FechaAcademicaResponse:
        """Build FechaAcademicaResponse from ORM model."""
        return FechaAcademicaResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            materia_id=obj.materia_id,
            cohorte_id=obj.cohorte_id,
            tipo=obj.tipo,
            numero=obj.numero,
            periodo=obj.periodo,
            fecha=obj.fecha,
            titulo=obj.titulo,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            deleted_at=obj.deleted_at,
        )

    async def _get_fecha_or_404(self, fecha_id: uuid.UUID) -> FechaAcademica:
        """Return the fecha or raise 404 if not found in this tenant."""
        fecha = await self._repo.get_by_id(fecha_id)
        if fecha is None:
            raise HTTPException(status_code=404, detail="Fecha académica no encontrada.")
        return fecha

    async def _validar_referencias(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> None:
        """Validate that materia and cohorte belong to this tenant.

        Cross-tenant references are treated as "not found" → 404.
        """
        if await self._materia_repo.get(materia_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"Materia {materia_id} no encontrada en este tenant.",
            )
        if await self._cohorte_repo.get(cohorte_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"Cohorte {cohorte_id} no encontrada en este tenant.",
            )

    # ------------------------------------------------------------------
    # Task 5.5 — crear_fecha
    # ------------------------------------------------------------------

    async def crear_fecha(self, data: FechaAcademicaCreate) -> FechaAcademicaResponse:
        """Create a new academic date.

        Validates:
          1. materia and cohorte belong to this tenant.
          2. Combo (materia_id, cohorte_id, tipo, numero) does not already exist.
        """
        await self._validar_referencias(data.materia_id, data.cohorte_id)

        combo_existe = await self._repo.existe_combo(
            materia_id=data.materia_id,
            cohorte_id=data.cohorte_id,
            tipo=data.tipo.value,
            numero=data.numero,
        )
        if combo_existe:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Ya existe una fecha académica viva con tipo={data.tipo.value!r}, "
                    f"numero={data.numero} para esta materia y cohorte."
                ),
            )

        fecha = FechaAcademica(
            tenant_id=self._tenant_id,
            materia_id=data.materia_id,
            cohorte_id=data.cohorte_id,
            tipo=data.tipo.value,
            numero=data.numero,
            periodo=data.periodo,
            fecha=data.fecha,
            titulo=data.titulo,
        )
        fecha = await self._repo.create(fecha)
        return self._to_response(fecha)

    # ------------------------------------------------------------------
    # Task 5.6 — actualizar_fecha
    # ------------------------------------------------------------------

    async def actualizar_fecha(
        self,
        fecha_id: uuid.UUID,
        data: FechaAcademicaUpdate,
    ) -> FechaAcademicaResponse:
        """Partial update of fecha, titulo and periodo.

        Only provided (non-None) fields are updated.
        Raises 404 if not found in this tenant.
        """
        await self._get_fecha_or_404(fecha_id)

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            # Nothing to update — return current state
            fecha = await self._get_fecha_or_404(fecha_id)
            return self._to_response(fecha)

        updated = await self._repo.update(fecha_id, **update_data)
        if updated is None:
            raise HTTPException(status_code=404, detail="Fecha académica no encontrada.")
        return self._to_response(updated)

    # ------------------------------------------------------------------
    # Task 5.6 — eliminar_fecha
    # ------------------------------------------------------------------

    async def eliminar_fecha(self, fecha_id: uuid.UUID) -> None:
        """Soft-delete a fecha académica.

        Raises 404 if not found in this tenant.
        """
        await self._get_fecha_or_404(fecha_id)
        deleted = await self._repo.soft_delete(fecha_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Fecha académica no encontrada.")

    # ------------------------------------------------------------------
    # Task 5.7 — listar_por_materia_cohorte
    # ------------------------------------------------------------------

    async def listar_por_materia_cohorte(
        self,
        *,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> list[FechaAcademicaResponse]:
        """Return all vivo fechas for materia × cohorte, ordered by fecha asc."""
        fechas = await self._repo.listar_por_materia_cohorte(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
        )
        return [self._to_response(f) for f in fechas]

    # ------------------------------------------------------------------
    # Task 5.8 — generar_fragmento_lms
    # ------------------------------------------------------------------

    async def generar_fragmento_lms(
        self,
        *,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> FragmentoLmsResponse:
        """Generate a formatted HTML fragment ready to paste in the LMS.

        Fetches vivo fechas ordered by fecha asc and assembles an HTML list.
        NO call to any external LMS API is made here (D3).

        If no fechas exist, returns an empty content string (not an error).
        """
        fechas = await self._repo.listar_por_materia_cohorte(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
        )

        if not fechas:
            contenido = ""
        else:
            items = []
            for f in fechas:
                fecha_str = f.fecha.strftime("%d/%m/%Y") if hasattr(f.fecha, "strftime") else str(f.fecha)
                items.append(
                    f"<li><strong>{f.tipo} {f.numero}</strong> — {f.titulo} — {fecha_str}</li>"
                )
            contenido = "<ul>\n" + "\n".join(items) + "\n</ul>"

        return FragmentoLmsResponse(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            formato="html",
            contenido=contenido,
        )

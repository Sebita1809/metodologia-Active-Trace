"""
app/services/asignacion_service.py — AsignacionService.

Business logic for role assignments with temporal validity.

Rules enforced:
  - estado_vigencia is DERIVED — never persisted; computed at read time.
  - Vigente: desde <= today AND (hasta is None OR today <= hasta)
  - Vencida: hasta < today
  - rol must be one of the valid business role values.
  - Tenant identity from constructor (JWT-sourced), never from request.
  - Soft delete for audit trail.

Implemented: C-07 (usuarios-y-asignaciones)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Literal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asignacion import Asignacion
from app.repositories.asignacion_repository import AsignacionRepository
from app.schemas.asignacion import ROL_NEGOCIO_VALUES


def _compute_estado_vigencia(
    desde: date,
    hasta: date | None,
    hoy: date,
) -> Literal["Vigente", "Vencida"]:
    """Compute the derived vigencia status.

    Vigente: desde <= hoy AND (hasta is None OR hoy <= hasta)
    Vencida: hasta is not None AND hasta < hoy
    """
    if hasta is not None and hasta < hoy:
        return "Vencida"
    return "Vigente"


@dataclass
class AsignacionConVigencia:
    """Transient DTO carrying an Asignacion with its derived estado_vigencia."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID
    rol: str
    materia_id: uuid.UUID | None
    carrera_id: uuid.UUID | None
    cohorte_id: uuid.UUID | None
    comisiones: list
    responsable_id: uuid.UUID | None
    desde: date
    hasta: date | None
    estado_vigencia: Literal["Vigente", "Vencida"]
    created_at: object
    updated_at: object


class AsignacionService:
    """CRUD operations for Asignaciones.

    All operations scoped to *tenant_id* from JWT — never from request body.
    Computes estado_vigencia at read time.
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._repo = AsignacionRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_dto(self, asignacion: Asignacion) -> AsignacionConVigencia:
        """Build AsignacionConVigencia with derived estado_vigencia."""
        hoy = date.today()
        return AsignacionConVigencia(
            id=asignacion.id,
            tenant_id=asignacion.tenant_id,
            usuario_id=asignacion.usuario_id,
            rol=asignacion.rol,
            materia_id=asignacion.materia_id,
            carrera_id=asignacion.carrera_id,
            cohorte_id=asignacion.cohorte_id,
            comisiones=asignacion.comisiones if asignacion.comisiones is not None else [],
            responsable_id=asignacion.responsable_id,
            desde=asignacion.desde,
            hasta=asignacion.hasta,
            estado_vigencia=_compute_estado_vigencia(asignacion.desde, asignacion.hasta, hoy),
            created_at=asignacion.created_at,
            updated_at=asignacion.updated_at,
        )

    def _validate_rol(self, rol: str) -> None:
        """Raise HTTPException(422) if rol is not a valid business role."""
        if rol not in ROL_NEGOCIO_VALUES:
            raise HTTPException(
                status_code=422,
                detail=f"Rol inválido: '{rol}'. Valores permitidos: {', '.join(ROL_NEGOCIO_VALUES)}",
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        usuario_id: uuid.UUID,
        rol: str,
        desde: date,
        hasta: date | None = None,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        comisiones: list[str] | None = None,
        responsable_id: uuid.UUID | None = None,
    ) -> AsignacionConVigencia:
        """Create a new Asignacion.

        Raises HTTPException(422) if rol is not a valid business role value.
        """
        self._validate_rol(rol)

        asignacion = Asignacion(
            tenant_id=self._tenant_id,
            usuario_id=usuario_id,
            rol=rol,
            desde=desde,
            hasta=hasta,
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            comisiones=comisiones if comisiones is not None else [],
            responsable_id=responsable_id,
        )
        persisted = await self._repo.create(asignacion)
        return self._to_dto(persisted)

    async def get(self, asignacion_id: uuid.UUID) -> AsignacionConVigencia | None:
        """Return Asignacion by ID (with vigencia), or None if not found."""
        asignacion = await self._repo.get(asignacion_id)
        if asignacion is None:
            return None
        return self._to_dto(asignacion)

    async def list_with_filters(
        self,
        *,
        usuario_id: uuid.UUID | None = None,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        rol: str | None = None,
        responsable_id: uuid.UUID | None = None,
    ) -> list[AsignacionConVigencia]:
        """Return filtered Asignaciones with derived vigencia."""
        asignaciones = await self._repo.list_with_filters(
            usuario_id=usuario_id,
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            rol=rol,
            responsable_id=responsable_id,
        )
        return [self._to_dto(a) for a in asignaciones]

    async def update(
        self,
        asignacion_id: uuid.UUID,
        *,
        rol: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        comisiones: list[str] | None = None,
        responsable_id: uuid.UUID | None = None,
    ) -> AsignacionConVigencia | None:
        """Update an Asignacion. Returns None if not found.

        Raises HTTPException(422) if the new rol is not a valid business role.
        """
        if rol is not None:
            self._validate_rol(rol)

        data: dict = {}
        if rol is not None:
            data["rol"] = rol
        if desde is not None:
            data["desde"] = desde
        if hasta is not None:
            data["hasta"] = hasta
        if materia_id is not None:
            data["materia_id"] = materia_id
        if carrera_id is not None:
            data["carrera_id"] = carrera_id
        if cohorte_id is not None:
            data["cohorte_id"] = cohorte_id
        if comisiones is not None:
            data["comisiones"] = comisiones
        if responsable_id is not None:
            data["responsable_id"] = responsable_id

        updated = await self._repo.update(asignacion_id, **data)
        if updated is None:
            return None
        return self._to_dto(updated)

    async def delete(self, asignacion_id: uuid.UUID) -> bool:
        """Soft-delete an Asignacion. Returns False if not found."""
        return await self._repo.soft_delete(asignacion_id)

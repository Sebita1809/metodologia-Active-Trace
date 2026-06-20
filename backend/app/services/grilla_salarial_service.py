"""
app/services/grilla_salarial_service.py — GrillaSalarialService (C-18).

Manages ABM (create / update / delete) for SalarioBase and SalarioPlus.
Enforces non-overlap of vigency ranges per (rol) and per (clave, rol) respectively (RN-31).

Raises ValueError when a vigency overlap is detected → caller maps to HTTP 409.

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.salario_base import SalarioBase
from app.models.salario_plus import SalarioPlus
from app.repositories.salario_base_repository import SalarioBaseRepository
from app.repositories.salario_plus_repository import SalarioPlusRepository
from app.schemas.salario_base import SalarioBaseCreate, SalarioBaseResponse, SalarioBaseUpdate
from app.schemas.salario_plus import SalarioPlusCreate, SalarioPlusResponse, SalarioPlusUpdate


class GrillaSalarialService:
    """ABM for salary grid (Base and Plus) with vigency non-overlap validation."""

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._base_repo = SalarioBaseRepository(session=session, tenant_id=tenant_id)
        self._plus_repo = SalarioPlusRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # SalarioBase ABM
    # ------------------------------------------------------------------

    def _to_base_response(self, row: SalarioBase) -> SalarioBaseResponse:
        return SalarioBaseResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            rol=row.rol,
            monto=row.monto,
            desde=row.desde,
            hasta=row.hasta,
            created_at=row.created_at,
            updated_at=row.updated_at,
            deleted_at=row.deleted_at,
        )

    async def crear_base(self, data: SalarioBaseCreate) -> SalarioBaseResponse:
        """Create a SalarioBase row. Raises ValueError on vigency overlap."""
        solapado = await self._base_repo.existe_solapamiento(
            data.rol, data.desde, data.hasta
        )
        if solapado:
            raise ValueError(
                f"Ya existe una vigencia solapada para rol '{data.rol}' "
                f"en el rango {data.desde} – {data.hasta or '∞'}. (RN-31)"
            )
        row = SalarioBase(
            tenant_id=self._tenant_id,
            rol=data.rol,
            monto=data.monto,
            desde=data.desde,
            hasta=data.hasta,
        )
        created = await self._base_repo.create(row)
        return self._to_base_response(created)

    async def listar_bases(self) -> list[SalarioBaseResponse]:
        """Return all active SalarioBase rows for this tenant."""
        rows = await self._base_repo.listar()
        return [self._to_base_response(r) for r in rows]

    async def actualizar_base(
        self, base_id: uuid.UUID, data: SalarioBaseUpdate
    ) -> SalarioBaseResponse:
        """Update a SalarioBase row. Raises ValueError on vigency overlap, 404 if not found."""
        row = await self._base_repo.get(base_id)
        if row is None:
            raise HTTPException(status_code=404, detail="SalarioBase no encontrado.")

        nuevo_rol = data.rol if data.rol is not None else row.rol
        nuevo_desde = data.desde if data.desde is not None else row.desde
        nuevo_hasta = data.hasta if data.hasta is not None else row.hasta

        solapado = await self._base_repo.existe_solapamiento(
            nuevo_rol, nuevo_desde, nuevo_hasta, excluir_id=base_id
        )
        if solapado:
            raise ValueError(
                f"Ya existe una vigencia solapada para rol '{nuevo_rol}' "
                f"en el rango {nuevo_desde} – {nuevo_hasta or '∞'}. (RN-31)"
            )

        kwargs: dict = {}
        if data.rol is not None:
            kwargs["rol"] = data.rol
        if data.monto is not None:
            kwargs["monto"] = data.monto
        if data.desde is not None:
            kwargs["desde"] = data.desde
        if data.hasta is not None:
            kwargs["hasta"] = data.hasta

        updated = await self._base_repo.update(base_id, **kwargs)
        if updated is None:
            raise HTTPException(status_code=404, detail="SalarioBase no encontrado.")
        return self._to_base_response(updated)

    async def eliminar_base(self, base_id: uuid.UUID) -> bool:
        """Soft-delete a SalarioBase row. Returns True if deleted, False if not found."""
        return await self._base_repo.soft_delete(base_id)

    # ------------------------------------------------------------------
    # SalarioPlus ABM
    # ------------------------------------------------------------------

    def _to_plus_response(self, row: SalarioPlus) -> SalarioPlusResponse:
        return SalarioPlusResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            clave=row.clave,
            rol=row.rol,
            descripcion=row.descripcion,
            monto=row.monto,
            desde=row.desde,
            hasta=row.hasta,
            created_at=row.created_at,
            updated_at=row.updated_at,
            deleted_at=row.deleted_at,
        )

    async def crear_plus(self, data: SalarioPlusCreate) -> SalarioPlusResponse:
        """Create a SalarioPlus row. Raises ValueError on vigency overlap."""
        solapado = await self._plus_repo.existe_solapamiento(
            data.clave, data.rol, data.desde, data.hasta
        )
        if solapado:
            raise ValueError(
                f"Ya existe una vigencia solapada para clave '{data.clave}' / rol '{data.rol}' "
                f"en el rango {data.desde} – {data.hasta or '∞'}. (RN-31)"
            )
        row = SalarioPlus(
            tenant_id=self._tenant_id,
            clave=data.clave,
            rol=data.rol,
            descripcion=data.descripcion,
            monto=data.monto,
            desde=data.desde,
            hasta=data.hasta,
        )
        created = await self._plus_repo.create(row)
        return self._to_plus_response(created)

    async def listar_plus(self) -> list[SalarioPlusResponse]:
        """Return all active SalarioPlus rows for this tenant."""
        rows = await self._plus_repo.listar()
        return [self._to_plus_response(r) for r in rows]

    async def actualizar_plus(
        self, plus_id: uuid.UUID, data: SalarioPlusUpdate
    ) -> SalarioPlusResponse:
        """Update a SalarioPlus row. Raises ValueError on vigency overlap, 404 if not found."""
        row = await self._plus_repo.get(plus_id)
        if row is None:
            raise HTTPException(status_code=404, detail="SalarioPlus no encontrado.")

        nueva_clave = data.clave if data.clave is not None else row.clave
        nuevo_rol = data.rol if data.rol is not None else row.rol
        nuevo_desde = data.desde if data.desde is not None else row.desde
        nuevo_hasta = data.hasta if data.hasta is not None else row.hasta

        solapado = await self._plus_repo.existe_solapamiento(
            nueva_clave, nuevo_rol, nuevo_desde, nuevo_hasta, excluir_id=plus_id
        )
        if solapado:
            raise ValueError(
                f"Ya existe una vigencia solapada para clave '{nueva_clave}' / rol '{nuevo_rol}' "
                f"en el rango {nuevo_desde} – {nuevo_hasta or '∞'}. (RN-31)"
            )

        kwargs: dict = {}
        if data.clave is not None:
            kwargs["clave"] = data.clave
        if data.rol is not None:
            kwargs["rol"] = data.rol
        if data.descripcion is not None:
            kwargs["descripcion"] = data.descripcion
        if data.monto is not None:
            kwargs["monto"] = data.monto
        if data.desde is not None:
            kwargs["desde"] = data.desde
        if data.hasta is not None:
            kwargs["hasta"] = data.hasta

        updated = await self._plus_repo.update(plus_id, **kwargs)
        if updated is None:
            raise HTTPException(status_code=404, detail="SalarioPlus no encontrado.")
        return self._to_plus_response(updated)

    async def eliminar_plus(self, plus_id: uuid.UUID) -> bool:
        """Soft-delete a SalarioPlus row. Returns True if deleted, False if not found."""
        return await self._plus_repo.soft_delete(plus_id)

"""
app/services/factura_service.py — FacturaService (C-18).

ABM for Factura with estado transition: Pendiente → Abonada (sets abonada_at, RN-39).
tenant_id ALWAYS from constructor (JWT), never from request body.

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.factura import EstadoFactura, Factura
from app.repositories.factura_repository import FacturaRepository
from app.schemas.factura import (
    CambiarEstadoRequest,
    FacturaCreate,
    FacturaRead,
    FacturaUpdate,
)


def _to_factura_read(row: Factura) -> FacturaRead:
    return FacturaRead(
        id=row.id,
        tenant_id=row.tenant_id,
        usuario_id=row.usuario_id,
        periodo_mes=row.periodo_mes,
        periodo_anio=row.periodo_anio,
        detalle=row.detalle,
        referencia_archivo=row.referencia_archivo,
        tamano_kb=row.tamano_kb,
        monto=row.monto,
        estado=row.estado,
        abonada_at=row.abonada_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


class FacturaService:
    """ABM and estado transitions for Factura (docentes facturantes)."""

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._repo = FacturaRepository(session=session, tenant_id=tenant_id)

    async def crear_factura(self, data: FacturaCreate) -> FacturaRead:
        """Create a Factura. Initial estado = Pendiente."""
        row = Factura(
            tenant_id=self._tenant_id,
            usuario_id=data.usuario_id,
            periodo_mes=data.periodo_mes,
            periodo_anio=data.periodo_anio,
            detalle=data.detalle,
            referencia_archivo=data.referencia_archivo,
            tamano_kb=data.tamano_kb,
            monto=data.monto,
            estado=EstadoFactura.Pendiente,
        )
        created = await self._repo.create(row)
        return _to_factura_read(created)

    async def listar_facturas(
        self,
        *,
        usuario_id: uuid.UUID | None = None,
        estado: str | None = None,
        periodo_mes: int | None = None,
        periodo_anio: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FacturaRead]:
        """Return facturas with optional filters."""
        rows = await self._repo.listar(
            usuario_id=usuario_id,
            estado=estado,
            periodo_mes=periodo_mes,
            periodo_anio=periodo_anio,
            limit=limit,
            offset=offset,
        )
        return [_to_factura_read(r) for r in rows]

    async def get_factura(self, factura_id: uuid.UUID) -> FacturaRead:
        """Return a single factura by id. Raises 404 if not found."""
        row = await self._repo.get_by_id(factura_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Factura no encontrada.")
        return _to_factura_read(row)

    async def actualizar_factura(
        self, factura_id: uuid.UUID, data: FacturaUpdate
    ) -> FacturaRead:
        """Update factura fields (non-estado). Raises 404 if not found."""
        row = await self._repo.get_by_id(factura_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Factura no encontrada.")

        kwargs: dict = {}
        if data.detalle is not None:
            kwargs["detalle"] = data.detalle
        if data.referencia_archivo is not None:
            kwargs["referencia_archivo"] = data.referencia_archivo
        if data.tamano_kb is not None:
            kwargs["tamano_kb"] = data.tamano_kb
        if data.monto is not None:
            kwargs["monto"] = data.monto

        updated = await self._repo.update(factura_id, **kwargs)
        if updated is None:
            raise HTTPException(status_code=404, detail="Factura no encontrada.")
        return _to_factura_read(updated)

    async def eliminar_factura(self, factura_id: uuid.UUID) -> bool:
        """Soft-delete a factura. Returns True if deleted."""
        deleted = await self._repo.soft_delete(factura_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Factura no encontrada.")
        return True

    async def cambiar_estado(
        self, factura_id: uuid.UUID, req: CambiarEstadoRequest
    ) -> FacturaRead:
        """Transition factura estado: Pendiente → Abonada (sets abonada_at, RN-39).

        Only valid transition is Pendiente → Abonada.
        Any other transition raises 422.
        """
        row = await self._repo.get_by_id(factura_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Factura no encontrada.")

        estado_actual = EstadoFactura(row.estado)
        nuevo_estado = req.nuevo_estado

        # Validate transition
        if estado_actual == EstadoFactura.Abonada and nuevo_estado == EstadoFactura.Pendiente:
            raise HTTPException(
                status_code=422,
                detail="No se puede revertir una factura ya Abonada a Pendiente.",
            )
        if estado_actual == nuevo_estado:
            # Idempotent: same state transition is a no-op, return current
            return _to_factura_read(row)

        kwargs: dict = {"estado": nuevo_estado.value}
        if nuevo_estado == EstadoFactura.Abonada:
            kwargs["abonada_at"] = datetime.now(tz=timezone.utc)

        updated = await self._repo.update(factura_id, **kwargs)
        if updated is None:
            raise HTTPException(status_code=404, detail="Factura no encontrada.")
        return _to_factura_read(updated)

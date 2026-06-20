"""
app/schemas/factura.py — Pydantic schemas for Factura (C-18).

Schemas:
  FacturaCreate         — create a new factura
  FacturaUpdate         — update factura fields (partial)
  FacturaRead           — read DTO
  CambiarEstadoRequest  — transition Pendiente → Abonada

All schemas use extra='forbid' (project rule).

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.factura import EstadoFactura


class FacturaCreate(BaseModel):
    """Request body for creating a Factura."""

    model_config = ConfigDict(extra="forbid")

    usuario_id: uuid.UUID
    periodo_mes: int
    periodo_anio: int
    detalle: str
    referencia_archivo: str | None = None
    tamano_kb: Decimal | None = None
    monto: Decimal

    @field_validator("monto")
    @classmethod
    def monto_no_negativo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("El monto no puede ser negativo.")
        return v

    @field_validator("periodo_mes")
    @classmethod
    def mes_valido(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("periodo_mes debe estar entre 1 y 12.")
        return v

    @field_validator("periodo_anio")
    @classmethod
    def anio_valido(cls, v: int) -> int:
        if v < 2000:
            raise ValueError("periodo_anio debe ser >= 2000.")
        return v


class FacturaUpdate(BaseModel):
    """Request body for partial update of a Factura (non-estado fields)."""

    model_config = ConfigDict(extra="forbid")

    detalle: str | None = None
    referencia_archivo: str | None = None
    tamano_kb: Decimal | None = None
    monto: Decimal | None = None

    @field_validator("monto")
    @classmethod
    def monto_no_negativo(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("El monto no puede ser negativo.")
        return v


class FacturaRead(BaseModel):
    """Read DTO for Factura."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID
    periodo_mes: int
    periodo_anio: int
    detalle: str
    referencia_archivo: str | None
    tamano_kb: Decimal | None
    monto: Decimal
    estado: str
    abonada_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CambiarEstadoRequest(BaseModel):
    """Request body for PATCH /facturas/{id}/estado."""

    model_config = ConfigDict(extra="forbid")

    nuevo_estado: EstadoFactura

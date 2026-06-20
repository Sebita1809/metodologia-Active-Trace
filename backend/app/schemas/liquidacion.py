"""
app/schemas/liquidacion.py — Pydantic schemas for Liquidacion (C-18).

Schemas:
  CalcularRequest  — trigger calculation for a period
  CerrarRequest    — close a period (immutable)
  LiquidacionRead  — full read DTO including desglose
  PeriodoView      — segmented view with KPIs (F10.6, RN-36/38)

All schemas use extra='forbid' (project rule).

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class CalcularRequest(BaseModel):
    """Request body for POST /liquidaciones/calcular."""

    model_config = ConfigDict(extra="forbid")

    cohorte_id: uuid.UUID
    mes: int
    anio: int

    @field_validator("mes")
    @classmethod
    def mes_valido(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("mes debe estar entre 1 y 12.")
        return v

    @field_validator("anio")
    @classmethod
    def anio_valido(cls, v: int) -> int:
        if v < 2000:
            raise ValueError("anio debe ser >= 2000.")
        return v


class CerrarRequest(BaseModel):
    """Request body for POST /liquidaciones/cerrar."""

    model_config = ConfigDict(extra="forbid")

    cohorte_id: uuid.UUID
    mes: int
    anio: int

    @field_validator("mes")
    @classmethod
    def mes_valido(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("mes debe estar entre 1 y 12.")
        return v

    @field_validator("anio")
    @classmethod
    def anio_valido(cls, v: int) -> int:
        if v < 2000:
            raise ValueError("anio debe ser >= 2000.")
        return v


class LiquidacionRead(BaseModel):
    """Full read DTO for a single Liquidacion row."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID
    cohorte_id: uuid.UUID
    periodo_mes: int
    periodo_anio: int
    rol: str
    comisiones: list[Any]
    base_monto: Decimal
    plus_monto: Decimal
    total_monto: Decimal
    desglose: dict[str, Any] | None
    es_nexo: bool
    excluido_por_factura: bool
    estado: str
    cerrada_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class PeriodoSegmento(BaseModel):
    """One segment (general / nexo / facturantes) of the PeriodoView."""

    model_config = ConfigDict(extra="forbid")

    liquidaciones: list[LiquidacionRead]
    total: Decimal


class PeriodoView(BaseModel):
    """Segmented view of a liquidation period with KPIs (F10.6, RN-36/38).

    Segments:
      general    — PROFESOR / TUTOR / COORDINADOR (non-facturante, non-NEXO)
      nexo       — NEXO role (shown separately, included in total_sin_factura)
      facturantes — excluido_por_factura=True (informative only)

    KPIs:
      total_sin_factura — general.total + nexo.total
      total_con_factura — sum of active facturas for the same period
    """

    model_config = ConfigDict(extra="forbid")

    cohorte_id: uuid.UUID
    mes: int
    anio: int
    general: PeriodoSegmento
    nexo: PeriodoSegmento
    facturantes: PeriodoSegmento
    total_sin_factura: Decimal
    total_con_factura: Decimal

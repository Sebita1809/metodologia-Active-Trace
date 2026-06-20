"""
app/schemas/salario_plus.py — Pydantic schemas for SalarioPlus (C-18).

All schemas use extra='forbid' (project rule).

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class SalarioPlusCreate(BaseModel):
    """Request body for creating a SalarioPlus row."""

    model_config = ConfigDict(extra="forbid")

    clave: str
    rol: str
    descripcion: str | None = None
    monto: Decimal
    desde: date
    hasta: date | None = None

    @field_validator("monto")
    @classmethod
    def monto_no_negativo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("El monto no puede ser negativo.")
        return v


class SalarioPlusUpdate(BaseModel):
    """Request body for updating a SalarioPlus row (all fields optional)."""

    model_config = ConfigDict(extra="forbid")

    clave: str | None = None
    rol: str | None = None
    descripcion: str | None = None
    monto: Decimal | None = None
    desde: date | None = None
    hasta: date | None = None

    @field_validator("monto")
    @classmethod
    def monto_no_negativo(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("El monto no puede ser negativo.")
        return v


class SalarioPlusResponse(BaseModel):
    """Response DTO for SalarioPlus."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    clave: str
    rol: str
    descripcion: str | None
    monto: Decimal
    desde: date
    hasta: date | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

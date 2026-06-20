"""
app/models/liquidacion.py — Liquidacion domain entity (C-18).

Represents one docente's salary liquidation for a (cohorte, periodo_mes, periodo_anio).
Unique constraint: (tenant_id, usuario_id, cohorte_id, periodo_anio, periodo_mes)
WHERE deleted_at IS NULL — enforced by partial index in migration 016.

EstadoLiquidacion: Abierta (default) → Cerrada (immutable once closed, RN-22).

Governance: CRÍTICO — touches money, closure is irreversible.

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel

from sqlalchemy import ForeignKey


class EstadoLiquidacion(StrEnum):
    """Valid states for a Liquidacion.

    StrEnum → VARCHAR storage, no PG ENUM migration required.
    Abierta is the initial state; Cerrada is immutable (RN-22).
    """

    Abierta = "Abierta"
    Cerrada = "Cerrada"


class Liquidacion(BaseTenantModel):
    """One docente's salary liquidation for a specific period.

    Columns beyond BaseTenantModel:
        usuario_id           — FK to usuarios.id (the docente being liquidated)
        cohorte_id           — FK to cohortes.id (unit of liquidation)
        periodo_mes          — month 1..12
        periodo_anio         — year >= 2000
        rol                  — role under which this docente is liquidated
        comisiones           — JSONB snapshot of comisiones used in calculation
        base_monto           — base salary amount from SalarioBase
        plus_monto           — total plus amount from SalarioPlus × N comisiones
        total_monto          — base_monto + plus_monto (RN-34)
        desglose             — JSONB breakdown by clave (auditable)
        es_nexo              — True when rol == NEXO (RN-36)
        excluido_por_factura — True when usuario.facturador == True (RN-35)
        estado               — Abierta | Cerrada (CheckConstraint)
        cerrada_at           — timestamp set on closure
    """

    __tablename__ = "liquidacion"
    __table_args__ = (
        CheckConstraint(
            "periodo_mes >= 1 AND periodo_mes <= 12",
            name="ck_liquidacion_mes_valid",
        ),
        CheckConstraint(
            "periodo_anio >= 2000",
            name="ck_liquidacion_anio_valid",
        ),
        CheckConstraint(
            "estado IN ('Abierta','Cerrada')",
            name="ck_liquidacion_estado_valid",
        ),
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohortes.id", ondelete="RESTRICT"),
        nullable=False,
    )

    periodo_mes: Mapped[int] = mapped_column(Integer, nullable=False)
    periodo_anio: Mapped[int] = mapped_column(Integer, nullable=False)
    rol: Mapped[str] = mapped_column(String(30), nullable=False)

    comisiones: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    base_monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    plus_monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    desglose: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    es_nexo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    excluido_por_factura: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EstadoLiquidacion.Abierta,
        server_default="Abierta",
    )

    cerrada_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Liquidacion id={self.id} tenant_id={self.tenant_id} "
            f"usuario_id={self.usuario_id} cohorte_id={self.cohorte_id} "
            f"periodo={self.periodo_anio}-{self.periodo_mes:02d} "
            f"estado={self.estado!r} total={self.total_monto}>"
        )

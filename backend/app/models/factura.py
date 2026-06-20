"""
app/models/factura.py — Factura domain entity (C-18).

Represents a factura (invoice) submitted by a docente with facturador=True.
Facturas are managed separately from the Base+Plus liquidation (RN-35).
Two states: Pendiente (loaded) → Abonada (paid; sets abonada_at).

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class EstadoFactura(StrEnum):
    """Valid states for a Factura (RN-39).

    StrEnum → VARCHAR storage.
    Only two states: Pendiente (loaded) → Abonada (paid).
    """

    Pendiente = "Pendiente"
    Abonada = "Abonada"


class Factura(BaseTenantModel):
    """Invoice record for a facturante docente.

    Columns beyond BaseTenantModel:
        usuario_id          — FK to usuarios.id (the facturante)
        periodo_mes         — month 1..12
        periodo_anio        — year >= 2000
        detalle             — free text description of the service
        referencia_archivo  — opaque pointer to document storage (nullable)
        tamano_kb           — file size in KB (nullable)
        monto               — invoice amount (CHECK >= 0)
        estado              — Pendiente | Abonada (CheckConstraint)
        abonada_at          — timestamp when payment was confirmed
    """

    __tablename__ = "factura"
    __table_args__ = (
        CheckConstraint(
            "periodo_mes >= 1 AND periodo_mes <= 12",
            name="ck_factura_mes_valid",
        ),
        CheckConstraint(
            "periodo_anio >= 2000",
            name="ck_factura_anio_valid",
        ),
        CheckConstraint("monto >= 0", name="ck_factura_monto_positivo"),
        CheckConstraint(
            "estado IN ('Pendiente','Abonada')",
            name="ck_factura_estado_valid",
        ),
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    periodo_mes: Mapped[int] = mapped_column(Integer, nullable=False)
    periodo_anio: Mapped[int] = mapped_column(Integer, nullable=False)

    detalle: Mapped[str] = mapped_column(Text, nullable=False)
    referencia_archivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    tamano_kb: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EstadoFactura.Pendiente,
        server_default="Pendiente",
    )

    abonada_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Factura id={self.id} tenant_id={self.tenant_id} "
            f"usuario_id={self.usuario_id} monto={self.monto} estado={self.estado!r}>"
        )

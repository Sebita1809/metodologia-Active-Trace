"""
app/models/aviso.py — Aviso domain entity.

Represents an institutional notice board post (tablón de avisos) scoped to a tenant.
Supports audience segmentation: Global, PorMateria, PorCohorte, PorRol.
Soft delete, timestamps and tenant isolation from BaseTenantModel.

CHECK constraints (VARCHAR-based — NOT PG ENUM type):
  alcance  IN ('Global','PorMateria','PorCohorte','PorRol')
  severidad IN ('Info','Advertencia','Critico')

Implemented: C-15 (avisos-y-acknowledgment)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class AlcanceAviso(StrEnum):
    GLOBAL = "Global"
    POR_MATERIA = "PorMateria"
    POR_COHORTE = "PorCohorte"
    POR_ROL = "PorRol"


class SeveridadAviso(StrEnum):
    INFO = "Info"
    ADVERTENCIA = "Advertencia"
    CRITICO = "Critico"


class Aviso(BaseTenantModel):
    """Institutional notice board post.

    Columns:
        alcance      — audience segmentation: Global | PorMateria | PorCohorte | PorRol
        materia_id   — FK to materias.id (nullable; required when alcance=PorMateria)
        cohorte_id   — FK to cohortes.id (nullable; required when alcance=PorCohorte)
        rol_destino  — role name e.g. 'ALUMNO' (nullable; required when alcance=PorRol)
        severidad    — notice severity: Info | Advertencia | Critico (default Info)
        titulo       — notice title (max 300 chars)
        cuerpo       — notice body (max 10000 chars)
        inicio_en    — publication start datetime (UTC)
        fin_en       — publication end datetime (UTC)
        orden        — display order (default 0, lower = first)
        activo       — whether the notice is active (default True)
        requiere_ack — whether users must acknowledge the notice (default False)
    """

    __tablename__ = "aviso"
    __table_args__ = (
        CheckConstraint(
            "alcance IN ('Global','PorMateria','PorCohorte','PorRol')",
            name="ck_aviso_alcance",
        ),
        CheckConstraint(
            "severidad IN ('Info','Advertencia','Critico')",
            name="ck_aviso_severidad",
        ),
    )

    alcance: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    materia_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materias.id", ondelete="RESTRICT"),
        nullable=True,
    )

    cohorte_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohortes.id", ondelete="RESTRICT"),
        nullable=True,
    )

    rol_destino: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    severidad: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="Info",
        server_default="Info",
    )

    titulo: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    cuerpo: Mapped[str] = mapped_column(
        String(10000),
        nullable=False,
    )

    inicio_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    fin_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    orden: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    requiere_ack: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

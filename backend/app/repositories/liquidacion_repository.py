"""
app/repositories/liquidacion_repository.py — LiquidacionRepository (C-18).

Tenant-scoped repository for Liquidacion. Implements:
  - listar_periodo(cohorte_id, mes, anio) → all vivo liquidaciones for a period
  - get_combo(usuario_id, cohorte_id, mes, anio) → single vivo row for unique combo
  - listar_cerradas() → all Cerrada liquidaciones for this tenant (historial)
  - upsert_calculo(...) → create or update an Abierta liquidacion for the combo

Also exposes:
  - contar_comisiones_por_clave(usuario_id, cohorte_id, ref_date)
    Joins Asignacion with Materia to count active comisiones grouped by clave_plus.
    Returns dict[str, int] (clave → N comisiones).

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asignacion import Asignacion
from app.models.liquidacion import EstadoLiquidacion, Liquidacion
from app.models.materia import Materia
from app.repositories.base import BaseRepository


class LiquidacionRepository(BaseRepository[Liquidacion]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Liquidacion, session=session, tenant_id=tenant_id)

    async def listar_periodo(
        self, cohorte_id: uuid.UUID, mes: int, anio: int
    ) -> list[Liquidacion]:
        """Return all vivo Liquidaciones for (cohorte, mes, anio) scoped to tenant."""
        stmt = (
            self._base_query()
            .where(Liquidacion.cohorte_id == cohorte_id)
            .where(Liquidacion.periodo_mes == mes)
            .where(Liquidacion.periodo_anio == anio)
            .order_by(Liquidacion.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_combo(
        self,
        usuario_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        mes: int,
        anio: int,
    ) -> Liquidacion | None:
        """Return the single vivo Liquidacion for the unique (tenant, usuario, cohorte, periodo).

        Returns None if not found (normal before first calculation).
        """
        stmt = (
            self._base_query()
            .where(Liquidacion.usuario_id == usuario_id)
            .where(Liquidacion.cohorte_id == cohorte_id)
            .where(Liquidacion.periodo_mes == mes)
            .where(Liquidacion.periodo_anio == anio)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def listar_cerradas(self) -> list[Liquidacion]:
        """Return all Cerrada Liquidaciones for this tenant (historial).

        Includes only non-soft-deleted rows (via _base_query).
        Ordered by periodo desc for most recent first.
        """
        stmt = (
            self._base_query()
            .where(Liquidacion.estado == EstadoLiquidacion.Cerrada)
            .order_by(Liquidacion.periodo_anio.desc(), Liquidacion.periodo_mes.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_calculo(
        self,
        *,
        usuario_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        mes: int,
        anio: int,
        rol: str,
        comisiones: list,
        base_monto: Decimal,
        plus_monto: Decimal,
        total_monto: Decimal,
        desglose: dict | None,
        es_nexo: bool,
        excluido_por_factura: bool,
    ) -> Liquidacion:
        """Create or update the Liquidacion for the given combo (idempotent, RN-37).

        If an Abierta row exists for (tenant, usuario, cohorte, mes, anio) → update it.
        If no row exists → create it.
        If a Cerrada row exists → raise ValueError (cannot recalculate closed period, RN-22).
        """
        existing = await self.get_combo(usuario_id, cohorte_id, mes, anio)

        if existing is not None:
            if existing.estado == EstadoLiquidacion.Cerrada:
                raise ValueError(
                    f"Liquidacion para usuario {usuario_id} en periodo {anio}-{mes:02d} "
                    "está Cerrada y no puede ser recalculada (RN-22)."
                )
            # Update existing Abierta row
            updated = await self.update(
                existing.id,
                rol=rol,
                comisiones=comisiones,
                base_monto=base_monto,
                plus_monto=plus_monto,
                total_monto=total_monto,
                desglose=desglose,
                es_nexo=es_nexo,
                excluido_por_factura=excluido_por_factura,
            )
            return updated  # type: ignore[return-value]

        # Create new row
        liq = Liquidacion(
            tenant_id=self._tenant_id,
            usuario_id=usuario_id,
            cohorte_id=cohorte_id,
            periodo_mes=mes,
            periodo_anio=anio,
            rol=rol,
            comisiones=comisiones,
            base_monto=base_monto,
            plus_monto=plus_monto,
            total_monto=total_monto,
            desglose=desglose,
            es_nexo=es_nexo,
            excluido_por_factura=excluido_por_factura,
            estado=EstadoLiquidacion.Abierta,
        )
        return await self.create(liq)

    async def cerrar_periodo(
        self, cohorte_id: uuid.UUID, mes: int, anio: int
    ) -> list[Liquidacion]:
        """Close all Abierta liquidaciones for (cohorte, mes, anio).

        Sets estado='Cerrada' and cerrada_at=now() atomically.
        Returns the list of closed liquidaciones.
        Raises ValueError if the period is already fully closed or has no rows.
        """
        rows = await self.listar_periodo(cohorte_id, mes, anio)
        if not rows:
            raise ValueError(
                f"No hay liquidaciones para el período {anio}-{mes:02d} en la cohorte {cohorte_id}."
            )

        ya_cerradas = [r for r in rows if r.estado == EstadoLiquidacion.Cerrada]
        abiertas = [r for r in rows if r.estado == EstadoLiquidacion.Abierta]

        if abiertas and ya_cerradas:
            raise ValueError(
                "El período tiene liquidaciones en estado mixto (algunas abiertas, otras cerradas). "
                "Corrija los datos antes de cerrar."
            )

        if not abiertas:
            raise ValueError(
                f"El período {anio}-{mes:02d} ya está completamente cerrado (RN-22)."
            )

        now = datetime.now(tz=timezone.utc)
        cerradas: list[Liquidacion] = []
        for row in abiertas:
            updated = await self.update(
                row.id,
                estado=EstadoLiquidacion.Cerrada,
                cerrada_at=now,
            )
            if updated is not None:
                cerradas.append(updated)

        return cerradas


async def contar_comisiones_por_clave(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    ref_date: date,
) -> dict[str, int]:
    """Count active comisiones per clave_plus for a docente in a cohorte at ref_date.

    Joins Asignacion (active, tenant-scoped) with Materia to get clave_plus.
    An Asignacion is "active" at ref_date if:
        desde <= ref_date AND (hasta IS NULL OR hasta >= ref_date)

    For each active Asignacion with a non-NULL clave_plus, counts the number of
    comisiones (len(asignacion.comisiones)) towards that clave.

    Returns dict[clave, N] where N is the total count of comisiones for that clave.
    Claves with only NULL clave_plus materias are NOT included.
    """
    stmt = (
        select(Asignacion, Materia.clave_plus)
        .join(Materia, Asignacion.materia_id == Materia.id)
        .where(Asignacion.tenant_id == tenant_id)
        .where(Asignacion.deleted_at.is_(None))
        .where(Asignacion.usuario_id == usuario_id)
        .where(Asignacion.cohorte_id == cohorte_id)
        .where(Asignacion.desde <= ref_date)
        .where(
            (Asignacion.hasta.is_(None)) | (Asignacion.hasta >= ref_date)
        )
        .where(Materia.deleted_at.is_(None))
        .where(Materia.clave_plus.is_not(None))
    )
    result = await session.execute(stmt)
    rows = result.all()

    conteo: dict[str, int] = {}
    for asignacion, clave_plus in rows:
        if clave_plus is None:
            continue
        n_comisiones = len(asignacion.comisiones) if asignacion.comisiones else 0
        conteo[clave_plus] = conteo.get(clave_plus, 0) + n_comisiones

    return conteo

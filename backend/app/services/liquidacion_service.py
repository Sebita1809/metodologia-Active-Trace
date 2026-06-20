"""
app/services/liquidacion_service.py — LiquidacionService (C-18).

Orchestrates:
  - calcular_periodo: compute Base+Plus liquidations for all docentes in a cohorte×month
  - vista_periodo: segmented view + KPIs (F10.6, RN-36/38)
  - cerrar_periodo: immutable closure + AuditLog LIQUIDACION_CERRAR (RN-22)
  - historial: list closed liquidaciones

Governance: CRÍTICO — touches money, closure is irreversible, emits audit event.

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.models.asignacion import Asignacion
from app.models.audit_log import AuditLog
from app.models.liquidacion import EstadoLiquidacion, Liquidacion
from app.models.usuario import Usuario
from app.repositories.factura_repository import FacturaRepository
from app.repositories.liquidacion_repository import (
    LiquidacionRepository,
    contar_comisiones_por_clave,
)
from app.repositories.salario_base_repository import SalarioBaseRepository
from app.repositories.salario_plus_repository import SalarioPlusRepository
from app.schemas.liquidacion import (
    CalcularRequest,
    CerrarRequest,
    LiquidacionRead,
    PeriodoSegmento,
    PeriodoView,
)
from app.services.liquidacion_calculo import calcular_liquidacion


def _to_liquidacion_read(row: Liquidacion) -> LiquidacionRead:
    return LiquidacionRead(
        id=row.id,
        tenant_id=row.tenant_id,
        usuario_id=row.usuario_id,
        cohorte_id=row.cohorte_id,
        periodo_mes=row.periodo_mes,
        periodo_anio=row.periodo_anio,
        rol=row.rol,
        comisiones=row.comisiones,
        base_monto=row.base_monto,
        plus_monto=row.plus_monto,
        total_monto=row.total_monto,
        desglose=row.desglose,
        es_nexo=row.es_nexo,
        excluido_por_factura=row.excluido_por_factura,
        estado=row.estado,
        cerrada_at=row.cerrada_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


class LiquidacionService:
    """Orchestrates liquidation calculation, view, closure and history."""

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._repo = LiquidacionRepository(session=session, tenant_id=tenant_id)
        self._base_repo = SalarioBaseRepository(session=session, tenant_id=tenant_id)
        self._plus_repo = SalarioPlusRepository(session=session, tenant_id=tenant_id)
        self._factura_repo = FacturaRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # 5.3 — calcular_periodo
    # ------------------------------------------------------------------

    async def calcular_periodo(
        self, req: CalcularRequest, current_user: CurrentUser
    ) -> list[LiquidacionRead]:
        """Calculate liquidations for all docentes in (cohorte, mes, anio).

        Algorithm:
          ref_date = date(anio, mes, 1)
          For each unique (usuario_id, rol) assignment in the cohorte at ref_date:
            1. Determine es_nexo (rol == 'NEXO') and excluido_por_factura (usuario.facturador)
            2. Fetch base_vigente for (rol, ref_date)
            3. Fetch plus_vigentes for each (clave, rol, ref_date)
            4. Count comisiones_por_clave
            5. Call calcular_liquidacion (pure fn, RN-33/34)
            6. Upsert — idempotent (RN-37)

        Raises 409 if any row in the period is already Cerrada (RN-22).
        """
        cohorte_id = req.cohorte_id
        mes = req.mes
        anio = req.anio
        ref_date = date(anio, mes, 1)

        # Check for existing Cerrada rows in this period (immutability guard, RN-22)
        existing = await self._repo.listar_periodo(cohorte_id, mes, anio)
        for liq in existing:
            if liq.estado == EstadoLiquidacion.Cerrada:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"El período {anio}-{mes:02d} de la cohorte {cohorte_id} "
                        "está Cerrado y no puede ser recalculado (RN-22)."
                    ),
                )

        # Get all active docentes in the cohorte at ref_date
        asignaciones = await self._get_asignaciones_activas(cohorte_id, ref_date)

        # Group by usuario_id → take rol from asignacion
        # A docente may have multiple asignaciones; group by (usuario_id, rol)
        usuario_rol_pairs: dict[tuple[uuid.UUID, str], None] = {}
        for a in asignaciones:
            usuario_rol_pairs[(a.usuario_id, a.rol)] = None

        resultados: list[LiquidacionRead] = []

        for (usuario_id, rol), _ in usuario_rol_pairs.items():
            # Fetch usuario for facturador flag
            usuario = await self._get_usuario(usuario_id)
            if usuario is None:
                continue

            excluido_por_factura = usuario.facturador
            es_nexo = (rol == "NEXO")

            # Base vigente
            base_row = await self._base_repo.get_vigente(rol, ref_date)
            base_vigente = base_row.monto if base_row is not None else None

            # Comisiones por clave
            comisiones_por_clave = await contar_comisiones_por_clave(
                session=self._session,
                tenant_id=self._tenant_id,
                usuario_id=usuario_id,
                cohorte_id=cohorte_id,
                ref_date=ref_date,
            )

            # Plus vigentes for each clave found
            plus_vigentes: dict[str, Decimal] = {}
            for clave in comisiones_por_clave:
                plus_row = await self._plus_repo.get_vigente(clave, rol, ref_date)
                if plus_row is not None:
                    plus_vigentes[clave] = plus_row.monto

            # Snapshot comisiones for this usuario in this cohorte
            comisiones_snapshot = self._build_comisiones_snapshot(
                asignaciones, usuario_id
            )

            # Calculate (pure function, no I/O)
            base_monto, plus_monto, total_monto, desglose = calcular_liquidacion(
                rol=rol,
                base_vigente=base_vigente,
                plus_vigentes=plus_vigentes,
                comisiones_por_clave=comisiones_por_clave,
            )

            # Upsert (idempotent, RN-37)
            liq = await self._repo.upsert_calculo(
                usuario_id=usuario_id,
                cohorte_id=cohorte_id,
                mes=mes,
                anio=anio,
                rol=rol,
                comisiones=comisiones_snapshot,
                base_monto=base_monto,
                plus_monto=plus_monto,
                total_monto=total_monto,
                desglose=desglose,
                es_nexo=es_nexo,
                excluido_por_factura=excluido_por_factura,
            )
            resultados.append(_to_liquidacion_read(liq))

        await self._session.flush()
        return resultados

    # ------------------------------------------------------------------
    # 5.4 — vista_periodo
    # ------------------------------------------------------------------

    async def vista_periodo(self, cohorte_id: uuid.UUID, mes: int, anio: int) -> PeriodoView:
        """Return the segmented view of a period with KPIs (F10.6, RN-36/38).

        Segments:
          general    — non-facturante, non-NEXO
          nexo       — es_nexo=True (NEXO role)
          facturantes — excluido_por_factura=True
        KPIs:
          total_sin_factura = general.total + nexo.total
          total_con_factura = sum of facturas for the same period
        """
        rows = await self._repo.listar_periodo(cohorte_id, mes, anio)

        general_rows: list[LiquidacionRead] = []
        nexo_rows: list[LiquidacionRead] = []
        factura_rows: list[LiquidacionRead] = []

        for row in rows:
            dto = _to_liquidacion_read(row)
            if row.excluido_por_factura:
                factura_rows.append(dto)
            elif row.es_nexo:
                nexo_rows.append(dto)
            else:
                general_rows.append(dto)

        def _sum(items: list[LiquidacionRead]) -> Decimal:
            return sum((i.total_monto for i in items), Decimal("0"))

        general_total = _sum(general_rows)
        nexo_total = _sum(nexo_rows)
        facturantes_total = _sum(factura_rows)

        total_con_factura = await self._factura_repo.sumar_periodo(mes, anio)

        return PeriodoView(
            cohorte_id=cohorte_id,
            mes=mes,
            anio=anio,
            general=PeriodoSegmento(liquidaciones=general_rows, total=general_total),
            nexo=PeriodoSegmento(liquidaciones=nexo_rows, total=nexo_total),
            facturantes=PeriodoSegmento(
                liquidaciones=factura_rows, total=facturantes_total
            ),
            total_sin_factura=general_total + nexo_total,
            total_con_factura=total_con_factura,
        )

    # ------------------------------------------------------------------
    # 5.5 — cerrar_periodo
    # ------------------------------------------------------------------

    async def cerrar_periodo(
        self, req: CerrarRequest, current_user: CurrentUser
    ) -> list[LiquidacionRead]:
        """Close all Abierta liquidaciones for the period. Emits LIQUIDACION_CERRAR audit.

        Raises 409 if already closed or no rows found.
        Raises 409 if period is empty.
        Emits AuditLog with actor_id from JWT (never from body).
        """
        try:
            cerradas = await self._repo.cerrar_periodo(req.cohorte_id, req.mes, req.anio)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        # Emit audit event (RN-23, design §7)
        total_cerrado = sum(
            (r.total_monto for r in cerradas if not r.excluido_por_factura),
            Decimal("0"),
        )
        audit = AuditLog(
            tenant_id=self._tenant_id,
            actor_id=current_user.user_id,
            accion="LIQUIDACION_CERRAR",
            filas_afectadas=len(cerradas),
            detalle={
                "cohorte_id": str(req.cohorte_id),
                "periodo_mes": req.mes,
                "periodo_anio": req.anio,
                "n_liquidaciones": len(cerradas),
                "total_cerrado": str(total_cerrado),
            },
        )
        self._session.add(audit)
        await self._session.flush()

        return [_to_liquidacion_read(r) for r in cerradas]

    # ------------------------------------------------------------------
    # 5.6 — historial
    # ------------------------------------------------------------------

    async def historial(self) -> list[LiquidacionRead]:
        """Return all closed liquidaciones for this tenant (historial)."""
        rows = await self._repo.listar_cerradas()
        return [_to_liquidacion_read(r) for r in rows]

    async def get_by_id(self, liquidacion_id: uuid.UUID) -> LiquidacionRead:
        """Return a single liquidacion by id. Raises 404 if not found."""
        row = await self._repo.get(liquidacion_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Liquidacion no encontrada.")
        return _to_liquidacion_read(row)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_asignaciones_activas(
        self, cohorte_id: uuid.UUID, ref_date: date
    ) -> list[Asignacion]:
        """Return all active Asignaciones for the cohorte at ref_date (tenant-scoped)."""
        stmt = (
            select(Asignacion)
            .where(Asignacion.tenant_id == self._tenant_id)
            .where(Asignacion.deleted_at.is_(None))
            .where(Asignacion.cohorte_id == cohorte_id)
            .where(Asignacion.desde <= ref_date)
            .where(
                (Asignacion.hasta.is_(None)) | (Asignacion.hasta >= ref_date)
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _get_usuario(self, usuario_id: uuid.UUID) -> Usuario | None:
        """Fetch a Usuario by id (tenant-scoped)."""
        stmt = (
            select(Usuario)
            .where(Usuario.id == usuario_id)
            .where(Usuario.tenant_id == self._tenant_id)
            .where(Usuario.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _build_comisiones_snapshot(
        self, asignaciones: list[Asignacion], usuario_id: uuid.UUID
    ) -> list:
        """Build a snapshot of comisiones for a user from their asignaciones."""
        snapshot = []
        for a in asignaciones:
            if a.usuario_id != usuario_id:
                continue
            if a.comisiones:
                snapshot.extend(a.comisiones)
        return snapshot

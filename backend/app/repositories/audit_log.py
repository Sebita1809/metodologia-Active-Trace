"""
app/repositories/audit_log.py — Append-only repository for AuditLog.

This repository intentionally does NOT inherit BaseRepository[T].
BaseRepository exposes update() and soft_delete(), both incompatible with
the append-only contract of AuditLog (D-03).

Public API:
  crear(...)                         — insert one immutable record scoped to this tenant
  listar(...)                        — query records filtered by tenant; optional actor_id filter
  listar_filtrado(...)               — filtered + paginated query (C-19)
  acciones_por_dia(...)              — daily action counts in date range (C-19)
  comunicaciones_por_docente(...)    — communication status counts per actor (C-19)
  interacciones_por_docente_materia(...)  — interaction counts per actor × materia (C-19)
  ultimas_acciones(...)              — latest N records ordered desc (C-19)

All reads are scoped to self._tenant_id — tenant isolation is mandatory.
No update/delete methods exist — the append-only contract (C-05) is preserved.

Implemented: C-05 (audit-log)
Updated:     C-19 (panel-auditoria-metricas) — aggregation queries and filtros
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

# Maximum allowed limit for ultimas_acciones to protect performance (C-19)
_MAX_ULTIMAS_ACCIONES = 1000


class AuditLogRepository:
    """Append-only repository for AuditLog records.

    Does not expose update() or soft_delete() — the model is immutable by design.
    All queries are scoped to the tenant_id provided at construction time.

    Constructor parameters:
        session   — open AsyncSession for the current request / test
        tenant_id — UUID of the tenant that owns this repository scope
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Write (append-only)
    # ------------------------------------------------------------------

    async def crear(
        self,
        *,
        actor_id: uuid.UUID,
        accion: str,
        impersonado_id: uuid.UUID | None = None,
        materia_id: uuid.UUID | None = None,
        detalle: dict | None = None,
        filas_afectadas: int = 0,
        ip: str | None,
        user_agent: str | None,
    ) -> AuditLog:
        """Persist one immutable audit record and return it with server fields.

        The tenant_id is always taken from this repository's scope —
        callers never specify it.

        Parameters
        ----------
        actor_id:
            UUID of the real acting user (always from the JWT sub claim).
        accion:
            Action code string from AccionAuditoria catalog.
        impersonado_id:
            UUID of the impersonated user, or None for normal sessions.
        materia_id:
            UUID of related materia, or None if not applicable.
        detalle:
            Structured context dict stored as JSONB (nullable).
        filas_afectadas:
            Number of rows affected by the action (default 0).
        ip:
            Client IP address (nullable).
        user_agent:
            Client User-Agent header value (nullable).
        """
        record = AuditLog(
            tenant_id=self._tenant_id,
            actor_id=actor_id,
            accion=accion,
            impersonado_id=impersonado_id,
            materia_id=materia_id,
            detalle=detalle,
            filas_afectadas=filas_afectadas,
            ip=ip,
            user_agent=user_agent,
        )
        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)
        return record

    # ------------------------------------------------------------------
    # Read (tenant-scoped)
    # ------------------------------------------------------------------

    async def listar(
        self,
        *,
        actor_id: uuid.UUID | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Return audit records for this tenant, optionally filtered by actor.

        Parameters
        ----------
        actor_id:
            If provided, return only records where actor_id matches.
            Supports the 'propio' scope in the audit query endpoint.
        limit:
            Maximum number of records to return (default 500).
        offset:
            Number of records to skip (for pagination).
        """
        stmt = (
            select(AuditLog)
            .where(AuditLog.tenant_id == self._tenant_id)
            .order_by(AuditLog.fecha_hora.desc())
            .limit(limit)
            .offset(offset)
        )

        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, record_id: uuid.UUID) -> AuditLog | None:
        """Return a single audit record by ID if it belongs to this tenant."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.tenant_id == self._tenant_id)
            .where(AuditLog.id == record_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # C-19: Aggregation queries (read-only, append-only preserved)
    # ------------------------------------------------------------------

    async def acciones_por_dia(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        actor_ids: list[uuid.UUID] | None = None,
    ) -> list[dict[str, Any]]:
        """Return daily action counts in a date range, scoped to this tenant.

        Aggregates by date_trunc('day', fecha_hora). If actor_ids is provided,
        only counts records where actor_id is in the given set.

        Parameters
        ----------
        desde:
            Start of date range (inclusive).
        hasta:
            End of date range (inclusive).
        actor_ids:
            Optional list of actor UUIDs to scope (propio). None means global.

        Returns
        -------
        List of dicts with keys 'dia' (date) and 'total' (int), ordered by dia.
        """
        dia_col = func.date_trunc("day", AuditLog.fecha_hora).label("dia")
        stmt = (
            select(dia_col, func.count().label("total"))
            .where(AuditLog.tenant_id == self._tenant_id)
            .where(AuditLog.fecha_hora >= desde)
            .where(AuditLog.fecha_hora <= hasta)
            .group_by(dia_col)
            .order_by(dia_col)
        )
        if actor_ids is not None:
            if not actor_ids:
                return []
            stmt = stmt.where(AuditLog.actor_id.in_(actor_ids))

        result = await self._session.execute(stmt)
        return [{"dia": row.dia, "total": row.total} for row in result.all()]

    async def comunicaciones_por_docente(
        self,
        *,
        actor_ids: list[uuid.UUID] | None = None,
    ) -> list[dict[str, Any]]:
        """Return COMUNICACION_* action counts grouped by actor_id and accion code.

        Filters only rows where accion starts with 'COMUNICACION_'.
        If actor_ids is provided, scopes to those actors.

        Returns
        -------
        List of dicts with keys 'actor_id' (UUID), 'accion' (str), 'total' (int).
        """
        stmt = (
            select(
                AuditLog.actor_id,
                AuditLog.accion,
                func.count().label("total"),
            )
            .where(AuditLog.tenant_id == self._tenant_id)
            .where(AuditLog.accion.like("COMUNICACION_%"))
            .group_by(AuditLog.actor_id, AuditLog.accion)
        )
        if actor_ids is not None:
            if not actor_ids:
                return []
            stmt = stmt.where(AuditLog.actor_id.in_(actor_ids))

        result = await self._session.execute(stmt)
        return [
            {"actor_id": row.actor_id, "accion": row.accion, "total": row.total}
            for row in result.all()
        ]

    async def interacciones_por_docente_materia(
        self,
        *,
        actor_ids: list[uuid.UUID] | None = None,
    ) -> list[dict[str, Any]]:
        """Return interaction counts grouped by actor_id and materia_id.

        Rows with materia_id IS NULL are grouped under materia_id=None (sin materia).
        If actor_ids is provided, scopes to those actors.

        Returns
        -------
        List of dicts: 'actor_id' (UUID), 'materia_id' (UUID|None), 'total' (int).
        """
        stmt = (
            select(
                AuditLog.actor_id,
                AuditLog.materia_id,
                func.count().label("total"),
            )
            .where(AuditLog.tenant_id == self._tenant_id)
            .group_by(AuditLog.actor_id, AuditLog.materia_id)
        )
        if actor_ids is not None:
            if not actor_ids:
                return []
            stmt = stmt.where(AuditLog.actor_id.in_(actor_ids))

        result = await self._session.execute(stmt)
        return [
            {"actor_id": row.actor_id, "materia_id": row.materia_id, "total": row.total}
            for row in result.all()
        ]

    async def ultimas_acciones(
        self,
        *,
        limit: int,
        actor_ids: list[uuid.UUID] | None = None,
    ) -> list[AuditLog]:
        """Return the latest N audit records ordered by fecha_hora descending.

        The limit is capped at _MAX_ULTIMAS_ACCIONES to protect performance.
        If actor_ids is provided, scopes to those actors.

        Parameters
        ----------
        limit:
            Maximum number of records to return (capped at _MAX_ULTIMAS_ACCIONES).
        actor_ids:
            Optional list of actor UUIDs to scope (propio). None means global.
        """
        effective_limit = min(limit, _MAX_ULTIMAS_ACCIONES)

        if actor_ids is not None and not actor_ids:
            return []

        stmt = (
            select(AuditLog)
            .where(AuditLog.tenant_id == self._tenant_id)
            .order_by(AuditLog.fecha_hora.desc())
            .limit(effective_limit)
        )
        if actor_ids is not None:
            stmt = stmt.where(AuditLog.actor_id.in_(actor_ids))

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def listar_filtrado(
        self,
        *,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        materia_id: uuid.UUID | None = None,
        actor_ids: list[uuid.UUID] | None = None,
        accion: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Return audit records with optional composable filters and pagination.

        All filters are optional (None = no constraint on that field).
        Results are ordered by fecha_hora DESC.
        Tenant isolation is always applied.

        Parameters
        ----------
        desde:
            Filter records with fecha_hora >= desde.
        hasta:
            Filter records with fecha_hora <= hasta.
        materia_id:
            Filter by exact materia_id.
        actor_ids:
            Scope to a set of actor UUIDs. Empty list → return empty (fail-closed).
            None → no actor filter (global scope).
        accion:
            Filter by exact action code.
        limit:
            Maximum records to return (for pagination).
        offset:
            Number of records to skip (for pagination).
        """
        if actor_ids is not None and not actor_ids:
            return []

        stmt = (
            select(AuditLog)
            .where(AuditLog.tenant_id == self._tenant_id)
            .order_by(AuditLog.fecha_hora.desc())
            .limit(limit)
            .offset(offset)
        )

        if actor_ids is not None:
            stmt = stmt.where(AuditLog.actor_id.in_(actor_ids))
        if desde is not None:
            stmt = stmt.where(AuditLog.fecha_hora >= desde)
        if hasta is not None:
            stmt = stmt.where(AuditLog.fecha_hora <= hasta)
        if materia_id is not None:
            stmt = stmt.where(AuditLog.materia_id == materia_id)
        if accion is not None:
            stmt = stmt.where(AuditLog.accion == accion)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

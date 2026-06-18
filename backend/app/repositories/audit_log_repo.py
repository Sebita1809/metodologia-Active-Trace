"""Repository for AuditLog — append-only, no update/delete."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    """Append-only repository for audit log entries.

    Only exposes ``add()`` and ``list()`` operations.
    No ``update()`` or ``delete()`` — intentional append-only design.
    """

    async def add(self, db: AsyncSession, entry: AuditLog) -> AuditLog:
        """Persist a new audit log entry."""
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    async def list(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
        actor_id: uuid.UUID | None = None,
        accion: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[AuditLog]:
        """List audit log entries with optional filters.

        All queries are scoped to ``tenant_id``.
        Results ordered by ``created_at`` DESC (most recent first).
        """
        stmt = (
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if fecha_desde is not None:
            stmt = stmt.where(AuditLog.fecha_hora >= fecha_desde)
        if fecha_hasta is not None:
            stmt = stmt.where(AuditLog.fecha_hora <= fecha_hasta)
        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if accion is not None:
            stmt = stmt.where(AuditLog.accion == accion)

        result = await db.execute(stmt)
        return result.scalars().all()

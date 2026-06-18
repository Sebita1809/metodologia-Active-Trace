"""Audit service — helpers for recording and querying audit log entries."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_codes import AuditAction
from app.models.audit_log import AuditLog
from app.repositories.audit_log_repo import AuditLogRepository


async def audit_record(
    db: AsyncSession,
    actor_id: uuid.UUID,
    accion: AuditAction,
    *,
    tenant_id: uuid.UUID,
    impersonado_id: uuid.UUID | None = None,
    materia_id: uuid.UUID | None = None,
    detalle: dict | None = None,
    filas_afectadas: int | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Record an action in the audit log.

    Parameters
    ----------
    db : AsyncSession
        Database session.
    actor_id : uuid.UUID
        UUID of the user performing the action.
    accion : AuditAction
        Standardised action code from the ``AuditAction`` enum.
    tenant_id : uuid.UUID
        Tenant context.
    impersonado_id : uuid.UUID | None
        If under impersonation, the impersonated user's UUID.
    materia_id : uuid.UUID | None
        Optional materia reference (logical FK, resolved at query time).
    detalle : dict | None
        Optional JSON-serialisable dict with action context.
    filas_afectadas : int | None
        Number of affected rows / records.
    ip : str | None
        Client IP address.
    user_agent : str | None
        Client user-agent string.

    Returns
    -------
    AuditLog
        The persisted ``AuditLog`` instance.
    """
    entry = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        accion=accion.value,
        impersonado_id=impersonado_id,
        materia_id=materia_id,
        detalle=detalle,
        filas_afectadas=filas_afectadas,
        ip=ip,
        user_agent=user_agent,
        fecha_hora=datetime.now(timezone.utc),
    )
    repo = AuditLogRepository()
    return await repo.add(db, entry)


async def list_audit_logs(
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
    """Query audit log entries with optional filters.

    Always scoped to ``tenant_id``. Ordered by ``created_at`` DESC (most recent first).
    """
    repo = AuditLogRepository()
    return await repo.list(
        db,
        tenant_id=tenant_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        actor_id=actor_id,
        accion=accion,
        limit=limit,
        offset=offset,
    )

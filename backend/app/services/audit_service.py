"""
app/services/audit_service.py — Audit log write helper.

Usage example::

    from app.services.audit_service import AuditService
    from app.services.audit_codes import AccionAuditoria

    svc = AuditService(session=session, tenant_id=current_user.tenant_id)
    await svc.registrar(
        current_user,
        AccionAuditoria.CALIFICACIONES_IMPORTAR,
        filas_afectadas=42,
        ip=request.client.host,
        user_agent=request.headers.get("user-agent"),
    )

Design decisions:
  D-07: actor_id is always taken from current_user.user_id — callers cannot
        override it. impersonado_id is taken from current_user.impersonando_user_id.
  D-04: detalle stored as JSONB.
  D-05: accion is typed as AccionAuditoria so the catalog is always enforced.

Implemented: C-05 (audit-log)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.models.audit_log import AuditLog
from app.repositories.audit_log import AuditLogRepository
from app.services.audit_codes import AccionAuditoria


class AuditService:
    """Service for writing immutable audit records.

    actor_id is derived exclusively from the CurrentUser DTO (which itself
    is derived from the verified JWT) — callers cannot inject an arbitrary
    actor_id. This is the primary defence against attribution forgery.

    Constructor parameters:
        session   — open AsyncSession for the current request
        tenant_id — UUID of the tenant scope (usually current_user.tenant_id)
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._repo = AuditLogRepository(session=session, tenant_id=tenant_id)

    async def registrar(
        self,
        current_user: CurrentUser,
        accion: AccionAuditoria,
        *,
        materia_id: uuid.UUID | None = None,
        detalle: dict | None = None,
        filas_afectadas: int = 0,
        ip: str | None,
        user_agent: str | None,
    ) -> AuditLog:
        """Persist one audit record and return it.

        Parameters
        ----------
        current_user:
            Verified identity from the JWT. actor_id is taken as
            current_user.user_id. impersonado_id is taken as
            current_user.impersonando_user_id (None for normal sessions).
        accion:
            Standardised action code from AccionAuditoria catalog.
        materia_id:
            UUID of related materia, or None if not applicable.
        detalle:
            Structured context dict stored as JSONB (nullable).
        filas_afectadas:
            Number of rows affected by the action (default 0).
        ip:
            Client IP address string (nullable).
        user_agent:
            Client User-Agent header value (nullable).
        """
        return await self._repo.crear(
            actor_id=current_user.user_id,
            accion=str(accion),
            impersonado_id=current_user.impersonando_user_id,
            materia_id=materia_id,
            detalle=detalle,
            filas_afectadas=filas_afectadas,
            ip=ip,
            user_agent=user_agent,
        )

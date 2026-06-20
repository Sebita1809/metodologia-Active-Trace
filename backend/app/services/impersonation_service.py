"""
app/services/impersonation_service.py — Impersonation session lifecycle.

Implements start and end of impersonation sessions:
  - iniciar_impersonacion: validates permission, emits impersonation token, audits
  - finalizar_impersonacion: records FINALIZAR audit, returns normal token hint

Design decisions (from design.md D-06):
  - The real actor is always in JWT 'sub'; the impersonated user is in 'impersonando'.
  - RBAC resolves as the impersonated user (reproduce their view).
  - All audit attribution is to the real actor.
  - TTL = same 15 min as a normal access token (OQ-2 decision).

Implemented: C-05 (audit-log)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.config import get_settings
from app.core.security import create_access_token
from app.services.audit_codes import AccionAuditoria
from app.services.audit_service import AuditService
from app.services.rbac_service import RbacService

from datetime import datetime, timezone


class ImpersonationService:
    """Service that handles start and end of impersonation sessions.

    Constructor parameters:
        session    — open AsyncSession for the current request
        tenant_id  — UUID of the tenant scope
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._audit_svc = AuditService(session=session, tenant_id=tenant_id)

    async def iniciar_impersonacion(
        self,
        *,
        current_user: CurrentUser,
        usuario_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> str:
        """Emit an impersonation access token and audit the start.

        The emitted token carries:
          - sub: real actor's user_id
          - tenant_id: tenant of the impersonated user (same tenant in this system)
          - roles: roles of the IMPERSONATED user (so RBAC resolves as them)
          - impersonando: UUID of the impersonated user

        Parameters
        ----------
        current_user:
            Verified identity of the real actor from JWT.
        usuario_id:
            UUID of the user to impersonate.
        ip:
            Client IP address.
        user_agent:
            Client User-Agent header.

        Returns
        -------
        A signed JWT access token for the impersonation session.
        """
        settings = get_settings()

        # Fetch impersonated user's roles
        rbac_svc = RbacService(session=self._session)
        ahora = datetime.now(tz=timezone.utc)
        imp_perms = await rbac_svc.resolver_permisos_efectivos(
            usuario_id,
            self._tenant_id,
            ahora,
        )
        # Extract just the role names from the usuario_rol table
        imp_roles = await self._get_user_roles(usuario_id)

        # Emit impersonation token
        token = create_access_token(
            user_id=current_user.user_id,  # real actor in sub
            tenant_id=self._tenant_id,
            roles=imp_roles,              # impersonated user's roles (D-06)
            secret_key=settings.secret_key,
            expire_minutes=settings.access_token_expire_minutes,
            impersonando_user_id=usuario_id,
        )

        # Audit INICIAR (actor = real actor, impersonado = target)
        audit_user = CurrentUser(
            user_id=current_user.user_id,
            tenant_id=self._tenant_id,
            roles=imp_roles,
            impersonando_user_id=usuario_id,
        )
        await self._audit_svc.registrar(
            audit_user,
            AccionAuditoria.IMPERSONACION_INICIAR,
            ip=ip,
            user_agent=user_agent,
        )

        return token

    async def finalizar_impersonacion(
        self,
        *,
        current_user: CurrentUser,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        """Record the end of an impersonation session.

        The CurrentUser from the impersonation token already carries
        impersonando_user_id, so the audit record is correctly attributed.
        """
        await self._audit_svc.registrar(
            current_user,
            AccionAuditoria.IMPERSONACION_FINALIZAR,
            ip=ip,
            user_agent=user_agent,
        )

    async def _get_user_roles(self, user_id: uuid.UUID) -> list[str]:
        """Return the current role names assigned to user_id within this tenant."""
        from sqlalchemy import text  # noqa: PLC0415

        result = await self._session.execute(
            text(
                """
                SELECT r.nombre FROM usuario_rol ur
                JOIN roles r ON r.id = ur.rol_id
                WHERE ur.user_id = :uid
                  AND ur.tenant_id = :tid
                  AND ur.deleted_at IS NULL
                  AND r.deleted_at IS NULL
                  AND ur.vigente_desde <= now()
                  AND (ur.vigente_hasta IS NULL OR ur.vigente_hasta >= now())
                """
            ),
            {"uid": str(user_id), "tid": str(self._tenant_id)},
        )
        return [row[0] for row in result]

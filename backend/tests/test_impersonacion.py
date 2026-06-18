"""Tests for C-05 audit-log: impersonation endpoints (iniciar / finalizar)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_codes import AuditAction
from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.auth_user import AuthUser
from app.models.tenant import Tenant

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _make_target_user(
    db_session: AsyncSession, tenant_id: uuid.UUID
) -> AuthUser:
    user = AuthUser(
        tenant_id=tenant_id,
        email=f"target_{uuid.uuid4().hex[:12]}@example.com",
        password_hash="argon2_placeholder_in_test",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _cleanup_user(db_session: AsyncSession, user_id: uuid.UUID) -> None:
    await db_session.execute(
        text("DELETE FROM auth_user WHERE id = :id"),
        {"id": user_id},
    )
    await db_session.commit()


# ═══════════════════════════════════════════════════════════════════
# 3.6 — 3.9  Impersonation endpoints
# ═══════════════════════════════════════════════════════════════════


class TestImpersonacion:
    async def test_iniciar_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """WHEN user with impersonacion:usar starts impersonation THEN 200 + impersonation JWT."""
        admin_token = create_access_token(
            user_id=str(uuid.uuid4()),
            tenant_id=str(tenant_a.id),
            roles=["ADMIN"],
        )

        target_user = await _make_target_user(db_session, tenant_a.id)
        try:
            resp = await async_client.post(
                "/api/v1/impersonacion/iniciar",
                json={"usuario_id": str(target_user.id)},
                headers=_auth_headers(admin_token),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert data["impersonating"] is True
            assert data["impersonated_user_id"] == str(target_user.id)
            assert data["token_type"] == "bearer"
        finally:
            await _cleanup_user(db_session, target_user.id)

    async def test_iniciar_without_permission_403(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """WHEN user WITHOUT impersonacion:usar tries to impersonate THEN 403."""
        alumno_token = create_access_token(
            user_id=str(uuid.uuid4()),
            tenant_id=str(tenant_a.id),
            roles=["ALUMNO"],
        )

        resp = await async_client.post(
            "/api/v1/impersonacion/iniciar",
            json={"usuario_id": str(uuid.uuid4())},
            headers=_auth_headers(alumno_token),
        )
        assert resp.status_code == 403

    async def test_iniciar_target_not_found_404(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """WHEN target user does not exist in tenant THEN 404."""
        admin_token = create_access_token(
            user_id=str(uuid.uuid4()),
            tenant_id=str(tenant_a.id),
            roles=["ADMIN"],
        )

        resp = await async_client.post(
            "/api/v1/impersonacion/iniciar",
            json={"usuario_id": str(uuid.uuid4())},
            headers=_auth_headers(admin_token),
        )
        assert resp.status_code == 404

    async def test_finalizar_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """WHEN ending impersonation THEN 200 + normal access JWT."""
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        impersonation_token = create_access_token(
            user_id=str(target_id),
            tenant_id=str(tenant_a.id),
            roles=["ADMIN"],
            impersonated_user_id=str(target_id),
            actor_id=str(actor_id),
        )

        resp = await async_client.post(
            "/api/v1/impersonacion/finalizar",
            headers=_auth_headers(impersonation_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["impersonating"] is False
        assert data["token_type"] == "bearer"

    async def test_finalizar_without_impersonation_400(
        self,
        async_client: AsyncClient,
        tenant_a: Tenant,
    ) -> None:
        """WHEN trying to end impersonation without active session THEN 400."""
        normal_token = create_access_token(
            user_id=str(uuid.uuid4()),
            tenant_id=str(tenant_a.id),
            roles=["ADMIN"],
        )

        resp = await async_client.post(
            "/api/v1/impersonacion/finalizar",
            headers=_auth_headers(normal_token),
        )
        assert resp.status_code == 400
        assert "sesión de impersonación activa" in resp.json()["detail"]

    async def test_accion_bajo_impersonacion_registra_actor_real(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """WHEN impersonation is initiated THEN audit_log captures the real admin as actor_id."""
        admin_id = uuid.uuid4()
        admin_token = create_access_token(
            user_id=str(admin_id),
            tenant_id=str(tenant_a.id),
            roles=["ADMIN"],
        )

        target_user = await _make_target_user(db_session, tenant_a.id)
        try:
            resp = await async_client.post(
                "/api/v1/impersonacion/iniciar",
                json={"usuario_id": str(target_user.id)},
                headers=_auth_headers(admin_token),
            )
            assert resp.status_code == 200

            # Verify audit log entry
            result = await db_session.execute(
                select(AuditLog).where(
                    AuditLog.accion == AuditAction.IMPERSONACION_INICIAR.value
                )
            )
            entry = result.scalar_one()
            assert entry.actor_id == admin_id
            assert entry.impersonado_id == target_user.id
            assert entry.tenant_id == tenant_a.id
        finally:
            await _cleanup_user(db_session, target_user.id)

    async def test_finalizar_registra_audit(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """WHEN impersonation ends THEN audit_log records IMPERSONACION_FINALIZAR."""
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        impersonation_token = create_access_token(
            user_id=str(target_id),
            tenant_id=str(tenant_a.id),
            roles=["ADMIN"],
            impersonated_user_id=str(target_id),
            actor_id=str(actor_id),
        )

        resp = await async_client.post(
            "/api/v1/impersonacion/finalizar",
            headers=_auth_headers(impersonation_token),
        )
        assert resp.status_code == 200

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.accion == AuditAction.IMPERSONACION_FINALIZAR.value
            )
        )
        entry = result.scalar_one()
        assert entry.actor_id == actor_id
        assert entry.impersonado_id == target_id

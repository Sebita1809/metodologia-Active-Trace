"""Tests for RBAC, validation, and multi-tenant isolation for usuario/asignacion endpoints (C-07)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.tenant import Tenant

pytestmark = pytest.mark.asyncio

USUARIOS_BASE = "/api/v1/admin/usuarios"
ASIGNACIONES_BASE = "/api/v1/asignaciones"


def _token(tenant_id: uuid.UUID, roles: list[str]) -> dict[str, str]:
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        roles=roles,
    )
    return {"Authorization": f"Bearer {token}"}


def _admin_token(tenant_id: uuid.UUID) -> dict[str, str]:
    return _token(tenant_id, ["ADMIN"])


def _tutor_token(tenant_id: uuid.UUID) -> dict[str, str]:
    return _token(tenant_id, ["TUTOR"])


def _coordinador_token(tenant_id: uuid.UUID) -> dict[str, str]:
    return _token(tenant_id, ["COORDINADOR"])


def _alumno_token(tenant_id: uuid.UUID) -> dict[str, str]:
    return _token(tenant_id, ["ALUMNO"])


# ═══════════════════════════════════════════════════════════════
# RBAC — Usuario endpoints require usuarios:gestionar
# ═══════════════════════════════════════════════════════════════


class TestRbacUsuarios:
    """User without usuarios:gestionar gets 403 on all usuario endpoints."""

    async def _create_usuario(self, client: AsyncClient, headers: dict) -> uuid.UUID:
        resp = await client.post(
            f"{USUARIOS_BASE}/",
            json={
                "nombre": "RBAC",
                "apellidos": "User",
                "email": f"rbac.{uuid.uuid4().hex[:8]}@example.com",
            },
            headers=headers,
        )
        return resp.json()["id"]

    async def test_tutor_cannot_list_usuarios(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _tutor_token(tenant_a.id)
        response = await async_client.get(f"{USUARIOS_BASE}/", headers=headers)
        assert response.status_code == 403

    async def test_tutor_cannot_create_usuario(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _tutor_token(tenant_a.id)
        response = await async_client.post(
            f"{USUARIOS_BASE}/",
            json={
                "nombre": "Nope",
                "apellidos": "User",
                "email": "nope@example.com",
            },
            headers=headers,
        )
        assert response.status_code == 403

    async def test_tutor_cannot_get_usuario(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        admin_headers = _admin_token(tenant_a.id)
        user_id = await self._create_usuario(async_client, admin_headers)
        headers = _tutor_token(tenant_a.id)
        response = await async_client.get(
            f"{USUARIOS_BASE}/{user_id}", headers=headers
        )
        assert response.status_code == 403

    async def test_tutor_cannot_update_usuario(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        admin_headers = _admin_token(tenant_a.id)
        user_id = await self._create_usuario(async_client, admin_headers)
        headers = _tutor_token(tenant_a.id)
        response = await async_client.patch(
            f"{USUARIOS_BASE}/{user_id}",
            json={"nombre": "Hack"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_tutor_cannot_deactivate_usuario(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        admin_headers = _admin_token(tenant_a.id)
        user_id = await self._create_usuario(async_client, admin_headers)
        headers = _tutor_token(tenant_a.id)
        response = await async_client.delete(
            f"{USUARIOS_BASE}/{user_id}", headers=headers
        )
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════
# RBAC — Asignacion endpoints require equipos:asignar
# ═══════════════════════════════════════════════════════════════


class TestRbacAsignaciones:
    """User without equipos:asignar gets 403 on all asignacion endpoints."""

    async def test_tutor_cannot_list_asignaciones(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _tutor_token(tenant_a.id)
        response = await async_client.get(f"{ASIGNACIONES_BASE}/", headers=headers)
        assert response.status_code == 403

    async def test_tutor_cannot_create_asignacion(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _tutor_token(tenant_a.id)
        response = await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": str(uuid.uuid4()),
                "rol": "PROFESOR",
                "desde": "2026-01-01",
            },
            headers=headers,
        )
        assert response.status_code == 403

    async def test_tutor_cannot_get_asignacion(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        admin_headers = _admin_token(tenant_a.id)
        # Create user first
        user_resp = await async_client.post(
            f"{USUARIOS_BASE}/",
            json={
                "nombre": "AsigRBAC",
                "apellidos": "User",
                "email": f"asigrbac.{uuid.uuid4().hex[:8]}@example.com",
            },
            headers=admin_headers,
        )
        user_id = user_resp.json()["id"]
        asig_resp = await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": "2026-01-01",
            },
            headers=admin_headers,
        )
        asig_id = asig_resp.json()["id"]
        headers = _tutor_token(tenant_a.id)
        response = await async_client.get(
            f"{ASIGNACIONES_BASE}/{asig_id}", headers=headers
        )
        assert response.status_code == 403

    async def test_tutor_cannot_update_asignacion(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        admin_headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"{USUARIOS_BASE}/",
            json={
                "nombre": "UpdRBAC",
                "apellidos": "User",
                "email": f"updrbac.{uuid.uuid4().hex[:8]}@example.com",
            },
            headers=admin_headers,
        )
        user_id = user_resp.json()["id"]
        asig_resp = await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": "2026-01-01",
            },
            headers=admin_headers,
        )
        asig_id = asig_resp.json()["id"]
        headers = _tutor_token(tenant_a.id)
        response = await async_client.patch(
            f"{ASIGNACIONES_BASE}/{asig_id}",
            json={"rol": "TUTOR"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_tutor_cannot_delete_asignacion(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        admin_headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"{USUARIOS_BASE}/",
            json={
                "nombre": "DelRBAC",
                "apellidos": "User",
                "email": f"delrbac.{uuid.uuid4().hex[:8]}@example.com",
            },
            headers=admin_headers,
        )
        user_id = user_resp.json()["id"]
        asig_resp = await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": "2026-01-01",
            },
            headers=admin_headers,
        )
        asig_id = asig_resp.json()["id"]
        headers = _tutor_token(tenant_a.id)
        response = await async_client.delete(
            f"{ASIGNACIONES_BASE}/{asig_id}", headers=headers
        )
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════
# RBAC — ADMIN can access both routers
# ═══════════════════════════════════════════════════════════════


class TestAdminAccess:
    async def test_admin_can_list_usuarios(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _admin_token(tenant_a.id)
        response = await async_client.get(f"{USUARIOS_BASE}/", headers=headers)
        assert response.status_code == 200

    async def test_admin_can_list_asignaciones(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _admin_token(tenant_a.id)
        response = await async_client.get(f"{ASIGNACIONES_BASE}/", headers=headers)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════
# RBAC — COORDINADOR can access asignaciones but not usuarios
# ═══════════════════════════════════════════════════════════════


class TestCoordinadorAccess:
    async def test_coordinador_cannot_list_usuarios(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _coordinador_token(tenant_a.id)
        response = await async_client.get(f"{USUARIOS_BASE}/", headers=headers)
        assert response.status_code == 403

    async def test_coordinador_can_list_asignaciones(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _coordinador_token(tenant_a.id)
        response = await async_client.get(f"{ASIGNACIONES_BASE}/", headers=headers)
        assert response.status_code == 200

    async def test_coordinador_can_create_asignacion(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _coordinador_token(tenant_a.id)
        admin_headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"{USUARIOS_BASE}/",
            json={
                "nombre": "CoordAsig",
                "apellidos": "User",
                "email": f"coordasig.{uuid.uuid4().hex[:8]}@example.com",
            },
            headers=admin_headers,
        )
        user_id = user_resp.json()["id"]
        response = await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "TUTOR",
                "desde": "2026-01-01",
            },
            headers=headers,
        )
        assert response.status_code == 201


# ═══════════════════════════════════════════════════════════════
# Unauthenticated — 401
# ═══════════════════════════════════════════════════════════════


class TestUnauthenticated:
    async def test_no_token_usuarios_list(
        self, async_client: AsyncClient
    ):
        response = await async_client.get(f"{USUARIOS_BASE}/")
        assert response.status_code == 401

    async def test_no_token_asignaciones_list(
        self, async_client: AsyncClient
    ):
        response = await async_client.get(f"{ASIGNACIONES_BASE}/")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════
# Multi-Tenant Isolation  (7.5)
# ═══════════════════════════════════════════════════════════════


class TestMultiTenant:
    """Tenant A cannot see/modify Tenant B data."""

    async def test_tenant_a_cannot_see_tenant_b_users(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """GIVEN tenant_a and tenant_b each have a user WHEN tenant_a lists THEN only A's user visible."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        await async_client.post(
            f"{USUARIOS_BASE}/",
            json={
                "nombre": "UserA",
                "apellidos": "Only",
                "email": "usera.only@example.com",
            },
            headers=headers_a,
        )
        await async_client.post(
            f"{USUARIOS_BASE}/",
            json={
                "nombre": "UserB",
                "apellidos": "Only",
                "email": "userb.only@example.com",
            },
            headers=headers_b,
        )
        resp_a = await async_client.get(f"{USUARIOS_BASE}/", headers=headers_a)
        emails_a = [u["email"] for u in resp_a.json()]
        assert "usera.only@example.com" in emails_a
        assert "userb.only@example.com" not in emails_a

    async def test_tenant_b_cannot_get_tenant_a_user(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """GIVEN tenant_a has a user WHEN tenant_b tries get THEN 404."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        resp = await async_client.post(
            f"{USUARIOS_BASE}/",
            json={
                "nombre": "TenantA",
                "apellidos": "Secret",
                "email": "tenant.a.secret@example.com",
            },
            headers=headers_a,
        )
        user_id = resp.json()["id"]
        response = await async_client.get(
            f"{USUARIOS_BASE}/{user_id}", headers=headers_b
        )
        assert response.status_code == 404

    async def test_asignacion_referencing_user_from_other_tenant_rejected(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """GIVEN a user in tenant_b WHEN tenant_a tries to create asignacion with that user THEN 404."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        # Create user in tenant_b
        user_b_resp = await async_client.post(
            f"{USUARIOS_BASE}/",
            json={
                "nombre": "UserB",
                "apellidos": "NoAccess",
                "email": "user.b.noaccess@example.com",
            },
            headers=headers_b,
        )
        user_b_id = user_b_resp.json()["id"]
        # Tenant A tries to create asignacion referencing tenant B's user
        response = await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": str(user_b_id),
                "rol": "PROFESOR",
                "desde": "2026-01-01",
            },
            headers=headers_a,
        )
        assert response.status_code == 404

    async def test_tenant_b_cannot_get_tenant_a_asignacion(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """GIVEN tenant_a has an asignacion WHEN tenant_b tries get THEN 404."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        user_resp = await async_client.post(
            f"{USUARIOS_BASE}/",
            json={
                "nombre": "AsigA",
                "apellidos": "Secret",
                "email": "asig.a.secret@example.com",
            },
            headers=headers_a,
        )
        user_id = user_resp.json()["id"]
        asig_resp = await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": "2026-01-01",
            },
            headers=headers_a,
        )
        asig_id = asig_resp.json()["id"]
        response = await async_client.get(
            f"{ASIGNACIONES_BASE}/{asig_id}", headers=headers_b
        )
        assert response.status_code == 404

    async def test_tenant_b_cannot_delete_tenant_a_asignacion(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """GIVEN tenant_a has an asignacion WHEN tenant_b tries delete THEN 404."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        user_resp = await async_client.post(
            f"{USUARIOS_BASE}/",
            json={
                "nombre": "DelAsigA",
                "apellidos": "Secret",
                "email": "delasig.a.secret@example.com",
            },
            headers=headers_a,
        )
        user_id = user_resp.json()["id"]
        asig_resp = await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": "2026-01-01",
            },
            headers=headers_a,
        )
        asig_id = asig_resp.json()["id"]
        response = await async_client.delete(
            f"{ASIGNACIONES_BASE}/{asig_id}", headers=headers_b
        )
        assert response.status_code == 404

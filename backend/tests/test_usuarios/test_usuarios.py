"""Tests for Usuario CRUD, PII encryption, and business rules (C-07)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.tenant import Tenant

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/admin/usuarios"


def _admin_token(tenant_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        roles=["ADMIN"],
    )
    return {"Authorization": f"Bearer {token}"}


def _tutor_token(tenant_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        roles=["TUTOR"],
    )
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════
# Usuario Creation
# ═══════════════════════════════════════════════════════════════


class TestUsuarioCreate:
    async def test_create_usuario_with_pii_encrypted(
        self, async_client: AsyncClient, tenant_a: Tenant, db_session: AsyncSession
    ):
        """WHEN creating a user with PII THEN response has decrypted values AND DB stores encrypted."""
        headers = _admin_token(tenant_a.id)
        payload = {
            "nombre": "Juan",
            "apellidos": "Pérez",
            "email": "juan.perez@example.com",
            "dni": "12345678",
            "cuil": "20-12345678-9",
            "legajo": "LEG-001",
        }
        response = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "juan.perez@example.com"
        assert data["dni"] == "12345678"
        assert data["cuil"] == "20-12345678-9"
        assert data["nombre"] == "Juan"
        assert data["estado"] == "Activa"

        # Verify DB stores encrypted value
        result = await db_session.execute(
            text("SELECT email, email_hash, dni, cuil FROM usuario WHERE id = :uid"),
            {"uid": data["id"]},
        )
        row = result.one()
        assert row.email != "juan.perez@example.com"
        assert row.dni is not None
        assert row.dni != "12345678"
        assert row.cuil is not None
        assert row.cuil != "20-12345678-9"

    async def test_create_duplicate_email_same_tenant(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating two users with same email in same tenant THEN 409."""
        headers = _admin_token(tenant_a.id)
        payload = {
            "nombre": "Primero",
            "apellidos": "User",
            "email": "dupe@example.com",
        }
        resp1 = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert resp1.status_code == 201
        resp2 = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert resp2.status_code == 409

    async def test_create_same_email_different_tenant(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """WHEN creating users with same email in different tenants THEN both succeed."""
        payload = {
            "nombre": "Multi",
            "apellidos": "Tenant",
            "email": "multi@example.com",
        }
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        resp_a = await async_client.post(f"{BASE}/", json=payload, headers=headers_a)
        assert resp_a.status_code == 201
        resp_b = await async_client.post(f"{BASE}/", json=payload, headers=headers_b)
        assert resp_b.status_code == 201

    async def test_create_usuario_without_optional_pii(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating a user with only required fields THEN 201."""
        headers = _admin_token(tenant_a.id)
        payload = {
            "nombre": "María",
            "apellidos": "García",
            "email": "maria.garcia@example.com",
        }
        response = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "María"
        assert data["dni"] is None
        assert data["cuil"] is None
        assert data["cbu"] is None

    async def test_create_usuario_extra_field_rejected(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN sending extra fields THEN 422."""
        headers = _admin_token(tenant_a.id)
        payload = {
            "nombre": "Extra",
            "apellidos": "Field",
            "email": "extra@example.com",
            "extra_field": "xyz",
        }
        response = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert response.status_code == 422

    async def test_create_usuario_unauthenticated(
        self, async_client: AsyncClient
    ):
        """WHEN no auth token THEN 401."""
        payload = {
            "nombre": "No",
            "apellidos": "Auth",
            "email": "noauth@example.com",
        }
        response = await async_client.post(f"{BASE}/", json=payload)
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════
# Usuario Read
# ═══════════════════════════════════════════════════════════════


class TestUsuarioRead:
    async def test_get_usuario_by_id(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN getting a user by ID THEN 200 with matching data."""
        headers = _admin_token(tenant_a.id)
        payload = {
            "nombre": "GetTest",
            "apellidos": "User",
            "email": "gettest@example.com",
        }
        create_resp = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        user_id = create_resp.json()["id"]
        response = await async_client.get(f"{BASE}/{user_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == "gettest@example.com"

    async def test_get_usuario_not_found(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN getting non-existent user THEN 404."""
        headers = _admin_token(tenant_a.id)
        response = await async_client.get(
            f"{BASE}/{uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 404

    async def test_list_usuarios(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN listing usuarios THEN 200 with list."""
        headers = _admin_token(tenant_a.id)
        await async_client.post(
            f"{BASE}/",
            json={"nombre": "List1", "apellidos": "A", "email": "list1@example.com"},
            headers=headers,
        )
        await async_client.post(
            f"{BASE}/",
            json={"nombre": "List2", "apellidos": "B", "email": "list2@example.com"},
            headers=headers,
        )
        response = await async_client.get(f"{BASE}/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    async def test_search_by_email(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN searching by email THEN returns matching user."""
        headers = _admin_token(tenant_a.id)
        await async_client.post(
            f"{BASE}/",
            json={
                "nombre": "Search",
                "apellidos": "User",
                "email": "search.unique@example.com",
            },
            headers=headers,
        )
        response = await async_client.get(
            f"{BASE}/",
            params={"email": "search.unique@example.com"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == "search.unique@example.com"

    async def test_search_by_email_not_found(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN searching by email that doesn't exist THEN empty list."""
        headers = _admin_token(tenant_a.id)
        response = await async_client.get(
            f"{BASE}/",
            params={"email": "nonexistent@example.com"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json() == []


# ═══════════════════════════════════════════════════════════════
# Usuario Update
# ═══════════════════════════════════════════════════════════════


class TestUsuarioUpdate:
    async def test_update_usuario_email(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN updating email THEN email changes in response."""
        headers = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{BASE}/",
            json={
                "nombre": "Email",
                "apellidos": "Update",
                "email": "old.email@example.com",
            },
            headers=headers,
        )
        user_id = resp.json()["id"]
        response = await async_client.patch(
            f"{BASE}/{user_id}",
            json={"email": "new.email@example.com"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["email"] == "new.email@example.com"

    async def test_update_nombre_without_pii(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN updating only nombre THEN nombre changes, PII unchanged."""
        headers = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{BASE}/",
            json={
                "nombre": "Original",
                "apellidos": "Name",
                "email": "name.update@example.com",
                "dni": "87654321",
            },
            headers=headers,
        )
        user_id = resp.json()["id"]
        original_email = resp.json()["email"]
        original_dni = resp.json()["dni"]
        response = await async_client.patch(
            f"{BASE}/{user_id}",
            json={"nombre": "Updated"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["nombre"] == "Updated"
        assert response.json()["email"] == original_email
        assert response.json()["dni"] == original_dni

    async def test_update_usuario_not_found(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN updating non-existent user THEN 404."""
        headers = _admin_token(tenant_a.id)
        response = await async_client.patch(
            f"{BASE}/{uuid.uuid4()}",
            json={"nombre": "Nope"},
            headers=headers,
        )
        assert response.status_code == 404

    async def test_update_usuario_duplicate_email(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN updating to an email that already exists THEN 409."""
        headers = _admin_token(tenant_a.id)
        await async_client.post(
            f"{BASE}/",
            json={
                "nombre": "Existing",
                "apellidos": "User",
                "email": "existing@example.com",
            },
            headers=headers,
        )
        resp = await async_client.post(
            f"{BASE}/",
            json={
                "nombre": "Target",
                "apellidos": "User",
                "email": "target@example.com",
            },
            headers=headers,
        )
        target_id = resp.json()["id"]
        response = await async_client.patch(
            f"{BASE}/{target_id}",
            json={"email": "existing@example.com"},
            headers=headers,
        )
        assert response.status_code == 409


# ═══════════════════════════════════════════════════════════════
# Usuario Deactivate (Soft Delete)
# ═══════════════════════════════════════════════════════════════


class TestUsuarioDeactivate:
    async def test_deactivate_usuario(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN deactivating a user THEN 204 and estado becomes Inactiva."""
        headers = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{BASE}/",
            json={
                "nombre": "Deact",
                "apellidos": "User",
                "email": "deact@example.com",
            },
            headers=headers,
        )
        user_id = resp.json()["id"]
        delete_resp = await async_client.delete(
            f"{BASE}/{user_id}", headers=headers
        )
        assert delete_resp.status_code == 204

        get_resp = await async_client.get(f"{BASE}/{user_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["estado"] == "Inactiva"

    async def test_deactivate_already_inactive(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN deactivating an already inactive user THEN 409."""
        headers = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{BASE}/",
            json={
                "nombre": "Double",
                "apellidos": "Deact",
                "email": "double.deact@example.com",
            },
            headers=headers,
        )
        user_id = resp.json()["id"]
        await async_client.delete(f"{BASE}/{user_id}", headers=headers)
        second = await async_client.delete(f"{BASE}/{user_id}", headers=headers)
        assert second.status_code == 409

    async def test_deactivate_not_found(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN deactivating non-existent user THEN 404."""
        headers = _admin_token(tenant_a.id)
        response = await async_client.delete(
            f"{BASE}/{uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 404

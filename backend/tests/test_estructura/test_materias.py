"""Tests for Materia CRUD and business rules (C-06)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.tenant import Tenant

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/admin/materias"


def _admin_token(tenant_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        roles=["ADMIN"],
    )
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════
# Materia Creation
# ═══════════════════════════════════════════════════════════════


class TestMateriaCreate:
    async def test_create_materia_success(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating a materia with valid data THEN 201 + entity returned."""
        headers = _admin_token(tenant_a.id)
        payload = {"codigo": "MAT101", "nombre": "Matemática I"}
        response = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["codigo"] == "MAT101"
        assert data["nombre"] == "Matemática I"
        assert data["estado"] == "Activa"
        assert "id" in data
        assert "tenant_id" in data

    async def test_create_materia_duplicate_codigo_mismo_tenant(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating materia with duplicate codigo in same tenant THEN 409."""
        headers = _admin_token(tenant_a.id)
        payload = {"codigo": "DUPEMAT", "nombre": "Duplicada"}
        await async_client.post(f"{BASE}/", json=payload, headers=headers)
        response = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert response.status_code == 409

    async def test_create_materia_duplicate_codigo_distinto_tenant(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """WHEN creating materia with same codigo in different tenant THEN 201."""
        payload = {"codigo": "SHAREDMAT", "nombre": "Compartida"}
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        resp_a = await async_client.post(f"{BASE}/", json=payload, headers=headers_a)
        assert resp_a.status_code == 201
        resp_b = await async_client.post(f"{BASE}/", json=payload, headers=headers_b)
        assert resp_b.status_code == 201


# ═══════════════════════════════════════════════════════════════
# Materia Read
# ═══════════════════════════════════════════════════════════════


class TestMateriaRead:
    async def test_get_materia_by_id(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN getting materia by ID THEN 200 with data."""
        headers = _admin_token(tenant_a.id)
        payload = {"codigo": "GETMAT", "nombre": "Get Test"}
        create_resp = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        materia_id = create_resp.json()["id"]
        response = await async_client.get(f"{BASE}/{materia_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["codigo"] == "GETMAT"

    async def test_list_materias(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN listing materias THEN 200 with list."""
        headers = _admin_token(tenant_a.id)
        await async_client.post(
            f"{BASE}/", json={"codigo": "ML1", "nombre": "List1"}, headers=headers
        )
        await async_client.post(
            f"{BASE}/", json={"codigo": "ML2", "nombre": "List2"}, headers=headers
        )
        response = await async_client.get(f"{BASE}/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    async def test_get_materia_otro_tenant(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """WHEN getting materia from another tenant THEN 404."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        resp = await async_client.post(
            f"{BASE}/", json={"codigo": "OTROMAT", "nombre": "Otro Tenant"}, headers=headers_a
        )
        materia_id = resp.json()["id"]
        response = await async_client.get(f"{BASE}/{materia_id}", headers=headers_b)
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════
# Materia Update
# ═══════════════════════════════════════════════════════════════


class TestMateriaUpdate:
    async def test_update_materia_nombre(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN updating materia nombre THEN 200."""
        headers = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{BASE}/", json={"codigo": "UPDMAT", "nombre": "Original"}, headers=headers
        )
        materia_id = resp.json()["id"]
        response = await async_client.put(
            f"{BASE}/{materia_id}",
            json={"nombre": "Actualizado"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["nombre"] == "Actualizado"

    async def test_desactivar_materia(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN desactivando materia THEN 200."""
        headers = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{BASE}/",
            json={"codigo": "DESCMAT", "nombre": "Desactivar"},
            headers=headers,
        )
        materia_id = resp.json()["id"]
        response = await async_client.put(
            f"{BASE}/{materia_id}",
            json={"estado": "Inactiva"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["estado"] == "Inactiva"


# ═══════════════════════════════════════════════════════════════
# Materia Soft Delete
# ═══════════════════════════════════════════════════════════════


class TestMateriaDelete:
    async def test_delete_materia(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN deleting a materia THEN 204 and soft-deleted."""
        headers = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{BASE}/", json={"codigo": "DELMAT", "nombre": "To Delete"}, headers=headers
        )
        materia_id = resp.json()["id"]

        delete_resp = await async_client.delete(
            f"{BASE}/{materia_id}", headers=headers
        )
        assert delete_resp.status_code == 204

        get_resp = await async_client.get(f"{BASE}/{materia_id}", headers=headers)
        assert get_resp.status_code == 404

        list_resp = await async_client.get(f"{BASE}/", headers=headers)
        ids = [m["id"] for m in list_resp.json()]
        assert str(materia_id) not in ids

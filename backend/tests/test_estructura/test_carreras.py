"""Tests for Carrera CRUD and business rules (C-06)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.tenant import Tenant

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/admin/carreras"
COHORTES_BASE = "/api/v1/admin/cohortes"


def _admin_token(tenant_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        roles=["ADMIN"],
    )
    return {"Authorization": f"Bearer {token}"}


def _alumno_token(tenant_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        roles=["ALUMNO"],
    )
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════
# Carrera Creation
# ═══════════════════════════════════════════════════════════════


class TestCarreraCreate:
    async def test_create_carrera_success(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating a carrera with valid data THEN 201 + entity returned."""
        headers = _admin_token(tenant_a.id)
        payload = {"codigo": "TUPAD", "nombre": "Tecnicatura Universitaria en Programación"}
        response = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["codigo"] == "TUPAD"
        assert data["nombre"] == "Tecnicatura Universitaria en Programación"
        assert data["estado"] == "Activa"
        assert "id" in data
        assert "tenant_id" in data

    async def test_create_carrera_duplicate_codigo_mismo_tenant(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating carrera with duplicate codigo in same tenant THEN 409."""
        headers = _admin_token(tenant_a.id)
        payload = {"codigo": "DUPE", "nombre": "Duplicada"}
        await async_client.post(f"{BASE}/", json=payload, headers=headers)
        response = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert response.status_code == 409

    async def test_create_carrera_duplicate_codigo_distinto_tenant(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """WHEN creating carrera with same codigo in different tenant THEN 201."""
        payload = {"codigo": "SHARED", "nombre": "Compartida"}
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        resp_a = await async_client.post(f"{BASE}/", json=payload, headers=headers_a)
        assert resp_a.status_code == 201
        resp_b = await async_client.post(f"{BASE}/", json=payload, headers=headers_b)
        assert resp_b.status_code == 201


# ═══════════════════════════════════════════════════════════════
# Carrera Read
# ═══════════════════════════════════════════════════════════════


class TestCarreraRead:
    async def test_get_carrera_by_id(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN getting carrera by ID THEN 200 with data."""
        headers = _admin_token(tenant_a.id)
        payload = {"codigo": "GET01", "nombre": "Get Test"}
        create_resp = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        carrera_id = create_resp.json()["id"]
        response = await async_client.get(f"{BASE}/{carrera_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["codigo"] == "GET01"

    async def test_list_carreras(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN listing carreras THEN 200 with list."""
        headers = _admin_token(tenant_a.id)
        await async_client.post(
            f"{BASE}/", json={"codigo": "L1", "nombre": "List1"}, headers=headers
        )
        await async_client.post(
            f"{BASE}/", json={"codigo": "L2", "nombre": "List2"}, headers=headers
        )
        response = await async_client.get(f"{BASE}/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    async def test_get_carrera_otro_tenant(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """WHEN getting carrera from another tenant THEN 404."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        resp = await async_client.post(
            f"{BASE}/", json={"codigo": "OTRO", "nombre": "Otro Tenant"}, headers=headers_a
        )
        carrera_id = resp.json()["id"]
        response = await async_client.get(f"{BASE}/{carrera_id}", headers=headers_b)
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════
# Carrera Update
# ═══════════════════════════════════════════════════════════════


class TestCarreraUpdate:
    async def test_update_carrera_nombre(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN updating carrera nombre THEN 200."""
        headers = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{BASE}/", json={"codigo": "UPD", "nombre": "Original"}, headers=headers
        )
        carrera_id = resp.json()["id"]
        response = await async_client.put(
            f"{BASE}/{carrera_id}",
            json={"nombre": "Actualizado"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["nombre"] == "Actualizado"

    async def test_desactivar_carrera_sin_cohortes(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN desactivando carrera sin cohortes activas THEN 200."""
        headers = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{BASE}/", json={"codigo": "DESACT", "nombre": "Desactivar"}, headers=headers
        )
        carrera_id = resp.json()["id"]
        response = await async_client.put(
            f"{BASE}/{carrera_id}",
            json={"estado": "Inactiva"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["estado"] == "Inactiva"

    async def test_reactivar_carrera(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN reactivando carrera THEN 200."""
        headers = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{BASE}/", json={"codigo": "REACT", "nombre": "Reactivar"}, headers=headers
        )
        carrera_id = resp.json()["id"]
        await async_client.put(
            f"{BASE}/{carrera_id}",
            json={"estado": "Inactiva"},
            headers=headers,
        )
        response = await async_client.put(
            f"{BASE}/{carrera_id}",
            json={"estado": "Activa"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["estado"] == "Activa"

    async def test_desactivar_carrera_con_cohortes_activas(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN desactivando carrera con cohortes activas THEN 409."""
        headers = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{BASE}/",
            json={"codigo": "CONCOH", "nombre": "Con Cohorte"},
            headers=headers,
        )
        carrera_id = resp.json()["id"]

        hoy = "2026-01-01"
        cohorte_payload = {
            "carrera_id": str(carrera_id),
            "nombre": "Cohorte Activa",
            "anio": 2026,
            "vig_desde": hoy,
        }
        await async_client.post(
            f"{COHORTES_BASE}/", json=cohorte_payload, headers=headers
        )

        response = await async_client.put(
            f"{BASE}/{carrera_id}",
            json={"estado": "Inactiva"},
            headers=headers,
        )
        assert response.status_code == 409


# ═══════════════════════════════════════════════════════════════
# Carrera Soft Delete
# ═══════════════════════════════════════════════════════════════


class TestCarreraDelete:
    async def test_delete_carrera(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN deleting a carrera THEN 204 and soft-deleted."""
        headers = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{BASE}/", json={"codigo": "DEL01", "nombre": "To Delete"}, headers=headers
        )
        carrera_id = resp.json()["id"]

        delete_resp = await async_client.delete(
            f"{BASE}/{carrera_id}", headers=headers
        )
        assert delete_resp.status_code == 204

        get_resp = await async_client.get(f"{BASE}/{carrera_id}", headers=headers)
        assert get_resp.status_code == 404

        list_resp = await async_client.get(f"{BASE}/", headers=headers)
        ids = [c["id"] for c in list_resp.json()]
        assert str(carrera_id) not in ids

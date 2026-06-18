"""Tests for Cohorte CRUD and business rules (C-06)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.tenant import Tenant

pytestmark = pytest.mark.asyncio

CARRERAS_BASE = "/api/v1/admin/carreras"
COHORTES_BASE = "/api/v1/admin/cohortes"


def _admin_token(tenant_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        roles=["ADMIN"],
    )
    return {"Authorization": f"Bearer {token}"}


async def _crear_carrera_activa(
    client: AsyncClient, headers: dict, codigo: str, nombre: str
) -> dict:
    resp = await client.post(
        f"{CARRERAS_BASE}/",
        json={"codigo": codigo, "nombre": nombre},
        headers=headers,
    )
    return resp.json()


# ═══════════════════════════════════════════════════════════════
# Cohorte Creation
# ═══════════════════════════════════════════════════════════════


class TestCohorteCreate:
    async def test_create_cohorte_success(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating a cohorte for an active carrera THEN 201."""
        headers = _admin_token(tenant_a.id)
        carrera = await _crear_carrera_activa(
            async_client, headers, "COH-C", "Carrera Cohorte"
        )
        payload = {
            "carrera_id": str(carrera["id"]),
            "nombre": "2026 A",
            "anio": 2026,
            "vig_desde": "2026-03-01",
        }
        response = await async_client.post(f"{COHORTES_BASE}/", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "2026 A"
        assert data["anio"] == 2026
        assert data["estado"] == "Activa"
        assert "id" in data
        assert "tenant_id" in data

    async def test_create_cohorte_carrera_inactiva(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating cohorte for inactive carrera THEN 422."""
        headers = _admin_token(tenant_a.id)
        carrera = await _crear_carrera_activa(
            async_client, headers, "COH-INACT", "Inactiva"
        )
        await async_client.put(
            f"{CARRERAS_BASE}/{carrera['id']}",
            json={"estado": "Inactiva"},
            headers=headers,
        )
        payload = {
            "carrera_id": str(carrera["id"]),
            "nombre": "No Debe Crearse",
            "anio": 2026,
            "vig_desde": "2026-03-01",
        }
        response = await async_client.post(f"{COHORTES_BASE}/", json=payload, headers=headers)
        assert response.status_code == 422

    async def test_create_cohorte_duplicate_nombre_misma_carrera(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating cohorte with duplicate nombre in same carrera THEN 409."""
        headers = _admin_token(tenant_a.id)
        carrera = await _crear_carrera_activa(
            async_client, headers, "COH-DUP", "Dupe"
        )
        payload = {
            "carrera_id": str(carrera["id"]),
            "nombre": "Repetido",
            "anio": 2026,
            "vig_desde": "2026-03-01",
        }
        await async_client.post(f"{COHORTES_BASE}/", json=payload, headers=headers)
        response = await async_client.post(f"{COHORTES_BASE}/", json=payload, headers=headers)
        assert response.status_code == 409

    async def test_create_cohorte_vig_hasta_in_past(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating cohorte with vig_hasta in the past THEN 201 (allowed)."""
        headers = _admin_token(tenant_a.id)
        carrera = await _crear_carrera_activa(
            async_client, headers, "COH-PAST", "Pasado"
        )
        payload = {
            "carrera_id": str(carrera["id"]),
            "nombre": "Vig Pasada",
            "anio": 2024,
            "vig_desde": "2024-03-01",
            "vig_hasta": "2024-12-31",
        }
        response = await async_client.post(f"{COHORTES_BASE}/", json=payload, headers=headers)
        assert response.status_code == 201
        assert response.json()["vig_hasta"] == "2024-12-31"


# ═══════════════════════════════════════════════════════════════
# Cohorte Read
# ═══════════════════════════════════════════════════════════════


class TestCohorteRead:
    async def test_get_cohorte_by_id(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN getting cohorte by ID THEN 200 with data."""
        headers = _admin_token(tenant_a.id)
        carrera = await _crear_carrera_activa(
            async_client, headers, "COH-RD", "Read"
        )
        payload = {
            "carrera_id": str(carrera["id"]),
            "nombre": "Get Me",
            "anio": 2026,
            "vig_desde": "2026-03-01",
        }
        create_resp = await async_client.post(
            f"{COHORTES_BASE}/", json=payload, headers=headers
        )
        coh_id = create_resp.json()["id"]
        response = await async_client.get(f"{COHORTES_BASE}/{coh_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["nombre"] == "Get Me"

    async def test_list_cohortes_with_carrera_filter(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN listing cohortes with carrera_id filter THEN 200."""
        headers = _admin_token(tenant_a.id)
        carrera = await _crear_carrera_activa(
            async_client, headers, "COH-LST", "List"
        )
        payload = {
            "carrera_id": str(carrera["id"]),
            "nombre": "Filtrable",
            "anio": 2026,
            "vig_desde": "2026-03-01",
        }
        await async_client.post(f"{COHORTES_BASE}/", json=payload, headers=headers)
        response = await async_client.get(
            f"{COHORTES_BASE}/?carrera_id={carrera['id']}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_get_cohorte_otro_tenant(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """WHEN getting cohorte from another tenant THEN 404."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        carrera = await _crear_carrera_activa(
            async_client, headers_a, "COH-OTRO", "Otro"
        )
        payload = {
            "carrera_id": str(carrera["id"]),
            "nombre": "Secreta",
            "anio": 2026,
            "vig_desde": "2026-03-01",
        }
        create_resp = await async_client.post(
            f"{COHORTES_BASE}/", json=payload, headers=headers_a
        )
        coh_id = create_resp.json()["id"]
        response = await async_client.get(
            f"{COHORTES_BASE}/{coh_id}", headers=headers_b
        )
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════
# Cohorte Update
# ═══════════════════════════════════════════════════════════════


class TestCohorteUpdate:
    async def test_update_cohorte_nombre(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN updating cohorte nombre THEN 200."""
        headers = _admin_token(tenant_a.id)
        carrera = await _crear_carrera_activa(
            async_client, headers, "COH-UPD", "Update"
        )
        payload = {
            "carrera_id": str(carrera["id"]),
            "nombre": "Original",
            "anio": 2026,
            "vig_desde": "2026-03-01",
        }
        create_resp = await async_client.post(
            f"{COHORTES_BASE}/", json=payload, headers=headers
        )
        coh_id = create_resp.json()["id"]
        response = await async_client.put(
            f"{COHORTES_BASE}/{coh_id}",
            json={"nombre": "Actualizado"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["nombre"] == "Actualizado"

    async def test_change_cohorte_to_inactive_carrera(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN changing cohorte to an inactive carrera THEN 422."""
        headers = _admin_token(tenant_a.id)
        carrera_a = await _crear_carrera_activa(
            async_client, headers, "COH-CA", "Carrera Activa"
        )
        carrera_b = await _crear_carrera_activa(
            async_client, headers, "COH-CI", "Carrera Inactiva"
        )
        await async_client.put(
            f"{CARRERAS_BASE}/{carrera_b['id']}",
            json={"estado": "Inactiva"},
            headers=headers,
        )
        payload = {
            "carrera_id": str(carrera_a["id"]),
            "nombre": "Migrar",
            "anio": 2026,
            "vig_desde": "2026-03-01",
        }
        create_resp = await async_client.post(
            f"{COHORTES_BASE}/", json=payload, headers=headers
        )
        coh_id = create_resp.json()["id"]
        response = await async_client.put(
            f"{COHORTES_BASE}/{coh_id}",
            json={"carrera_id": str(carrera_b["id"])},
            headers=headers,
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Cohorte Soft Delete
# ═══════════════════════════════════════════════════════════════


class TestCohorteDelete:
    async def test_delete_cohorte(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN deleting a cohorte THEN 204 and soft-deleted."""
        headers = _admin_token(tenant_a.id)
        carrera = await _crear_carrera_activa(
            async_client, headers, "COH-DEL", "Delete"
        )
        payload = {
            "carrera_id": str(carrera["id"]),
            "nombre": "Delete Me",
            "anio": 2026,
            "vig_desde": "2026-03-01",
        }
        create_resp = await async_client.post(
            f"{COHORTES_BASE}/", json=payload, headers=headers
        )
        coh_id = create_resp.json()["id"]

        delete_resp = await async_client.delete(
            f"{COHORTES_BASE}/{coh_id}", headers=headers
        )
        assert delete_resp.status_code == 204

        get_resp = await async_client.get(f"{COHORTES_BASE}/{coh_id}", headers=headers)
        assert get_resp.status_code == 404

        list_resp = await async_client.get(f"{COHORTES_BASE}/", headers=headers)
        ids = [c["id"] for c in list_resp.json()]
        assert str(coh_id) not in ids

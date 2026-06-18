"""Tests for RBAC, validation, and multi-tenant isolation for estructura endpoints (C-06)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.tenant import Tenant

pytestmark = pytest.mark.asyncio

CARRERAS_BASE = "/api/v1/admin/carreras"
COHORTES_BASE = "/api/v1/admin/cohortes"
MATERIAS_BASE = "/api/v1/admin/materias"


def _alumno_token(tenant_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        roles=["ALUMNO"],
    )
    return {"Authorization": f"Bearer {token}"}


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
# RBAC — user without estructura:gestionar receives 403
# ═══════════════════════════════════════════════════════════════


class TestRbac:
    """User with ALUMNO role (no permissions) gets 403 on all estructura endpoints."""

    async def test_alumno_cannot_create_carrera(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _alumno_token(tenant_a.id)
        response = await async_client.post(
            f"{CARRERAS_BASE}/",
            json={"codigo": "NOPE", "nombre": "No"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_alumno_cannot_list_carreras(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _alumno_token(tenant_a.id)
        response = await async_client.get(f"{CARRERAS_BASE}/", headers=headers)
        assert response.status_code == 403

    async def test_alumno_cannot_get_carrera(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers_admin = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{CARRERAS_BASE}/",
            json={"codigo": "RBAC01", "nombre": "RBAC"},
            headers=headers_admin,
        )
        carrera_id = resp.json()["id"]
        headers = _alumno_token(tenant_a.id)
        response = await async_client.get(
            f"{CARRERAS_BASE}/{carrera_id}", headers=headers
        )
        assert response.status_code == 403

    async def test_alumno_cannot_update_carrera(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers_admin = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{CARRERAS_BASE}/",
            json={"codigo": "RBAC02", "nombre": "RBAC"},
            headers=headers_admin,
        )
        carrera_id = resp.json()["id"]
        headers = _alumno_token(tenant_a.id)
        response = await async_client.put(
            f"{CARRERAS_BASE}/{carrera_id}",
            json={"nombre": "Hack"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_alumno_cannot_delete_carrera(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers_admin = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{CARRERAS_BASE}/",
            json={"codigo": "RBAC03", "nombre": "RBAC"},
            headers=headers_admin,
        )
        carrera_id = resp.json()["id"]
        headers = _alumno_token(tenant_a.id)
        response = await async_client.delete(
            f"{CARRERAS_BASE}/{carrera_id}", headers=headers
        )
        assert response.status_code == 403

    async def test_alumno_cannot_create_cohorte(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _alumno_token(tenant_a.id)
        response = await async_client.post(
            f"{COHORTES_BASE}/",
            json={
                "carrera_id": str(uuid.uuid4()),
                "nombre": "Nope",
                "anio": 2026,
                "vig_desde": "2026-03-01",
            },
            headers=headers,
        )
        assert response.status_code == 403

    async def test_alumno_cannot_list_cohortes(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _alumno_token(tenant_a.id)
        response = await async_client.get(f"{COHORTES_BASE}/", headers=headers)
        assert response.status_code == 403

    async def test_alumno_cannot_create_materia(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _alumno_token(tenant_a.id)
        response = await async_client.post(
            f"{MATERIAS_BASE}/",
            json={"codigo": "NOPE", "nombre": "No"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_alumno_cannot_list_materias(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _alumno_token(tenant_a.id)
        response = await async_client.get(f"{MATERIAS_BASE}/", headers=headers)
        assert response.status_code == 403

    async def test_alumno_cannot_update_materia(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers_admin = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{MATERIAS_BASE}/",
            json={"codigo": "RBACMAT", "nombre": "RBAC"},
            headers=headers_admin,
        )
        materia_id = resp.json()["id"]
        headers = _alumno_token(tenant_a.id)
        response = await async_client.put(
            f"{MATERIAS_BASE}/{materia_id}",
            json={"nombre": "Hack"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_alumno_cannot_delete_materia(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers_admin = _admin_token(tenant_a.id)
        resp = await async_client.post(
            f"{MATERIAS_BASE}/",
            json={"codigo": "RBACMAT2", "nombre": "RBAC"},
            headers=headers_admin,
        )
        materia_id = resp.json()["id"]
        headers = _alumno_token(tenant_a.id)
        response = await async_client.delete(
            f"{MATERIAS_BASE}/{materia_id}", headers=headers
        )
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════
# Validation — extra fields rejected with 422
# ═══════════════════════════════════════════════════════════════


class TestValidacion:
    async def test_extra_field_on_carrera_create_rejected(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN sending extra fields to carrera create THEN 422."""
        headers = _admin_token(tenant_a.id)
        response = await async_client.post(
            f"{CARRERAS_BASE}/",
            json={"codigo": "EXTRA", "nombre": "Test", "extra_field": "xyz"},
            headers=headers,
        )
        assert response.status_code == 422

    async def test_extra_field_on_cohorte_create_rejected(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN sending extra fields to cohorte create THEN 422."""
        headers = _admin_token(tenant_a.id)
        response = await async_client.post(
            f"{COHORTES_BASE}/",
            json={
                "carrera_id": str(uuid.uuid4()),
                "nombre": "Test",
                "anio": 2026,
                "vig_desde": "2026-03-01",
                "extra_field": "xyz",
            },
            headers=headers,
        )
        assert response.status_code == 422

    async def test_extra_field_on_materia_create_rejected(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN sending extra fields to materia create THEN 422."""
        headers = _admin_token(tenant_a.id)
        response = await async_client.post(
            f"{MATERIAS_BASE}/",
            json={"codigo": "EXTRA", "nombre": "Test", "extra_field": "xyz"},
            headers=headers,
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Multi-Tenant Isolation
# ═══════════════════════════════════════════════════════════════


class TestMultiTenant:
    """Tenant A cannot see/modify Tenant B data in any estructura endpoint."""

    async def test_tenant_b_list_empty_for_tenant_a_carreras(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """GIVEN tenant_a has carreras WHEN tenant_b lists THEN empty."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        await async_client.post(
            f"{CARRERAS_BASE}/",
            json={"codigo": "TNA", "nombre": "Solo A"},
            headers=headers_a,
        )
        resp_b = await async_client.get(f"{CARRERAS_BASE}/", headers=headers_b)
        b_codigos = [c["codigo"] for c in resp_b.json()]
        assert "TNA" not in b_codigos

    async def test_tenant_b_cannot_get_tenant_a_carrera(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """GIVEN tenant_a has a carrera WHEN tenant_b tries get THEN 404."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        resp = await async_client.post(
            f"{CARRERAS_BASE}/",
            json={"codigo": "TNAGET", "nombre": "Solo A"},
            headers=headers_a,
        )
        carrera_id = resp.json()["id"]
        response = await async_client.get(
            f"{CARRERAS_BASE}/{carrera_id}", headers=headers_b
        )
        assert response.status_code == 404

    async def test_tenant_b_cannot_update_tenant_a_carrera(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """GIVEN tenant_a has a carrera WHEN tenant_b tries update THEN 404."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        resp = await async_client.post(
            f"{CARRERAS_BASE}/",
            json={"codigo": "TNAUPD", "nombre": "Solo A"},
            headers=headers_a,
        )
        carrera_id = resp.json()["id"]
        response = await async_client.put(
            f"{CARRERAS_BASE}/{carrera_id}",
            json={"nombre": "Hacked"},
            headers=headers_b,
        )
        assert response.status_code == 404

    async def test_tenant_b_cannot_delete_tenant_a_materia(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """GIVEN tenant_a has a materia WHEN tenant_b tries delete THEN 404."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        resp = await async_client.post(
            f"{MATERIAS_BASE}/",
            json={"codigo": "TNADEL", "nombre": "Solo A"},
            headers=headers_a,
        )
        materia_id = resp.json()["id"]
        response = await async_client.delete(
            f"{MATERIAS_BASE}/{materia_id}", headers=headers_b
        )
        assert response.status_code == 404

    async def test_tenant_b_list_empty_for_tenant_a_materias(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """GIVEN tenant_a has materias WHEN tenant_b lists THEN empty."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        await async_client.post(
            f"{MATERIAS_BASE}/",
            json={"codigo": "TNAMAT", "nombre": "Solo A"},
            headers=headers_a,
        )
        resp_b = await async_client.get(f"{MATERIAS_BASE}/", headers=headers_b)
        b_codigos = [m["codigo"] for m in resp_b.json()]
        assert "TNAMAT" not in b_codigos

    async def test_tenant_b_cannot_get_tenant_a_cohorte(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """GIVEN tenant_a has a cohorte WHEN tenant_b tries get THEN 404."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        carrera = await _crear_carrera_activa(
            async_client, headers_a, "TNACOH", "Solo A"
        )
        payload = {
            "carrera_id": str(carrera["id"]),
            "nombre": "Cohorte Secreta",
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

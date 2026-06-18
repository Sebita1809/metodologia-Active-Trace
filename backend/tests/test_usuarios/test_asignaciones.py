"""Tests for Asignacion CRUD, validation rules, and vigencia (C-07)."""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.tenant import Tenant

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/asignaciones"


def _admin_token(tenant_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        roles=["ADMIN"],
    )
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════
# Asignacion Creation
# ═══════════════════════════════════════════════════════════════


class TestAsignacionCreate:
    async def test_create_asignacion_valid(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating a valid asignacion THEN 201 with estado_vigencia."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Asig",
                "apellidos": "User",
                "email": "asig.user@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        payload = {
            "usuario_id": str(user_id),
            "rol": "PROFESOR",
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
        }
        response = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["rol"] == "PROFESOR"
        assert data["estado_vigencia"] in ("vigente", "vencida")
        assert "id" in data
        assert data["comisiones"] == []

    async def test_create_asignacion_without_academic_context(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating asignacion without materia/carrera (global role) THEN 201."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Global",
                "apellidos": "Role",
                "email": "global.role@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        payload = {
            "usuario_id": str(user_id),
            "rol": "ADMIN",
            "desde": "2026-01-01",
        }
        response = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert response.status_code == 201
        assert response.json()["materia_id"] is None
        assert response.json()["carrera_id"] is None

    async def test_create_asignacion_inactive_user(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating asignacion for inactive user THEN 422."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Inactive",
                "apellidos": "User",
                "email": "inactive.asig@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        await async_client.delete(f"/api/v1/admin/usuarios/{user_id}", headers=headers)
        payload = {
            "usuario_id": str(user_id),
            "rol": "PROFESOR",
            "desde": "2026-01-01",
        }
        response = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert response.status_code == 422
        assert "inactive" in response.json()["detail"].lower()

    async def test_create_asignacion_desde_mayor_que_hasta(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN creating asignacion with desde > hasta THEN 422."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Bad",
                "apellidos": "Dates",
                "email": "bad.dates@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        payload = {
            "usuario_id": str(user_id),
            "rol": "PROFESOR",
            "desde": "2026-12-31",
            "hasta": "2026-01-01",
        }
        response = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert response.status_code == 422

    async def test_create_asignacion_responsable_otro_tenant(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """WHEN creating asignacion with responsable from another tenant THEN 422."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        # Create a user in tenant_b to use as responsable
        resp_b = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Other",
                "apellidos": "Tenant",
                "email": "other.tenant@example.com",
            },
            headers=headers_b,
        )
        responsable_id = resp_b.json()["id"]
        # Create user in tenant_a for the asignacion
        resp_a = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Main",
                "apellidos": "User",
                "email": "main.user@example.com",
            },
            headers=headers_a,
        )
        user_id = resp_a.json()["id"]
        payload = {
            "usuario_id": str(user_id),
            "rol": "PROFESOR",
            "desde": "2026-01-01",
            "responsable_id": str(responsable_id),
        }
        response = await async_client.post(f"{BASE}/", json=payload, headers=headers_a)
        assert response.status_code == 422

    async def test_create_asignacion_extra_field_rejected(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN sending extra fields THEN 422."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Extra",
                "apellidos": "F",
                "email": "extra.f@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        payload = {
            "usuario_id": str(user_id),
            "rol": "PROFESOR",
            "desde": "2026-01-01",
            "extra_field": "xyz",
        }
        response = await async_client.post(f"{BASE}/", json=payload, headers=headers)
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Asignacion Read / List
# ═══════════════════════════════════════════════════════════════


class TestAsignacionRead:
    async def test_get_asignacion_by_id(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN getting asignacion by ID THEN 200."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Get",
                "apellidos": "Asig",
                "email": "get.asig@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        create_resp = await async_client.post(
            f"{BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "TUTOR",
                "desde": "2026-01-01",
            },
            headers=headers,
        )
        asig_id = create_resp.json()["id"]
        response = await async_client.get(f"{BASE}/{asig_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["rol"] == "TUTOR"

    async def test_get_asignacion_not_found(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN getting non-existent asignacion THEN 404."""
        headers = _admin_token(tenant_a.id)
        response = await async_client.get(
            f"{BASE}/{uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 404

    async def test_list_by_usuario(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN listing by usuario_id THEN returns that user's asignaciones."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "ListBy",
                "apellidos": "User",
                "email": "listby@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        await async_client.post(
            f"{BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": "2026-01-01",
            },
            headers=headers,
        )
        await async_client.post(
            f"{BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "TUTOR",
                "desde": "2026-02-01",
            },
            headers=headers,
        )
        response = await async_client.get(
            f"{BASE}/",
            params={"usuario_id": str(user_id)},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        roles = {a["rol"] for a in data}
        assert roles == {"PROFESOR", "TUTOR"}

    async def test_list_solo_vigentes(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN filtering solo_vigentes THEN only current asignaciones."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Vigencia",
                "apellidos": "Test",
                "email": "vigencia.test@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        past_year = date.today().year - 2
        # Create a vencida asignacion
        await async_client.post(
            f"{BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": f"{past_year}-01-01",
                "hasta": f"{past_year}-06-30",
            },
            headers=headers,
        )
        response = await async_client.get(
            f"{BASE}/",
            params={"usuario_id": str(user_id), "solo_vigentes": "true"},
            headers=headers,
        )
        assert response.status_code == 200
        vencidas = [a for a in response.json() if a["estado_vigencia"] == "vencida"]
        assert len(vencidas) == 0


# ═══════════════════════════════════════════════════════════════
# Asignacion Estado Vigencia
# ═══════════════════════════════════════════════════════════════


class TestEstadoVigencia:
    async def test_asignacion_vigente(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN asignacion has desde in past and hasta in future THEN vigente."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Vigente",
                "apellidos": "User",
                "email": "vigente.user@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        future = date.today() + timedelta(days=365)
        past = date.today() - timedelta(days=30)
        resp = await async_client.post(
            f"{BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": past.isoformat(),
                "hasta": future.isoformat(),
            },
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["estado_vigencia"] == "vigente"

    async def test_asignacion_vencida(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN asignacion has hasta in the past THEN vencida."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Vencida",
                "apellidos": "User",
                "email": "vencida.user@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        past_year = date.today().year - 2
        resp = await async_client.post(
            f"{BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": f"{past_year}-01-01",
                "hasta": f"{past_year}-06-30",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["estado_vigencia"] == "vencida"

    async def test_asignacion_sin_hasta_vigente(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN asignacion has no hasta date THEN always vigente."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "SinHasta",
                "apellidos": "User",
                "email": "sinhasta@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        past = date.today() - timedelta(days=30)
        resp = await async_client.post(
            f"{BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": past.isoformat(),
            },
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["estado_vigencia"] == "vigente"

    async def test_asignacion_futura_vencida(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN asignacion has desde in the future THEN vencida."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Futura",
                "apellidos": "User",
                "email": "futura.user@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        future = date.today() + timedelta(days=30)
        resp = await async_client.post(
            f"{BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": future.isoformat(),
            },
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["estado_vigencia"] == "vencida"


# ═══════════════════════════════════════════════════════════════
# Asignacion Soft Delete
# ═══════════════════════════════════════════════════════════════


class TestAsignacionDelete:
    async def test_soft_delete_asignacion(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN deleting an asignacion THEN 204 and GET returns 404."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Del",
                "apellidos": "Asig",
                "email": "del.asig@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        create_resp = await async_client.post(
            f"{BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": "2026-01-01",
            },
            headers=headers,
        )
        asig_id = create_resp.json()["id"]
        delete_resp = await async_client.delete(
            f"{BASE}/{asig_id}", headers=headers
        )
        assert delete_resp.status_code == 204
        get_resp = await async_client.get(f"{BASE}/{asig_id}", headers=headers)
        assert get_resp.status_code == 404

    async def test_delete_not_found(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN deleting non-existent asignacion THEN 404."""
        headers = _admin_token(tenant_a.id)
        response = await async_client.delete(
            f"{BASE}/{uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════
# Asignacion Update
# ═══════════════════════════════════════════════════════════════


class TestAsignacionUpdate:
    async def test_update_asignacion_rol(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN updating rol THEN it changes."""
        headers = _admin_token(tenant_a.id)
        user_resp = await async_client.post(
            f"/api/v1/admin/usuarios/",
            json={
                "nombre": "Upd",
                "apellidos": "Asig",
                "email": "upd.asig@example.com",
            },
            headers=headers,
        )
        user_id = user_resp.json()["id"]
        create_resp = await async_client.post(
            f"{BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": "2026-01-01",
            },
            headers=headers,
        )
        asig_id = create_resp.json()["id"]
        response = await async_client.patch(
            f"{BASE}/{asig_id}",
            json={"rol": "TUTOR"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["rol"] == "TUTOR"

    async def test_update_not_found(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN updating non-existent asignacion THEN 404."""
        headers = _admin_token(tenant_a.id)
        response = await async_client.patch(
            f"{BASE}/{uuid.uuid4()}",
            json={"rol": "TUTOR"},
            headers=headers,
        )
        assert response.status_code == 404

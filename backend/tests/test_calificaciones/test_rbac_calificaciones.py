"""Tests for RBAC and multi-tenant isolation for calificaciones endpoints (C-10)."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.tenant import Tenant

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/calificaciones"


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


class TestRbacCalificaciones:
    """Users without calificaciones:importar permission receive 403."""

    async def test_alumno_cannot_preview(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _alumno_token(tenant_a.id)
        response = await async_client.post(
            f"{BASE}/import/preview",
            headers=headers,
        )
        assert response.status_code == 403

    async def test_alumno_cannot_confirm(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _alumno_token(tenant_a.id)
        response = await async_client.post(
            f"{BASE}/import/confirm",
            json={},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_alumno_cannot_list(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _alumno_token(tenant_a.id)
        mid = uuid.uuid4()
        cid = uuid.uuid4()
        response = await async_client.get(
            f"{BASE}/{mid}/{cid}",
            headers=headers,
        )
        assert response.status_code == 403

    async def test_alumno_cannot_clear(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _alumno_token(tenant_a.id)
        mid = uuid.uuid4()
        cid = uuid.uuid4()
        response = await async_client.delete(
            f"{BASE}/{mid}/{cid}",
            headers=headers,
        )
        assert response.status_code == 403

    async def test_alumno_cannot_update_umbral(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _alumno_token(tenant_a.id)
        response = await async_client.put(
            f"{BASE}/umbral",
            json={},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_admin_can_preview_no_file(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _admin_token(tenant_a.id)
        response = await async_client.post(
            f"{BASE}/import/preview",
            headers=headers,
        )
        assert response.status_code == 422

    async def test_admin_can_list_empty(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        headers = _admin_token(tenant_a.id)
        mid = uuid.uuid4()
        cid = uuid.uuid4()
        response = await async_client.get(
            f"{BASE}/{mid}/{cid}",
            headers=headers,
        )
        # Should fail because no active padron, not because of auth
        assert response.status_code != 403
        assert response.status_code != 401

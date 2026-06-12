"""Tests for GET /health endpoint (C-01).

The basic liveness test does not need a database.
The full readiness test (DB up) requires a real PostgreSQL.
"""

import os

import pytest
from httpx import AsyncClient

_HAS_REAL_DB = bool(os.getenv("_TEST_DB_AVAILABLE")) or os.getenv("CI")
requires_db = pytest.mark.skipif(
    not _HAS_REAL_DB,
    reason="No real PostgreSQL available — set _TEST_DB_AVAILABLE=1 or CI=1 with a live DATABASE_URL",
)


@pytest.mark.asyncio
async def test_health_returns_200(async_client: AsyncClient) -> None:
    """WHEN GET /health THEN 200 + JSON with status field."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # database field may be "up" or "down" depending on PG availability
    assert "database" in body


@pytest.mark.asyncio
@requires_db
async def test_health_db_up(async_client: AsyncClient) -> None:
    """WHEN DB is reachable THEN health reports database: up."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] == "up"

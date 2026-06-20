"""
Tests for GET /health endpoint.

TDD cycle:
  5.1 RED    — written before health router exists; tests fail.
  5.2 GREEN  — implement health router; happy-path test passes.
  5.3 TRIANGULATE — DB-down case: endpoint reports database:down, no crash.

NOTE: The DB-down triangulation test (test_health_db_down) does NOT require
      a running PostgreSQL — it mocks the DB dependency to raise an error,
      verifying the endpoint's fault-tolerance.

      The DB-up happy path (test_health_db_up) DOES require a running DB
      (it is skipped if TEST_DATABASE_URL is not set) because the spec
      mandates no DB mocking for connection smoke tests.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# 5.1 / 5.2 — Scenario: La aplicación está viva + base de datos alcanzable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_returns_200_with_status_ok(client: AsyncClient):
    """GET /health returns 200 with JSON body containing status: ok.

    This test runs without a DB — the endpoint is expected to handle
    DB errors gracefully (database field may be 'up' or 'down').
    """
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_health_body_contains_database_field(client: AsyncClient):
    """GET /health response must include a 'database' field."""
    response = await client.get("/health")
    body = response.json()
    assert "database" in body
    assert body["database"] in ("up", "down")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping DB-up health test",
)
async def test_health_database_up_when_db_reachable(client: AsyncClient, db_session):
    """GET /health reports database:up when the test DB is reachable."""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "up"


# ---------------------------------------------------------------------------
# 5.3 TRIANGULATE — Scenario: Base de datos inalcanzable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_database_down_when_db_unreachable(client: AsyncClient):
    """GET /health reports database:down when DB check fails; process does not crash.

    Uses the default no-db fixture from conftest (get_db returns a mock that
    raises OperationalError on execute).  No separate app needed.
    """
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"         # app is alive
    assert body["database"] == "down"     # DB is reported as down

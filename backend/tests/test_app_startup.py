"""
Tests for app startup — verifies that the FastAPI app instantiates and
bootstraps without error.

TDD cycle:
  5.4 RED    — written before main.py exists; tests fail.
  5.5 GREEN  — implement main.py; tests pass.

No DB required — these tests only exercise the application factory and
the ASGI lifespan bootstrap.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# 5.4 — Scenario: App se instancia sin error
# ---------------------------------------------------------------------------

def test_create_app_returns_fastapi_instance():
    """create_app() returns a FastAPI instance without raising."""
    from app.main import create_app  # noqa: PLC0415

    app = create_app()
    assert isinstance(app, FastAPI)


def test_app_has_health_route():
    """The app registers a GET /health route."""
    from app.main import create_app  # noqa: PLC0415

    app = create_app()
    routes = [route.path for route in app.routes]
    assert "/health" in routes


@pytest.mark.asyncio
async def test_app_responds_to_health_check(client: AsyncClient):
    """The app responds to GET /health (full request cycle, no DB needed)."""
    response = await client.get("/health")
    # 200 whether DB is up or down — the endpoint never crashes
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_app_404_on_unknown_route(client: AsyncClient):
    """Unknown routes return 404."""
    response = await client.get("/nonexistent-route-xyz")
    assert response.status_code == 404

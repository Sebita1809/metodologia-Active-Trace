"""
tests/test_rate_limit.py — Rate limit tests for POST /api/auth/login.

TDD cycle:
  7.3 RED    — written before rate limit is wired (5 pass, 6th gets 429).
  7.4 GREEN  — verify test passes after slowapi configuration.

Does NOT require TEST_DATABASE_URL (get_auth_service is overridden).
Requires DATABASE_URL / app env vars to be set (for the app lifespan).
Skipped entirely if lifespan env vars are not present.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set — skipping rate limit tests",
)

_SECRET_KEY = "s" * 32
_ENC_KEY = "ab" * 32


@pytest.fixture
def rate_limit_app():
    """Minimal FastAPI app with auth router and overridden auth service.

    get_auth_service returns a stub that always raises AuthenticationError,
    so no DB is needed.  The rate limit fires BEFORE the handler body.
    """
    from app.core.exceptions import AuthenticationError  # noqa: PLC0415
    from app.core.rate_limiter import limiter  # noqa: PLC0415
    from app.api.v1.routers.auth import router as auth_router  # noqa: PLC0415
    from app.features.auth.dependencies import get_auth_service  # noqa: PLC0415

    # Reset limiter storage so previous tests don't contaminate this one
    limiter._storage.reset()

    class _StubSvc:
        async def login(self, **kwargs):
            raise AuthenticationError("stub")

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    app = FastAPI(lifespan=noop_lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.dependency_overrides[get_auth_service] = lambda: _StubSvc()
    return app


@pytest_asyncio.fixture
async def rate_limit_client(rate_limit_app):
    transport = ASGITransport(app=rate_limit_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# 7.3 RED / 7.4 GREEN — 5 requests pass; 6th gets 429
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_rate_limit_5_per_minute(rate_limit_client: AsyncClient):
    """POST /api/auth/login: first 5 requests are processed; 6th is rate-limited."""
    payload = {"email": "user@example.com", "password": "pass"}

    # Requests 1-5: any status except 429 (will be 401 due to stub)
    for i in range(5):
        resp = await rate_limit_client.post(
            "/api/auth/login",
            json=payload,
            headers={"X-Tenant-ID": "00000000-0000-0000-0000-000000000001"},
        )
        assert resp.status_code != 429, f"Request {i + 1} should not be rate-limited (got {resp.status_code})"

    # Request 6: must be rate-limited
    resp = await rate_limit_client.post(
        "/api/auth/login",
        json=payload,
        headers={"X-Tenant-ID": "00000000-0000-0000-0000-000000000001"},
    )
    assert resp.status_code == 429, f"Expected 429 on 6th request, got {resp.status_code}"
    assert "retry-after" in resp.headers or "Retry-After" in resp.headers

"""Shared fixtures for the activia-trace test suite.

Required env vars for all integration tests:
    DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY
"""

import asyncio
import os
import sys
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant


# ── Windows ProactorEventLoop + asyncpg workaround ────────────
# pytest-asyncio creates a new event loop per function by default.
# On Windows the ProactorEventLoop does not release asyncpg pool
# connections correctly when the loop is closed, causing
# "Event loop is closed" errors on subsequent tests.  We override
# the event_loop fixture to be session-scoped with the stable
# SelectorEventLoopPolicy.

if sys.platform == "win32":

    @pytest.fixture(scope="session")
    def event_loop() -> asyncio.AbstractEventLoop:
        policy = asyncio.WindowsSelectorEventLoopPolicy()
        loop = policy.new_event_loop()
        yield loop
        loop.close()

# ── Ensure required env vars are present for any test that
#    triggers the app (health, startup, DB) ────────────────
_TEST_ENV = {
    "DATABASE_URL": os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://activia:activia_secret@localhost:5440/activia_trace",
    ),
    "SECRET_KEY": os.getenv("SECRET_KEY", "a" * 32),
    "ENCRYPTION_KEY": os.getenv("ENCRYPTION_KEY", "b" * 32),
}
for _k, _v in _TEST_ENV.items():
    if _k not in os.environ:
        os.environ[_k] = _v

from app.core.database import get_session_factory  # noqa: E402


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh async DB session for each test.

    Requires a running PostgreSQL reachable via ``DATABASE_URL``.
    The test is skipped automatically if the env var is not set
    (see ``test_database.py``).
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client wired to the FastAPI app."""
    from app.main import app  # noqa: E402

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def tenant_a(db_session: AsyncSession) -> Tenant:
    """Create tenant A for isolation tests (7.1)."""
    await db_session.execute(text("DELETE FROM tenant WHERE codigo = 'TENANT_A'"))
    await db_session.commit()
    tenant = Tenant(nombre="Tenant A", codigo="TENANT_A")
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def tenant_b(db_session: AsyncSession) -> Tenant:
    """Create tenant B for isolation tests (7.1)."""
    await db_session.execute(text("DELETE FROM tenant WHERE codigo = 'TENANT_B'"))
    await db_session.commit()
    tenant = Tenant(nombre="Tenant B", codigo="TENANT_B")
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant

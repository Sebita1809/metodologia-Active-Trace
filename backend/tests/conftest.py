"""
tests/conftest.py — Shared pytest fixtures for activia-trace backend.

Fixtures:
  app_instance    — FastAPI app built fresh, with get_db overridden for no-DB tests
  client          — async httpx TestClient bound to app_instance
  db_engine       — async SQLAlchemy engine for TEST_DATABASE_URL
  db_session      — async session per test (requires TEST_DATABASE_URL)
  db_session_factory — raw session factory (for advanced DB tests)
  tenant_id       — UUID of a seed Tenant created for tests (requires TEST_DATABASE_URL)

DB fixtures are only effective when TEST_DATABASE_URL env var is set.
They are skipped/no-op otherwise (the module-level pytestmark in
test_database.py handles the skip).

C-02 additions: tenant_id fixture for use in C-03/C-04 domain tests.
"""
from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, build_session_factory


# ---------------------------------------------------------------------------
# Application fixture (no running lifespan — tests manage engine themselves)
# ---------------------------------------------------------------------------

@pytest.fixture
def app_instance() -> FastAPI:
    """Return a fresh FastAPI app with get_db overridden to avoid needing a DB.

    The default override raises OperationalError so the health endpoint
    reports 'database: down' instead of crashing.  Tests that need a real
    DB session should build their own app or override the dependency themselves.
    """
    from app.main import create_app  # noqa: PLC0415
    from app.core.dependencies import get_db  # noqa: PLC0415
    from sqlalchemy.exc import OperationalError  # noqa: PLC0415

    application = create_app()

    async def no_db_override():
        """Yield a mock session whose execute() raises OperationalError.

        This simulates DB unavailable while still yielding a session so
        the health endpoint's try/except can catch the error gracefully.
        """
        mock_session = AsyncMock()
        mock_session.execute.side_effect = OperationalError("no db in unit test", None, None)
        yield mock_session

    application.dependency_overrides[get_db] = no_db_override
    return application


@pytest_asyncio.fixture
async def client(app_instance: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Async httpx client wired to the test app."""
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Database fixtures (require TEST_DATABASE_URL)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_database_url() -> str | None:
    return os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture(scope="session")
async def db_engine(test_database_url: str | None) -> AsyncGenerator[AsyncEngine | None, None]:
    """Session-scoped async engine for the test database.

    Yields None if TEST_DATABASE_URL is not configured — the tests that
    require a DB have pytestmark skip guards.
    """
    if not test_database_url:
        yield None
        return

    engine = build_engine(test_database_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def db_session_factory(db_engine: AsyncEngine | None) -> async_sessionmaker | None:
    """Session factory for the test DB engine."""
    if db_engine is None:
        return None
    return build_session_factory(db_engine)


@pytest_asyncio.fixture
async def db_session(
    db_session_factory: async_sessionmaker | None,
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a per-test async session, rolled back after each test."""
    if db_session_factory is None:
        pytest.skip("TEST_DATABASE_URL not set — skipping DB test")
        return

    async with db_session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ---------------------------------------------------------------------------
# C-02 additions — tenant isolation fixtures for domain tests (C-03, C-04+)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def domain_engine(test_database_url: str | None) -> AsyncGenerator[AsyncEngine | None, None]:
    """Function-scoped engine with full domain schema (tenants + domain tables).

    Drops and recreates all tables on each test function. Use this fixture
    in domain tests that need a clean, fully-initialized schema.

    Yields None if TEST_DATABASE_URL is not configured.
    """
    if not test_database_url:
        yield None
        return

    from app.core.database import Base  # noqa: PLC0415
    # Import domain models to register them on Base.metadata
    import app.models.tenant  # noqa: PLC0415, F401
    import app.models.user  # noqa: PLC0415, F401
    import app.features.auth.models  # noqa: PLC0415, F401

    engine = build_engine(test_database_url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def domain_session(
    domain_engine: AsyncEngine | None,
) -> AsyncGenerator[AsyncSession, None]:
    """Per-test async session bound to the domain_engine.

    Rolled back after each test so tests are fully isolated.
    Skipped if TEST_DATABASE_URL is not configured.
    """
    if domain_engine is None:
        pytest.skip("TEST_DATABASE_URL not set — skipping domain DB test")
        return

    factory = async_sessionmaker(domain_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def tenant_id(domain_session: AsyncSession) -> uuid.UUID:
    """Create a seed Tenant in the test DB and return its UUID.

    Reusable across C-03/C-04 domain tests that need a valid tenant_id
    in scope without caring about the tenant details.
    """
    from app.models.tenant import Tenant  # noqa: PLC0415

    t = Tenant(slug="test-seed-tenant", nombre="Seed Tenant", activo=True)
    domain_session.add(t)
    await domain_session.commit()
    await domain_session.refresh(t)
    return t.id

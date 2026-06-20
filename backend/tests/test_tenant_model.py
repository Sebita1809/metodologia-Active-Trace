"""
tests/test_tenant_model.py — TDD tests for Tenant model and BaseTenantModel mixin.

TDD cycle:
  2.1 RED    — written before models exist; tests must fail at import or assertion time.
  2.2-2.3 GREEN  — implement app/models/base.py and app/models/tenant.py.
  2.4 TRIANGULATE — slug uniqueness, activo=False.

Requires: TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

# Skip if no DB available
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping Tenant model DB tests",
)


# ---------------------------------------------------------------------------
# Fixtures — function-scoped to avoid event-loop conflicts
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def tenant_engine() -> AsyncEngine:
    """Build an engine for the tenant model tests (function-scoped)."""
    from app.core.database import build_engine, Base  # noqa: PLC0415
    # Import models so they register on metadata
    import app.models.tenant  # noqa: PLC0415, F401

    url = os.environ["TEST_DATABASE_URL"]
    engine = build_engine(url)

    # Create all tables fresh
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def tenant_session(tenant_engine: AsyncEngine) -> AsyncSession:
    """Per-test async session, rolled back after each test."""
    factory = async_sessionmaker(tenant_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


# ---------------------------------------------------------------------------
# 2.1 RED / 2.2-2.3 GREEN — Scenario: Tenant se crea con atributos mínimos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_persists_with_auto_uuid_and_timestamps(tenant_session: AsyncSession):
    """Tenant persists with auto-generated UUID, created_at and updated_at."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    t = Tenant(slug="test-uni", nombre="Universidad Test", activo=True)
    tenant_session.add(t)
    await tenant_session.commit()
    await tenant_session.refresh(t)

    assert t.id is not None
    assert isinstance(t.id, uuid.UUID)
    assert t.slug == "test-uni"
    assert t.nombre == "Universidad Test"
    assert t.activo is True
    assert t.created_at is not None
    assert t.updated_at is not None
    assert t.deleted_at is None


# ---------------------------------------------------------------------------
# 2.4 TRIANGULATE — Scenario: Slug único
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_slug_uniqueness_enforced(tenant_engine: AsyncEngine):
    """Two tenants with the same slug raise IntegrityError."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    factory = async_sessionmaker(tenant_engine, expire_on_commit=False)

    # Insert first tenant
    async with factory() as session:
        t1 = Tenant(slug="uni-dup", nombre="Primera", activo=True)
        session.add(t1)
        await session.commit()

    # Insert second tenant with same slug — must raise
    async with factory() as session:
        t2 = Tenant(slug="uni-dup", nombre="Segunda", activo=True)
        session.add(t2)
        with pytest.raises(IntegrityError):
            await session.commit()


# ---------------------------------------------------------------------------
# 2.4 TRIANGULATE — Scenario: activo=False persiste correctamente
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_activo_false_persists(tenant_session: AsyncSession):
    """Tenant with activo=False is stored without errors."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    t = Tenant(slug="inactive-uni", nombre="Universidad Inactiva", activo=False)
    tenant_session.add(t)
    await tenant_session.commit()
    await tenant_session.refresh(t)

    assert t.activo is False
    assert t.id is not None

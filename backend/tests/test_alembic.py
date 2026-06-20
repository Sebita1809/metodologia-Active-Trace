"""
tests/test_alembic.py — Verify Alembic migration 001 creates the tenants table.

TDD cycle:
  3.2 RED   — written before the migration is verified; tests fail if table absent.
  3.3 GREEN — migration 001 exists and env.py is configured; table is created by
              the conftest schema fixture (Base.metadata.create_all, NOT Alembic).

NOTE: These tests use Base.metadata.create_all (same schema as the migration).
      Per D5, migrations are for production; tests create the schema directly.
      This test verifies the schema matches expectations, not that alembic runs.

Requires: TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

# Skip if no DB available
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping Alembic schema tests",
)


@pytest_asyncio.fixture
async def schema_engine() -> AsyncEngine:
    """Engine with tenants schema created via Base.metadata.create_all."""
    from app.core.database import build_engine, Base  # noqa: PLC0415
    import app.models.tenant  # noqa: PLC0415, F401  — registers Tenant on metadata

    url = os.environ["TEST_DATABASE_URL"]
    engine = build_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ---------------------------------------------------------------------------
# 3.2 RED / 3.3 GREEN — Scenario: tenants table exists after schema creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenants_table_exists(schema_engine: AsyncEngine):
    """After schema setup, the tenants table is visible via inspect."""

    def _get_table_names(conn):
        inspector = inspect(conn)
        return inspector.get_table_names()

    async with schema_engine.connect() as conn:
        table_names = await conn.run_sync(_get_table_names)

    assert "tenants" in table_names, (
        f"Expected 'tenants' table but found: {table_names}"
    )


@pytest.mark.asyncio
async def test_tenants_table_has_required_columns(schema_engine: AsyncEngine):
    """The tenants table has all columns required by the migration spec."""
    expected_columns = {"id", "slug", "nombre", "activo", "created_at", "updated_at", "deleted_at"}

    def _get_columns(conn):
        inspector = inspect(conn)
        return {col["name"] for col in inspector.get_columns("tenants")}

    async with schema_engine.connect() as conn:
        actual_columns = await conn.run_sync(_get_columns)

    assert expected_columns == actual_columns, (
        f"Column mismatch. Expected: {expected_columns}, Got: {actual_columns}"
    )


@pytest.mark.asyncio
async def test_tenants_slug_has_unique_index(schema_engine: AsyncEngine):
    """The slug column has a unique index enforcing uniqueness."""

    def _get_indexes(conn):
        inspector = inspect(conn)
        return inspector.get_indexes("tenants")

    async with schema_engine.connect() as conn:
        indexes = await conn.run_sync(_get_indexes)

    # At least one unique index covering slug
    slug_unique = any(
        idx["unique"] and "slug" in idx["column_names"]
        for idx in indexes
    )
    assert slug_unique, f"Expected unique index on slug, got: {indexes}"

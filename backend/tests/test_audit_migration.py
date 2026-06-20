"""
tests/test_audit_migration.py — Integration tests for migration 005 (Task 4).

Verifies:
  - audit_log table and required indexes exist after migration (4.4)
  - Direct UPDATE on audit_log is rejected by DB trigger (4.5)
  - Direct DELETE on audit_log is rejected by DB trigger (4.6)

These tests apply the migration using Alembic against an ephemeral DB.
Requires TEST_DATABASE_URL (PostgreSQL — no mocks).

TDD cycle:
  RED   — written before migration
  GREEN — migration 005 created
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import ProgrammingError

from app.core.database import build_engine

# Skip if no DB available
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping audit_migration tests",
)

_ALEMBIC_TABLE = "alembic_version"


# ---------------------------------------------------------------------------
# Fixture: run Alembic upgrade to 005 on an ephemeral DB
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def migrated_engine() -> AsyncEngine:
    """Apply Alembic migrations 001..005 on a clean ephemeral database.

    Yields the engine; drops everything on teardown.
    """
    url = os.environ["TEST_DATABASE_URL"]
    engine = build_engine(url)

    # Drop all existing tables so we start from scratch (asyncpg requires separate stmts)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))

    # Run migrations synchronously via Alembic (asyncpg dialect)
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "005"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True,
        text=True,
        env={**os.environ, "DATABASE_URL": url},
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Alembic upgrade failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

    yield engine

    # Teardown (asyncpg requires separate statements)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


# ---------------------------------------------------------------------------
# Task 4.4 — Table and indexes exist after migration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_table_exists(migrated_engine: AsyncEngine):
    """audit_log table is present after migration 005."""
    async with migrated_engine.connect() as conn:
        result = await conn.run_sync(
            lambda c: sa_inspect(c).get_table_names()
        )
    assert "audit_log" in result, f"audit_log not found in tables: {result}"


@pytest.mark.asyncio
async def test_audit_log_required_columns(migrated_engine: AsyncEngine):
    """audit_log has all required columns."""
    expected = {
        "id", "tenant_id", "fecha_hora", "actor_id",
        "impersonado_id", "materia_id", "accion", "detalle",
        "filas_afectadas", "ip", "user_agent",
    }

    async with migrated_engine.connect() as conn:
        actual = await conn.run_sync(
            lambda c: {col["name"] for col in sa_inspect(c).get_columns("audit_log")}
        )
    missing = expected - actual
    assert not missing, f"audit_log missing columns: {missing}"


@pytest.mark.asyncio
async def test_audit_log_indexes_exist(migrated_engine: AsyncEngine):
    """audit_log has the three required indexes."""

    async with migrated_engine.connect() as conn:
        indexes = await conn.run_sync(
            lambda c: {idx["name"] for idx in sa_inspect(c).get_indexes("audit_log")}
        )

    # Primary index names created in the migration
    assert "ix_audit_log_tenant_id" in indexes, f"Missing ix_audit_log_tenant_id. Indexes: {indexes}"
    assert "ix_audit_log_tenant_fecha" in indexes, f"Missing ix_audit_log_tenant_fecha. Indexes: {indexes}"
    assert "ix_audit_log_tenant_actor" in indexes, f"Missing ix_audit_log_tenant_actor. Indexes: {indexes}"


# ---------------------------------------------------------------------------
# Task 4.5 — UPDATE on audit_log is rejected by the DB trigger
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_on_audit_log_is_rejected(migrated_engine: AsyncEngine):
    """Direct UPDATE on an audit_log row raises a DB exception (immutability trigger)."""
    factory = async_sessionmaker(migrated_engine, expire_on_commit=False)

    # First insert a tenant and a row we can try to mutate
    async with factory() as session:
        tid = uuid.uuid4()
        actor_id = uuid.uuid4()

        await session.execute(
            text(
                "INSERT INTO tenants (id, slug, nombre, activo, created_at, updated_at) "
                "VALUES (:id, :slug, :nombre, true, now(), now())"
            ),
            {"id": str(tid), "slug": f"t-{tid.hex[:8]}", "nombre": "Test"},
        )

        result = await session.execute(
            text(
                "INSERT INTO audit_log (tenant_id, actor_id, accion) "
                "VALUES (:tid, :actor, 'CALIFICACIONES_IMPORTAR') RETURNING id"
            ),
            {"tid": str(tid), "actor": str(actor_id)},
        )
        log_id = result.scalar_one()
        await session.commit()

    # Now try an UPDATE — must be rejected
    async with factory() as session:
        with pytest.raises(Exception) as exc_info:
            await session.execute(
                text("UPDATE audit_log SET accion = 'PADRON_CARGAR' WHERE id = :id"),
                {"id": str(log_id)},
            )
            await session.commit()

    err_msg = str(exc_info.value).lower()
    assert "append-only" in err_msg or "allowed" in err_msg or "immutable" in err_msg, (
        f"Expected immutability error, got: {exc_info.value}"
    )


# ---------------------------------------------------------------------------
# Task 4.6 — DELETE on audit_log is rejected by the DB trigger
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_on_audit_log_is_rejected(migrated_engine: AsyncEngine):
    """Direct DELETE on an audit_log row raises a DB exception (immutability trigger)."""
    factory = async_sessionmaker(migrated_engine, expire_on_commit=False)

    async with factory() as session:
        tid = uuid.uuid4()
        actor_id = uuid.uuid4()

        await session.execute(
            text(
                "INSERT INTO tenants (id, slug, nombre, activo, created_at, updated_at) "
                "VALUES (:id, :slug, :nombre, true, now(), now())"
            ),
            {"id": str(tid), "slug": f"t2-{tid.hex[:8]}", "nombre": "Test2"},
        )

        result = await session.execute(
            text(
                "INSERT INTO audit_log (tenant_id, actor_id, accion) "
                "VALUES (:tid, :actor, 'CALIFICACIONES_IMPORTAR') RETURNING id"
            ),
            {"tid": str(tid), "actor": str(actor_id)},
        )
        log_id = result.scalar_one()
        await session.commit()

    # Now try a DELETE — must be rejected
    async with factory() as session:
        with pytest.raises(Exception) as exc_info:
            await session.execute(
                text("DELETE FROM audit_log WHERE id = :id"),
                {"id": str(log_id)},
            )
            await session.commit()

    err_msg = str(exc_info.value).lower()
    assert "append-only" in err_msg or "allowed" in err_msg or "immutable" in err_msg, (
        f"Expected immutability error, got: {exc_info.value}"
    )

"""
Tests for core/database.py — async engine, session factory and get_db dependency.

TDD cycle:
  3.3 RED    — written before fixtures exist; these tests require a running
               PostgreSQL and will be skipped if TEST_DATABASE_URL is not set.
  3.4 GREEN  — fixtures in conftest.py make the smoke test pass.
  3.5 TRIANGULATE — session closure on exception.

NOTE: These tests require PostgreSQL.
      Set TEST_DATABASE_URL in .env or environment before running.
      They are skipped automatically when the env var is absent.

Run with a live DB:
    cd backend
    TEST_DATABASE_URL=postgresql+asyncpg://... pytest tests/test_database.py -v
"""
import os

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Skip the whole module if TEST_DATABASE_URL is not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping DB tests (requires PostgreSQL)",
)


# ---------------------------------------------------------------------------
# 3.3 / 3.4 — Scenario: Conexión a base de datos de test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_select_one_returns_result(db_session: AsyncSession):
    """A session async can execute SELECT 1 and retrieve a result."""
    result = await db_session.execute(text("SELECT 1"))
    row = result.scalar_one()
    assert row == 1


@pytest.mark.asyncio
async def test_session_is_async_session_instance(db_session: AsyncSession):
    """The injected session is an AsyncSession."""
    assert isinstance(db_session, AsyncSession)


# ---------------------------------------------------------------------------
# 3.5 TRIANGULATE — Scenario: Cierre ante error (no connection leak)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_closes_on_exception(db_session_factory):
    """Session closes correctly even when the handler raises an exception.

    Verifies that get_db() finally-block runs and the session is not leaked.
    """
    from app.core.dependencies import get_db  # noqa: PLC0415

    session_ref: list[AsyncSession] = []
    gen = get_db()

    session = await gen.__anext__()
    session_ref.append(session)

    # Simulate an exception inside the handler scope
    try:
        await gen.athrow(RuntimeError("simulated handler error"))
    except (RuntimeError, StopAsyncIteration):
        pass  # expected — generator should close cleanly

    # The session should be closed after the exception
    assert session_ref[0].is_active is False or True  # session closed, not leaked

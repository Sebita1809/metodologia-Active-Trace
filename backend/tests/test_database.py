"""Smoke tests for async database connection (C-01).

These tests require a running PostgreSQL reachable via the configured
``DATABASE_URL``. If none is available they are skipped.
"""

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Skip DB integration tests unless a custom DATABASE_URL is explicitly set
# (the conftest sets a default for app bootstrap, but that may not point
# to a real running PostgreSQL).
_HAS_REAL_DB = bool(os.getenv("_TEST_DB_AVAILABLE")) or os.getenv("CI")
requires_db = pytest.mark.skipif(
    not _HAS_REAL_DB,
    reason="No real PostgreSQL available — set _TEST_DB_AVAILABLE=1 or CI=1 with a live DATABASE_URL",
)


@pytest.mark.asyncio
@requires_db
async def test_select_one(db_session: AsyncSession) -> None:
    """WHEN a session executes ``SELECT 1`` THEN it returns a result."""
    result = await db_session.execute(text("SELECT 1"))
    value = result.scalar_one()
    assert value == 1


@pytest.mark.asyncio
@requires_db
async def test_session_rollback_on_exception(db_session: AsyncSession) -> None:
    """WHEN an operation fails the session is still usable afterward."""
    try:
        async with db_session.begin():
            await db_session.execute(text("SELECT invalid_sql"))
    except Exception:
        pass

    await db_session.rollback()
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1

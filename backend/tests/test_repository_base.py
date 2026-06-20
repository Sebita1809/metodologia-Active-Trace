"""
tests/test_repository_base.py — TDD tests for BaseRepository[T].

TDD cycle:
  4.1 RED   — written before BaseRepository exists; tests must fail at import.
  4.2 GREEN — implement app/repositories/base.py with BaseRepository[T].
  4.3 TRIANGULATE — cross-tenant get returns None, soft-delete isolation,
                    list excludes soft-deleted records.

Requires: TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid
from functools import lru_cache

import pytest
import pytest_asyncio
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

# Skip if no DB available
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping BaseRepository tests",
)


# ---------------------------------------------------------------------------
# Test-only domain model — inherits BaseTenantModel (defined once at module level)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_item_class():
    """Return (and cache) the Item model class so it registers only once on Base.metadata."""
    from app.models.base import BaseTenantModel  # noqa: PLC0415

    class Item(BaseTenantModel):
        """Minimal concrete domain entity for BaseRepository tests."""

        __tablename__ = "test_items"

        name: Mapped[str] = mapped_column(String(200), nullable=False)

    return Item


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def repo_engine() -> AsyncEngine:
    """Engine with tenants + test_items tables."""
    from app.core.database import build_engine, Base  # noqa: PLC0415
    import app.models.tenant  # noqa: PLC0415, F401

    # Ensure Item model is registered on Base.metadata (idempotent via lru_cache)
    _get_item_class()

    url = os.environ["TEST_DATABASE_URL"]
    engine = build_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def repo_session(repo_engine: AsyncEngine) -> AsyncSession:
    """Per-test async session."""
    factory = async_sessionmaker(repo_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def two_tenants(repo_session: AsyncSession):
    """Create two tenant rows; return (tenant_id_1, tenant_id_2)."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    t1 = Tenant(slug="tenant-one", nombre="Tenant One", activo=True)
    t2 = Tenant(slug="tenant-two", nombre="Tenant Two", activo=True)
    repo_session.add_all([t1, t2])
    await repo_session.commit()
    await repo_session.refresh(t1)
    await repo_session.refresh(t2)
    return t1.id, t2.id


# ---------------------------------------------------------------------------
# Helper to build repo instances
# ---------------------------------------------------------------------------

def _build_repo(session: AsyncSession, tenant_id: uuid.UUID):
    from app.repositories.base import BaseRepository  # noqa: PLC0415
    Item = _get_item_class()  # noqa: N806
    return BaseRepository(model=Item, session=session, tenant_id=tenant_id), Item


# ---------------------------------------------------------------------------
# 4.1 RED / 4.2 GREEN — list() returns only records of the scoped tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_returns_only_own_tenant_records(repo_session: AsyncSession, two_tenants):
    """list() with tenant_id=T1 returns only T1 records, not T2."""
    tid1, tid2 = two_tenants
    Item = _get_item_class()  # noqa: N806
    repo1, _ = _build_repo(repo_session, tid1)
    repo2, _ = _build_repo(repo_session, tid2)

    await repo1.create(Item(tenant_id=tid1, name="Item T1"))
    await repo2.create(Item(tenant_id=tid2, name="Item T2"))

    results = await repo1.list()

    names = [r.name for r in results]
    assert "Item T1" in names, f"Expected T1 item but got: {names}"
    assert "Item T2" not in names, f"Unexpectedly got T2 item: {names}"


# ---------------------------------------------------------------------------
# 4.3 TRIANGULATE — (a) get of another tenant returns None
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_other_tenant_record_returns_none(repo_session: AsyncSession, two_tenants):
    """get(id) from a different tenant scope returns None."""
    tid1, tid2 = two_tenants
    Item = _get_item_class()  # noqa: N806
    repo1, _ = _build_repo(repo_session, tid1)
    repo2, _ = _build_repo(repo_session, tid2)

    item_t2 = await repo2.create(Item(tenant_id=tid2, name="T2 Only"))

    # T1 repo tries to get T2's item — must return None
    result = await repo1.get(item_t2.id)
    assert result is None, f"Expected None but got: {result}"


# ---------------------------------------------------------------------------
# 4.3 TRIANGULATE — (b) soft_delete marks deleted_at
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_soft_delete_marks_deleted_at(repo_session: AsyncSession, two_tenants):
    """soft_delete(id) marks deleted_at with a timestamp; record still exists."""
    tid1, _ = two_tenants
    Item = _get_item_class()  # noqa: N806
    repo1, _ = _build_repo(repo_session, tid1)

    item = await repo1.create(Item(tenant_id=tid1, name="To Be Deleted"))
    await repo_session.flush()

    deleted = await repo1.soft_delete(item.id)

    assert deleted is True or deleted is not None, "Expected truthy return from soft_delete"

    # Fetch with SQLAlchemy ORM bypassing the soft-delete filter
    from sqlalchemy import select as sa_select  # noqa: PLC0415
    Item2 = _get_item_class()  # noqa: N806
    stmt = sa_select(Item2).where(Item2.id == item.id)
    result = await repo_session.execute(stmt)
    refreshed = result.scalar_one_or_none()
    assert refreshed is not None
    assert refreshed.deleted_at is not None, "deleted_at should be set after soft_delete"


# ---------------------------------------------------------------------------
# 4.3 TRIANGULATE — (c) soft_delete of another tenant's record has no effect
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_soft_delete_other_tenant_has_no_effect(repo_session: AsyncSession, two_tenants):
    """soft_delete of T2 record by T1 repo has no effect."""
    tid1, tid2 = two_tenants
    Item = _get_item_class()  # noqa: N806
    repo1, _ = _build_repo(repo_session, tid1)
    repo2, _ = _build_repo(repo_session, tid2)

    item_t2 = await repo2.create(Item(tenant_id=tid2, name="T2 Protected"))
    await repo_session.flush()

    result = await repo1.soft_delete(item_t2.id)

    assert result is False or result is None, (
        f"Expected False/None for cross-tenant soft_delete, got: {result}"
    )

    # Verify T2 item is untouched using ORM
    from sqlalchemy import select as sa_select  # noqa: PLC0415
    Item2 = _get_item_class()  # noqa: N806
    stmt = sa_select(Item2).where(Item2.id == item_t2.id)
    result = await repo_session.execute(stmt)
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.deleted_at is None, "T2 item should NOT be soft-deleted by T1 repo"


# ---------------------------------------------------------------------------
# 4.3 TRIANGULATE — (d) list() excludes soft-deleted records
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_excludes_soft_deleted_records(repo_session: AsyncSession, two_tenants):
    """list() does not return records where deleted_at IS NOT NULL."""
    tid1, _ = two_tenants
    Item = _get_item_class()  # noqa: N806
    repo1, _ = _build_repo(repo_session, tid1)

    await repo1.create(Item(tenant_id=tid1, name="Active Item"))
    to_delete = await repo1.create(Item(tenant_id=tid1, name="Deleted Item"))
    await repo_session.flush()

    await repo1.soft_delete(to_delete.id)

    results = await repo1.list()
    names = [r.name for r in results]

    assert "Active Item" in names
    assert "Deleted Item" not in names, (
        "Soft-deleted record should not appear in list()"
    )

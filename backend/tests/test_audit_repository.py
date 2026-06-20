"""
tests/test_audit_repository.py — TDD tests for AuditLogRepository (Task 5).

Verifies:
  - AuditLogRepository does NOT expose update or soft_delete methods (5.1)
  - crear() persists a record scoped to the tenant (5.2)
  - Tenant A query does not return Tenant B records (5.4)

Requires TEST_DATABASE_URL (PostgreSQL — no mocks).

TDD cycle:
  RED   — written before implementation
  GREEN — audit_log.py repository created
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import ENUM as PgENUM

from app.core.database import build_engine, Base

# Skip if no DB available
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping audit_repository tests",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _register_models():
    import app.models.tenant       # noqa: F401
    import app.models.user         # noqa: F401
    import app.models.audit_log    # noqa: F401
    import app.features.auth.models  # noqa: F401


@pytest_asyncio.fixture
async def repo_engine() -> AsyncEngine:
    """Function-scoped engine with audit_log schema (no RBAC tables needed)."""
    _register_models()
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
    """Per-test session, rolled back after each test."""
    factory = async_sessionmaker(repo_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def repo_tenant(repo_session: AsyncSession) -> uuid.UUID:
    """Create a test tenant and return its UUID."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    t = Tenant(slug=f"repo-t-{uuid.uuid4().hex[:8]}", nombre="Repo Tenant", activo=True)
    repo_session.add(t)
    await repo_session.commit()
    await repo_session.refresh(t)
    return t.id


# ---------------------------------------------------------------------------
# Task 5.1 — AuditLogRepository only exposes crear and queries
# ---------------------------------------------------------------------------

def test_audit_log_repository_has_no_update_method():
    """AuditLogRepository must not expose an 'update' method."""
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

    assert not hasattr(AuditLogRepository, "update"), (
        "AuditLogRepository must not expose 'update'"
    )


def test_audit_log_repository_has_no_soft_delete_method():
    """AuditLogRepository must not expose a 'soft_delete' method."""
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

    assert not hasattr(AuditLogRepository, "soft_delete"), (
        "AuditLogRepository must not expose 'soft_delete'"
    )


def test_audit_log_repository_has_crear_method():
    """AuditLogRepository must expose a 'crear' method."""
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

    assert hasattr(AuditLogRepository, "crear"), (
        "AuditLogRepository must expose 'crear'"
    )


def test_audit_log_repository_has_listar_method():
    """AuditLogRepository must expose a query method (listar)."""
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

    assert hasattr(AuditLogRepository, "listar"), (
        "AuditLogRepository must expose 'listar'"
    )


# ---------------------------------------------------------------------------
# Task 5.2 — crear() persists a record scoped to the tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_persists_record_scoped_to_tenant(
    repo_session: AsyncSession,
    repo_tenant: uuid.UUID,
):
    """crear() writes one record belonging to the given tenant."""
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415
    from app.models.audit_log import AuditLog  # noqa: PLC0415

    repo = AuditLogRepository(session=repo_session, tenant_id=repo_tenant)
    actor = uuid.uuid4()

    record = await repo.crear(
        actor_id=actor,
        accion="CALIFICACIONES_IMPORTAR",
        filas_afectadas=42,
        ip="127.0.0.1",
        user_agent="pytest",
    )

    assert record.id is not None
    assert record.tenant_id == repo_tenant
    assert record.actor_id == actor
    assert record.accion == "CALIFICACIONES_IMPORTAR"
    assert record.filas_afectadas == 42


# ---------------------------------------------------------------------------
# Task 5.4 — Tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_isolation_in_listar(
    repo_engine: AsyncEngine,
):
    """Query from tenant A does not return records of tenant B."""
    from app.models.tenant import Tenant  # noqa: PLC0415
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

    factory = async_sessionmaker(repo_engine, expire_on_commit=False)

    async with factory() as session:
        ta = Tenant(slug=f"ta-{uuid.uuid4().hex[:8]}", nombre="Tenant A", activo=True)
        tb = Tenant(slug=f"tb-{uuid.uuid4().hex[:8]}", nombre="Tenant B", activo=True)
        session.add_all([ta, tb])
        await session.commit()
        await session.refresh(ta)
        await session.refresh(tb)
        tid_a, tid_b = ta.id, tb.id

    actor_a = uuid.uuid4()
    actor_b = uuid.uuid4()

    async with factory() as session:
        repo_a = AuditLogRepository(session=session, tenant_id=tid_a)
        repo_b = AuditLogRepository(session=session, tenant_id=tid_b)

        await repo_a.crear(actor_id=actor_a, accion="PADRON_CARGAR", ip=None, user_agent=None)
        await repo_b.crear(actor_id=actor_b, accion="COMUNICACION_ENVIAR", ip=None, user_agent=None)
        await session.commit()

    async with factory() as session:
        repo_a = AuditLogRepository(session=session, tenant_id=tid_a)
        records_a = await repo_a.listar()

    assert len(records_a) == 1
    assert records_a[0].tenant_id == tid_a
    assert records_a[0].actor_id == actor_a

"""
tests/test_audit_service.py — TDD tests for AuditService (Task 6).

Verifies:
  - AuditService.registrar() takes actor_id from CurrentUser.user_id (6.1)
  - detalle is persisted/recovered as JSON without loss (6.2)
  - Without impersonation, impersonado_id is null (6.3)

Requires TEST_DATABASE_URL (PostgreSQL — no mocks).

TDD cycle:
  RED   — written before implementation
  GREEN — audit_service.py created
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

# Skip if no DB available
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping audit_service tests",
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
async def svc_engine() -> AsyncEngine:
    """Function-scoped engine with audit_log schema."""
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
async def svc_session(svc_engine: AsyncEngine) -> AsyncSession:
    """Per-test session, rolled back after each test."""
    factory = async_sessionmaker(svc_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def svc_tenant(svc_session: AsyncSession) -> uuid.UUID:
    """Create a test tenant and return its UUID."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    t = Tenant(slug=f"svc-t-{uuid.uuid4().hex[:8]}", nombre="Svc Tenant", activo=True)
    svc_session.add(t)
    await svc_session.commit()
    await svc_session.refresh(t)
    return t.id


def _make_user(tenant_id: uuid.UUID, user_id: uuid.UUID | None = None, impersonando: uuid.UUID | None = None):
    """Create a CurrentUser DTO for testing."""
    from app.core.auth_context import CurrentUser  # noqa: PLC0415

    return CurrentUser(
        user_id=user_id or uuid.uuid4(),
        tenant_id=tenant_id,
        roles=["ADMIN"],
        impersonando_user_id=impersonando,
    )


# ---------------------------------------------------------------------------
# Task 6.1 — actor_id comes from CurrentUser.user_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registrar_uses_current_user_id_as_actor(
    svc_session: AsyncSession,
    svc_tenant: uuid.UUID,
):
    """registrar() extracts actor_id from current_user.user_id, not a param."""
    from app.services.audit_service import AuditService  # noqa: PLC0415
    from app.services.audit_codes import AccionAuditoria  # noqa: PLC0415

    actor_id = uuid.uuid4()
    current_user = _make_user(svc_tenant, actor_id)
    svc = AuditService(session=svc_session, tenant_id=svc_tenant)

    record = await svc.registrar(
        current_user,
        AccionAuditoria.CALIFICACIONES_IMPORTAR,
        filas_afectadas=10,
        ip="127.0.0.1",
        user_agent="pytest",
    )

    assert record.actor_id == actor_id
    assert record.accion == "CALIFICACIONES_IMPORTAR"
    assert record.filas_afectadas == 10


# ---------------------------------------------------------------------------
# Task 6.2 — detalle is persisted and recovered as JSON
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registrar_persists_detalle_as_json(
    svc_engine: AsyncEngine,
    svc_tenant: uuid.UUID,
):
    """detalle dict is persisted and recovered without loss of structure."""
    from app.services.audit_service import AuditService  # noqa: PLC0415
    from app.services.audit_codes import AccionAuditoria  # noqa: PLC0415
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

    factory = async_sessionmaker(svc_engine, expire_on_commit=False)
    actor_id = uuid.uuid4()
    original_detalle = {"materia": "PROG_I", "version": 3, "nested": {"key": "val"}}

    record_id: uuid.UUID | None = None
    async with factory() as session:
        current_user = _make_user(svc_tenant, actor_id)
        svc = AuditService(session=session, tenant_id=svc_tenant)

        record = await svc.registrar(
            current_user,
            AccionAuditoria.CALIFICACIONES_IMPORTAR,
            detalle=original_detalle,
            ip=None,
            user_agent=None,
        )
        await session.commit()
        record_id = record.id

    # Re-read from a fresh session to verify persistence
    async with factory() as session:
        repo = AuditLogRepository(session=session, tenant_id=svc_tenant)
        fetched = await repo.get(record_id)

    assert fetched is not None
    assert fetched.detalle == original_detalle


# ---------------------------------------------------------------------------
# Task 6.3 — Without impersonation, impersonado_id is null
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registrar_without_impersonation_leaves_impersonado_id_null(
    svc_session: AsyncSession,
    svc_tenant: uuid.UUID,
):
    """Normal session (no impersonation) → impersonado_id is None in audit record."""
    from app.services.audit_service import AuditService  # noqa: PLC0415
    from app.services.audit_codes import AccionAuditoria  # noqa: PLC0415

    current_user = _make_user(svc_tenant)  # no impersonando_user_id
    svc = AuditService(session=svc_session, tenant_id=svc_tenant)

    record = await svc.registrar(
        current_user,
        AccionAuditoria.PADRON_CARGAR,
        ip=None,
        user_agent=None,
    )

    assert record.impersonado_id is None
    assert record.actor_id == current_user.user_id


@pytest.mark.asyncio
async def test_registrar_with_impersonation_sets_impersonado_id(
    svc_session: AsyncSession,
    svc_tenant: uuid.UUID,
):
    """Impersonation session → actor_id = real actor, impersonado_id = impersonated user."""
    from app.services.audit_service import AuditService  # noqa: PLC0415
    from app.services.audit_codes import AccionAuditoria  # noqa: PLC0415

    real_actor = uuid.uuid4()
    impersonado = uuid.uuid4()
    current_user = _make_user(svc_tenant, real_actor, impersonando=impersonado)

    svc = AuditService(session=svc_session, tenant_id=svc_tenant)

    record = await svc.registrar(
        current_user,
        AccionAuditoria.CALIFICACIONES_IMPORTAR,
        ip=None,
        user_agent=None,
    )

    assert record.actor_id == real_actor
    assert record.impersonado_id == impersonado

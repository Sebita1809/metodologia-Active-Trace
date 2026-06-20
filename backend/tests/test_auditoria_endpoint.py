"""
tests/test_auditoria_endpoint.py — TDD tests for audit query endpoint (Task 9).

Verifies:
  - Querying audit without auditoria:ver → 403 (9.1)
  - Scope 'propio' returns only actor_id == own user's records (9.2)
  - Scope 'global' returns all tenant records (9.3)

Requires TEST_DATABASE_URL (PostgreSQL — no mocks).

TDD cycle:
  RED   — written before implementation
  GREEN — auditoria.py router created
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping auditoria_endpoint tests",
)

_SECRET_KEY = "aud" + "x" * 29  # 32 chars
_ENC_KEY = "cd" * 32  # 64 hex chars


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _register_models():
    import app.models.tenant       # noqa: F401
    import app.models.user         # noqa: F401
    import app.models.audit_log    # noqa: F401
    import app.models.rol          # noqa: F401
    import app.models.permiso      # noqa: F401
    import app.models.rol_permiso  # noqa: F401
    import app.models.usuario_rol  # noqa: F401
    import app.features.auth.models  # noqa: F401


def _create_enum_if_not_exists(conn):
    try:
        conn.execute(text("CREATE TYPE alcance_enum AS ENUM ('global', 'propio')"))
    except Exception:
        pass


def _drop_enum(conn):
    try:
        conn.execute(text("DROP TYPE IF EXISTS alcance_enum CASCADE"))
    except Exception:
        pass


@pytest_asyncio.fixture
async def aud_engine() -> AsyncEngine:
    """Full schema with RBAC + audit_log."""
    _register_models()
    url = os.environ["TEST_DATABASE_URL"]
    engine = build_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_drop_enum)
        await conn.run_sync(_create_enum_if_not_exists)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_drop_enum)
    await engine.dispose()


@pytest_asyncio.fixture
async def aud_session(aud_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(aud_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def aud_tenant(aud_session: AsyncSession) -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    from app.services.rbac_seed import seed_rbac_for_tenant  # noqa: PLC0415

    os.environ["SECRET_KEY"] = _SECRET_KEY
    os.environ["ENCRYPTION_KEY"] = _ENC_KEY
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://placeholder/test")
    import app.core.config as cfg  # noqa: PLC0415
    cfg._settings = None

    t = Tenant(slug=f"aud-t-{uuid.uuid4().hex[:8]}", nombre="Aud Tenant", activo=True)
    aud_session.add(t)
    await aud_session.flush()
    await aud_session.refresh(t)
    tid = t.id

    conn = await aud_session.connection()
    await conn.run_sync(seed_rbac_for_tenant, tid)
    await aud_session.commit()
    return tid


def _build_aud_app(engine: AsyncEngine) -> FastAPI:
    """Build a minimal FastAPI app with auditoria router wired to test DB."""
    from app.core.dependencies import get_db  # noqa: PLC0415
    from app.api.v1.routers.auditoria import router as aud_router  # noqa: PLC0415

    factory = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    app = FastAPI(lifespan=noop_lifespan)
    app.include_router(aud_router, prefix="/api/auditoria", tags=["auditoria"])

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    return app


async def _create_user_with_role(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    role_name: str,
) -> uuid.UUID:
    from app.models.user import User  # noqa: PLC0415
    from app.core.security import hash_password  # noqa: PLC0415

    user = User(
        tenant_id=tenant_id,
        email=f"u{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("Test1234!"),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    uid = user.id

    await session.execute(
        text(
            """
            INSERT INTO usuario_rol (id, tenant_id, user_id, rol_id, vigente_desde, created_at, updated_at)
            SELECT gen_random_uuid(), :tid, :uid, r.id, now(), now(), now()
            FROM roles r
            WHERE r.tenant_id = :tid AND r.nombre = :role
            """
        ),
        {"tid": str(tenant_id), "uid": str(uid), "role": role_name},
    )
    await session.commit()
    return uid


async def _insert_audit_record(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
):
    """Insert a raw audit_log record for testing (bypasses the trigger — OK for INSERT)."""
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

    repo = AuditLogRepository(session=session, tenant_id=tenant_id)
    await repo.crear(
        actor_id=actor_id,
        accion="CALIFICACIONES_IMPORTAR",
        ip="127.0.0.1",
        user_agent="pytest",
    )
    await session.commit()


# ---------------------------------------------------------------------------
# Task 9.1 — No permission → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_query_audit_without_permission_returns_403(
    aud_engine: AsyncEngine,
    aud_tenant: uuid.UUID,
):
    """Querying audit log without auditoria:ver returns 403."""
    from app.core.security import create_access_token  # noqa: PLC0415

    factory = async_sessionmaker(aud_engine, expire_on_commit=False)
    async with factory() as session:
        # ALUMNO has no auditoria:ver
        user_id = await _create_user_with_role(session, aud_tenant, "ALUMNO")

    token = create_access_token(
        user_id=user_id,
        tenant_id=aud_tenant,
        roles=["ALUMNO"],
        secret_key=_SECRET_KEY,
        expire_minutes=15,
    )

    app = _build_aud_app(aud_engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/auditoria/",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Task 9.2 — Scope 'propio' returns only own actor's records
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scope_propio_returns_only_own_records(
    aud_engine: AsyncEngine,
    aud_tenant: uuid.UUID,
):
    """COORDINADOR (propio) sees only records where actor_id == their own user_id."""
    from app.core.security import create_access_token  # noqa: PLC0415

    factory = async_sessionmaker(aud_engine, expire_on_commit=False)
    async with factory() as session:
        coord_id = await _create_user_with_role(session, aud_tenant, "COORDINADOR")
        other_id = uuid.uuid4()

        # Insert records: one for coord_id, one for a different actor
        await _insert_audit_record(session, aud_tenant, coord_id)
        # Insert directly for other actor
        repo_factory = async_sessionmaker(aud_engine, expire_on_commit=False)

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415
        repo = AuditLogRepository(session=session, tenant_id=aud_tenant)
        await repo.crear(actor_id=other_id, accion="PADRON_CARGAR", ip=None, user_agent=None)
        await session.commit()

    # COORDINADOR has auditoria:ver with alcance=propio
    token = create_access_token(
        user_id=coord_id,
        tenant_id=aud_tenant,
        roles=["COORDINADOR"],
        secret_key=_SECRET_KEY,
        expire_minutes=15,
    )

    app = _build_aud_app(aud_engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/auditoria/",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    records = resp.json()

    # All returned records must belong to coord_id
    for rec in records:
        assert rec["actor_id"] == str(coord_id), (
            f"'propio' scope should only return records for {coord_id}, got actor_id={rec['actor_id']}"
        )

    # At least one record must exist for coord_id
    assert any(r["actor_id"] == str(coord_id) for r in records), "No records found for the coordinator"

    # The other actor's record must NOT be included
    assert not any(r["actor_id"] == str(other_id) for r in records), (
        f"'propio' scope returned record for a different actor: {other_id}"
    )


# ---------------------------------------------------------------------------
# Task 9.3 — Scope 'global' returns all tenant records
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scope_global_returns_all_tenant_records(
    aud_engine: AsyncEngine,
    aud_tenant: uuid.UUID,
):
    """ADMIN (global) sees all audit records of the tenant."""
    from app.core.security import create_access_token  # noqa: PLC0415

    factory = async_sessionmaker(aud_engine, expire_on_commit=False)

    actor_a = uuid.uuid4()
    actor_b = uuid.uuid4()

    async with factory() as session:
        admin_id = await _create_user_with_role(session, aud_tenant, "ADMIN")

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415
        repo = AuditLogRepository(session=session, tenant_id=aud_tenant)
        await repo.crear(actor_id=actor_a, accion="CALIFICACIONES_IMPORTAR", ip=None, user_agent=None)
        await repo.crear(actor_id=actor_b, accion="PADRON_CARGAR", ip=None, user_agent=None)
        await session.commit()

    token = create_access_token(
        user_id=admin_id,
        tenant_id=aud_tenant,
        roles=["ADMIN"],
        secret_key=_SECRET_KEY,
        expire_minutes=15,
    )

    app = _build_aud_app(aud_engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/auditoria/",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    records = resp.json()

    actor_ids_in_response = {r["actor_id"] for r in records}
    assert str(actor_a) in actor_ids_in_response, f"actor_a record missing: {actor_ids_in_response}"
    assert str(actor_b) in actor_ids_in_response, f"actor_b record missing: {actor_ids_in_response}"

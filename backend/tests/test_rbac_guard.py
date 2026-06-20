"""
tests/test_rbac_guard.py — TDD tests for require_permission guard (Tasks 5.1, 5.4)

TDD RED phase: written before the guard implementation.

Tests:
  5.1 endpoint with require_permission: user with perm passes; without perm → 403 (not 401)
  5.4 scope semantics: propio satisfies propio-scope endpoint; propio does NOT satisfy global-scope

Uses real DB via domain_engine/domain_session (function-scoped, no DB mocks).
Requires TEST_DATABASE_URL.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
import sqlalchemy as sa
from fastapi import FastAPI, Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping guard tests",
)

NOW = datetime.now(tz=timezone.utc)
PAST = NOW - timedelta(hours=1)
FUTURE = NOW + timedelta(days=365)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def guard_engine() -> AsyncEngine:
    import app.models.tenant  # noqa: F401
    import app.models.user  # noqa: F401
    import app.models.rol  # noqa: F401
    import app.models.permiso  # noqa: F401
    import app.models.rol_permiso  # noqa: F401
    import app.models.usuario_rol  # noqa: F401
    import app.features.auth.models  # noqa: F401

    url = os.environ["TEST_DATABASE_URL"]
    engine = build_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_drop_enum)
        await conn.run_sync(_create_enum)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_drop_enum)

    await engine.dispose()


def _create_enum(conn):
    try:
        conn.execute(sa.text("CREATE TYPE alcance_enum AS ENUM ('global', 'propio')"))
    except Exception:
        pass


def _drop_enum(conn):
    try:
        conn.execute(sa.text("DROP TYPE IF EXISTS alcance_enum CASCADE"))
    except Exception:
        pass


@pytest_asyncio.fixture
async def guard_session(guard_engine: AsyncEngine) -> AsyncSession:
    """Per-test async session.

    NOTE: Tests that make HTTP requests with a separate session MUST call
    await session.commit() before making the request so the HTTP handler's
    session can see the test data.
    """
    factory = async_sessionmaker(guard_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Helpers to build test fixtures in DB
# ---------------------------------------------------------------------------

async def _make_tenant(session: AsyncSession) -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=f"g-{uuid.uuid4().hex[:8]}", nombre="Guard Test Tenant", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_user(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.user import User  # noqa: PLC0415
    u = User(
        tenant_id=tid,
        email=f"gu_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="x",
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


async def _make_rol(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.rol import Rol  # noqa: PLC0415
    r = Rol(tenant_id=tid, nombre=f"GRol_{uuid.uuid4().hex[:6]}")
    session.add(r)
    await session.flush()
    await session.refresh(r)
    return r.id


async def _make_permiso(
    session: AsyncSession, tid: uuid.UUID, clave: str
) -> uuid.UUID:
    from app.models.permiso import Permiso  # noqa: PLC0415
    m, a = clave.split(":", 1)
    p = Permiso(tenant_id=tid, clave=clave, modulo=m, accion=a)
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p.id


async def _link(
    session: AsyncSession,
    tid: uuid.UUID,
    rol_id: uuid.UUID,
    perm_id: uuid.UUID,
    alcance: str = "global",
) -> None:
    from app.models.rol_permiso import RolPermiso, AlcanceEnum  # noqa: PLC0415
    rp = RolPermiso(
        tenant_id=tid,
        rol_id=rol_id,
        permiso_id=perm_id,
        alcance=AlcanceEnum.global_ if alcance == "global" else AlcanceEnum.propio,
    )
    session.add(rp)
    await session.flush()


async def _assign(
    session: AsyncSession,
    tid: uuid.UUID,
    uid: uuid.UUID,
    rol_id: uuid.UUID,
) -> None:
    from app.models.usuario_rol import UsuarioRol  # noqa: PLC0415
    ur = UsuarioRol(
        tenant_id=tid,
        user_id=uid,
        rol_id=rol_id,
        vigente_desde=PAST,
        vigente_hasta=None,
    )
    session.add(ur)
    await session.flush()


def _build_test_app(engine: AsyncEngine, user_id: uuid.UUID, tenant_id: uuid.UUID) -> FastAPI:
    """Build a minimal FastAPI app that uses require_permission for testing."""
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.core.dependencies import get_current_user, get_db  # noqa: PLC0415
    from app.core.permissions import require_permission, PermisoConcedido  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: PLC0415

    app = FastAPI()

    # Override get_current_user to return our test user
    def mock_get_current_user() -> CurrentUser:
        return CurrentUser(user_id=user_id, tenant_id=tenant_id, roles=[])

    # Override get_db to use the test engine
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def mock_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db] = mock_get_db

    # Protected endpoint requiring "test:acceder" with global scope
    @app.get("/protected-global")
    async def protected_global(
        perm: PermisoConcedido = Depends(require_permission("test:acceder", scope="global")),
    ):
        return {"ok": True, "alcance": perm.alcance}

    # Protected endpoint requiring "test:acceder" with propio scope
    @app.get("/protected-propio")
    async def protected_propio(
        perm: PermisoConcedido = Depends(require_permission("test:acceder", scope="propio")),
    ):
        return {"ok": True, "alcance": perm.alcance}

    return app


# ---------------------------------------------------------------------------
# 5.1 Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_with_permission_gets_access(
    guard_engine: AsyncEngine,
    guard_session: AsyncSession,
):
    """User with required permission (global) can access the protected endpoint."""
    tid = await _make_tenant(guard_session)
    uid = await _make_user(guard_session, tid)
    rol_id = await _make_rol(guard_session, tid)
    perm_id = await _make_permiso(guard_session, tid, "test:acceder")
    await _link(guard_session, tid, rol_id, perm_id, "global")
    await _assign(guard_session, tid, uid, rol_id)
    await guard_session.commit()  # must commit so HTTP handler's session can see data

    app = _build_test_app(guard_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/protected-global")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_user_without_permission_gets_403(
    guard_engine: AsyncEngine,
    guard_session: AsyncSession,
):
    """User without required permission gets 403 (not 401)."""
    tid = await _make_tenant(guard_session)
    uid = await _make_user(guard_session, tid)
    # No role assigned → no permissions

    app = _build_test_app(guard_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/protected-global")

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_missing_permission_returns_403_not_401(
    guard_engine: AsyncEngine,
    guard_session: AsyncSession,
):
    """The guard returns 403 (authorized but no perm), never 401 (unauthenticated)."""
    tid = await _make_tenant(guard_session)
    uid = await _make_user(guard_session, tid)
    # User is authenticated but has no permissions

    app = _build_test_app(guard_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/protected-global")

    assert resp.status_code != 401, "Guard must return 403, not 401"
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 5.4 Tests — scope semantics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_propio_alcance_satisfies_propio_scope_endpoint(
    guard_engine: AsyncEngine,
    guard_session: AsyncSession,
):
    """A user with 'propio' alcance can access an endpoint declaring scope='propio'."""
    tid = await _make_tenant(guard_session)
    uid = await _make_user(guard_session, tid)
    rol_id = await _make_rol(guard_session, tid)
    perm_id = await _make_permiso(guard_session, tid, "test:acceder")
    await _link(guard_session, tid, rol_id, perm_id, "propio")  # propio alcance
    await _assign(guard_session, tid, uid, rol_id)
    await guard_session.commit()  # commit so HTTP handler's session can see data

    app = _build_test_app(guard_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/protected-propio")

    assert resp.status_code == 200, f"propio should satisfy propio endpoint, got {resp.status_code}"
    assert resp.json()["alcance"] == "propio"


@pytest.mark.asyncio
async def test_propio_alcance_does_not_satisfy_global_scope_endpoint(
    guard_engine: AsyncEngine,
    guard_session: AsyncSession,
):
    """A user with only 'propio' alcance gets 403 on an endpoint requiring global scope."""
    tid = await _make_tenant(guard_session)
    uid = await _make_user(guard_session, tid)
    rol_id = await _make_rol(guard_session, tid)
    perm_id = await _make_permiso(guard_session, tid, "test:acceder")
    await _link(guard_session, tid, rol_id, perm_id, "propio")  # only propio
    await _assign(guard_session, tid, uid, rol_id)
    await guard_session.commit()  # commit so HTTP handler's session can see data

    app = _build_test_app(guard_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/protected-global")

    assert resp.status_code == 403, f"propio should NOT satisfy global endpoint, got {resp.status_code}"


@pytest.mark.asyncio
async def test_global_alcance_satisfies_propio_scope_endpoint(
    guard_engine: AsyncEngine,
    guard_session: AsyncSession,
):
    """A user with 'global' alcance can also access an endpoint declaring scope='propio'."""
    tid = await _make_tenant(guard_session)
    uid = await _make_user(guard_session, tid)
    rol_id = await _make_rol(guard_session, tid)
    perm_id = await _make_permiso(guard_session, tid, "test:acceder")
    await _link(guard_session, tid, rol_id, perm_id, "global")
    await _assign(guard_session, tid, uid, rol_id)
    await guard_session.commit()  # commit so HTTP handler's session can see data

    app = _build_test_app(guard_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/protected-propio")

    assert resp.status_code == 200, f"global should satisfy propio endpoint, got {resp.status_code}"
    assert resp.json()["alcance"] == "global"


@pytest.mark.asyncio
async def test_handler_receives_granted_alcance(
    guard_engine: AsyncEngine,
    guard_session: AsyncSession,
):
    """When guard passes, the handler receives PermisoConcedido with the actual alcance."""
    tid = await _make_tenant(guard_session)
    uid = await _make_user(guard_session, tid)
    rol_id = await _make_rol(guard_session, tid)
    perm_id = await _make_permiso(guard_session, tid, "test:acceder")
    await _link(guard_session, tid, rol_id, perm_id, "propio")
    await _assign(guard_session, tid, uid, rol_id)
    await guard_session.commit()  # commit so HTTP handler's session can see data

    app = _build_test_app(guard_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/protected-propio")

    assert resp.status_code == 200
    data = resp.json()
    assert data["alcance"] == "propio", f"Expected alcance=propio, got {data['alcance']}"

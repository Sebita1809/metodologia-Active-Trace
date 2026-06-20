"""
tests/test_rbac_admin.py — Integration tests for RBAC admin API (Task 6.4)

Tests:
  - User without rbac:administrar → 403 on all admin endpoints (anti-privilege escalation)
  - ADMIN (with rbac:administrar) can edit the matrix
  - Changes to the matrix take effect immediately in permission resolution (no token reissue)

Requires TEST_DATABASE_URL (PostgreSQL).
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
    reason="TEST_DATABASE_URL not set — skipping RBAC admin tests",
)

NOW = datetime.now(tz=timezone.utc)
PAST = NOW - timedelta(hours=1)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def admin_engine() -> AsyncEngine:
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
async def admin_session(admin_engine: AsyncEngine) -> AsyncSession:
    """Per-test async session.

    NOTE: Tests that make HTTP requests with a separate session MUST call
    await session.commit() before making the request so the HTTP handler's
    session can see the test data.
    """
    factory = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _make_tenant(session: AsyncSession) -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=f"adm-{uuid.uuid4().hex[:8]}", nombre="Admin Test", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_user(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.user import User  # noqa: PLC0415
    u = User(
        tenant_id=tid,
        email=f"adm_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="x",
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


async def _make_rol(session: AsyncSession, tid: uuid.UUID, nombre: str) -> uuid.UUID:
    from app.models.rol import Rol  # noqa: PLC0415
    r = Rol(tenant_id=tid, nombre=nombre)
    session.add(r)
    await session.flush()
    await session.refresh(r)
    return r.id


async def _make_permiso(session: AsyncSession, tid: uuid.UUID, clave: str) -> uuid.UUID:
    from app.models.permiso import Permiso  # noqa: PLC0415
    m, a = clave.split(":", 1)
    p = Permiso(tenant_id=tid, clave=clave, modulo=m, accion=a)
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p.id


async def _assign_perm(
    session: AsyncSession, tid: uuid.UUID,
    rol_id: uuid.UUID, perm_id: uuid.UUID, alcance: str = "global"
) -> None:
    from app.models.rol_permiso import RolPermiso, AlcanceEnum  # noqa: PLC0415
    rp = RolPermiso(
        tenant_id=tid, rol_id=rol_id, permiso_id=perm_id,
        alcance=AlcanceEnum.global_ if alcance == "global" else AlcanceEnum.propio,
    )
    session.add(rp)
    await session.flush()


async def _assign_rol(
    session: AsyncSession, tid: uuid.UUID, uid: uuid.UUID, rol_id: uuid.UUID
) -> None:
    from app.models.usuario_rol import UsuarioRol  # noqa: PLC0415
    ur = UsuarioRol(tenant_id=tid, user_id=uid, rol_id=rol_id, vigente_desde=PAST)
    session.add(ur)
    await session.flush()


def _build_rbac_app(engine: AsyncEngine, uid: uuid.UUID, tid: uuid.UUID) -> FastAPI:
    """Build a minimal FastAPI app with only the RBAC router mounted.

    Avoids importing create_app() which has a pre-existing auth router issue
    (C-03 forward-ref bug unrelated to C-04).
    """
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.core.dependencies import get_current_user, get_db  # noqa: PLC0415
    from app.api.v1.routers.rbac import router as rbac_router  # noqa: PLC0415

    app = FastAPI()

    def mock_user() -> CurrentUser:
        return CurrentUser(user_id=uid, tenant_id=tid, roles=[])

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def mock_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_db] = mock_db

    app.include_router(rbac_router, prefix="/api/rbac", tags=["rbac"])
    return app


# ---------------------------------------------------------------------------
# 6.4 Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_without_rbac_administrar_gets_403_on_roles_list(
    admin_engine: AsyncEngine,
    admin_session: AsyncSession,
):
    """A user without rbac:administrar cannot list roles — gets 403."""
    tid = await _make_tenant(admin_session)
    uid = await _make_user(admin_session, tid)
    # No rbac:administrar assigned
    await admin_session.commit()

    app = _build_rbac_app(admin_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/rbac/roles")

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_user_without_rbac_administrar_cannot_create_rol(
    admin_engine: AsyncEngine,
    admin_session: AsyncSession,
):
    """A user without rbac:administrar cannot create a role — gets 403 (anti-escalation)."""
    tid = await _make_tenant(admin_session)
    uid = await _make_user(admin_session, tid)
    # No role assigned → no permissions
    await admin_session.commit()

    app = _build_rbac_app(admin_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/rbac/roles",
            json={"nombre": "ESCALADA", "descripcion": None},
        )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_admin_can_create_and_list_roles(
    admin_engine: AsyncEngine,
    admin_session: AsyncSession,
):
    """ADMIN (with rbac:administrar) can create a new role and list it."""
    tid = await _make_tenant(admin_session)
    uid = await _make_user(admin_session, tid)
    admin_rol_id = await _make_rol(admin_session, tid, f"ADMIN_{uuid.uuid4().hex[:6]}")
    rbac_perm_id = await _make_permiso(admin_session, tid, "rbac:administrar")
    await _assign_perm(admin_session, tid, admin_rol_id, rbac_perm_id, "global")
    await _assign_rol(admin_session, tid, uid, admin_rol_id)
    await admin_session.commit()  # commit so HTTP handler can see permissions

    app = _build_rbac_app(admin_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/rbac/roles",
            json={"nombre": f"NUEVO_{uuid.uuid4().hex[:6]}", "descripcion": "Test role"},
        )
        assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.text}"

        list_resp = await client.get("/api/rbac/roles")
        assert list_resp.status_code == 200


@pytest.mark.asyncio
async def test_matrix_change_takes_effect_immediately_without_reissuing_token(
    admin_engine: AsyncEngine,
    admin_session: AsyncSession,
):
    """After ADMIN assigns a new permission, it takes effect immediately (no token reissue)."""
    from app.services.rbac_service import RbacService  # noqa: PLC0415

    tid = await _make_tenant(admin_session)
    # Regular user with a role
    uid = await _make_user(admin_session, tid)
    user_rol_id = await _make_rol(admin_session, tid, f"USERROLE_{uuid.uuid4().hex[:6]}")
    await _assign_rol(admin_session, tid, uid, user_rol_id)

    # Create a new permission
    new_perm_id = await _make_permiso(admin_session, tid, "test:nueva_capacidad")

    await admin_session.flush()

    # Before assignment: user should NOT have the permission
    svc = RbacService(session=admin_session)
    perms_before = await svc.resolver_permisos_efectivos(uid, tid, NOW)
    assert "test:nueva_capacidad" not in perms_before

    # Now assign the new permission to user's role
    await _assign_perm(admin_session, tid, user_rol_id, new_perm_id, "global")
    await admin_session.flush()

    # After assignment: user should now have the permission (same session, no token reissue)
    perms_after = await svc.resolver_permisos_efectivos(uid, tid, NOW)
    assert "test:nueva_capacidad" in perms_after, (
        "New permission should take effect immediately after matrix change"
    )
    assert perms_after["test:nueva_capacidad"] == "global"


@pytest.mark.asyncio
async def test_user_without_rbac_cannot_modify_matrix(
    admin_engine: AsyncEngine,
    admin_session: AsyncSession,
):
    """A user without rbac:administrar cannot assign permissions to roles."""
    tid = await _make_tenant(admin_session)
    uid = await _make_user(admin_session, tid)
    # User has some role but NOT rbac:administrar
    basic_rol_id = await _make_rol(admin_session, tid, f"BASIC_{uuid.uuid4().hex[:6]}")
    await _assign_rol(admin_session, tid, uid, basic_rol_id)

    target_rol_id = await _make_rol(admin_session, tid, f"TARGET_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(admin_session, tid, "test:sensitive")
    await admin_session.commit()  # commit so HTTP handler can see assignments

    app = _build_rbac_app(admin_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/rbac/roles/{target_rol_id}/permisos",
            json={"permiso_id": str(perm_id), "alcance": "global"},
        )

    assert resp.status_code == 403, f"Expected 403 (no privilege escalation), got {resp.status_code}"

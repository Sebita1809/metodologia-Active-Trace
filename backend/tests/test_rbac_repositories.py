"""
tests/test_rbac_repositories.py — TDD tests for RBAC repositories (Task 3.2)

Verifies tenant isolation: a repo scoped to tenant A cannot see rows belonging
to tenant B. Tests use a real ephemeral database (no DB mocks).

Requires TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping RBAC repository tests",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def rbac_repo_engine() -> AsyncEngine:
    """Function-scoped engine with the full RBAC schema."""
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
async def rbac_repo_session(rbac_repo_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(rbac_repo_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def two_rbac_tenants(rbac_repo_session: AsyncSession):
    """Create two tenants and return (tid_a, tid_b)."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    t_a = Tenant(slug=f"rbac-a-{uuid.uuid4().hex[:6]}", nombre="RBAC Tenant A", activo=True)
    t_b = Tenant(slug=f"rbac-b-{uuid.uuid4().hex[:6]}", nombre="RBAC Tenant B", activo=True)
    rbac_repo_session.add_all([t_a, t_b])
    await rbac_repo_session.flush()
    await rbac_repo_session.refresh(t_a)
    await rbac_repo_session.refresh(t_b)
    return t_a.id, t_b.id


# ---------------------------------------------------------------------------
# RolRepository isolation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rol_repo_tenant_isolation(
    rbac_repo_session: AsyncSession,
    two_rbac_tenants: tuple[uuid.UUID, uuid.UUID],
):
    """RolRepository scoped to tenant A does not return tenant B's roles."""
    from app.models.rol import Rol  # noqa: PLC0415
    from app.repositories.roles import RolRepository  # noqa: PLC0415

    tid_a, tid_b = two_rbac_tenants

    rol_a = Rol(tenant_id=tid_a, nombre="ROL_A_ONLY")
    rol_b = Rol(tenant_id=tid_b, nombre="ROL_B_ONLY")
    rbac_repo_session.add_all([rol_a, rol_b])
    await rbac_repo_session.flush()

    repo_a = RolRepository(session=rbac_repo_session, tenant_id=tid_a)
    results = await repo_a.list()
    nombres = [r.nombre for r in results]

    assert "ROL_A_ONLY" in nombres
    assert "ROL_B_ONLY" not in nombres


@pytest.mark.asyncio
async def test_rol_repo_get_other_tenant_returns_none(
    rbac_repo_session: AsyncSession,
    two_rbac_tenants: tuple[uuid.UUID, uuid.UUID],
):
    """RolRepository.get() of another tenant's Rol returns None."""
    from app.models.rol import Rol  # noqa: PLC0415
    from app.repositories.roles import RolRepository  # noqa: PLC0415

    tid_a, tid_b = two_rbac_tenants

    rol_b = Rol(tenant_id=tid_b, nombre="ONLY_B")
    rbac_repo_session.add(rol_b)
    await rbac_repo_session.flush()
    await rbac_repo_session.refresh(rol_b)

    repo_a = RolRepository(session=rbac_repo_session, tenant_id=tid_a)
    result = await repo_a.get(rol_b.id)
    assert result is None


# ---------------------------------------------------------------------------
# PermisoRepository isolation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_permiso_repo_tenant_isolation(
    rbac_repo_session: AsyncSession,
    two_rbac_tenants: tuple[uuid.UUID, uuid.UUID],
):
    """PermisoRepository scoped to tenant A does not return tenant B's permisos."""
    from app.models.permiso import Permiso  # noqa: PLC0415
    from app.repositories.permisos import PermisoRepository  # noqa: PLC0415

    tid_a, tid_b = two_rbac_tenants

    p_a = Permiso(tenant_id=tid_a, clave="modA:accion", modulo="modA", accion="accion")
    p_b = Permiso(tenant_id=tid_b, clave="modB:accion", modulo="modB", accion="accion")
    rbac_repo_session.add_all([p_a, p_b])
    await rbac_repo_session.flush()

    repo_a = PermisoRepository(session=rbac_repo_session, tenant_id=tid_a)
    results = await repo_a.list()
    claves = [p.clave for p in results]

    assert "modA:accion" in claves
    assert "modB:accion" not in claves


# ---------------------------------------------------------------------------
# UsuarioRolRepository — vigentes filtering
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_usuario_rol_repo_vigentes_excludes_expired(
    rbac_repo_session: AsyncSession,
    two_rbac_tenants: tuple[uuid.UUID, uuid.UUID],
):
    """list_vigentes() does not return expired assignments."""
    from app.models.user import User  # noqa: PLC0415
    from app.models.rol import Rol  # noqa: PLC0415
    from app.models.usuario_rol import UsuarioRol  # noqa: PLC0415
    from app.repositories.usuario_rol import UsuarioRolRepository  # noqa: PLC0415

    tid_a, _ = two_rbac_tenants

    user = User(tenant_id=tid_a, email=f"u_{uuid.uuid4().hex[:6]}@test.com", password_hash="x")
    rol = Rol(tenant_id=tid_a, nombre=f"ROL_{uuid.uuid4().hex[:6]}")
    rbac_repo_session.add_all([user, rol])
    await rbac_repo_session.flush()
    await rbac_repo_session.refresh(user)
    await rbac_repo_session.refresh(rol)

    past = datetime(2020, 1, 1, tzinfo=timezone.utc)
    past_end = datetime(2021, 1, 1, tzinfo=timezone.utc)

    # Expired assignment
    expired = UsuarioRol(
        tenant_id=tid_a,
        user_id=user.id,
        rol_id=rol.id,
        vigente_desde=past,
        vigente_hasta=past_end,  # already past
    )
    rbac_repo_session.add(expired)
    await rbac_repo_session.flush()

    ahora = datetime.now(tz=timezone.utc)
    repo = UsuarioRolRepository(session=rbac_repo_session, tenant_id=tid_a)
    vigentes = await repo.list_vigentes(user.id, ahora)

    assert len(vigentes) == 0, "Expired assignment should not be in vigentes"


@pytest.mark.asyncio
async def test_usuario_rol_repo_tenant_isolation(
    rbac_repo_session: AsyncSession,
    two_rbac_tenants: tuple[uuid.UUID, uuid.UUID],
):
    """UsuarioRolRepository scoped to tenant A does not see tenant B's assignments."""
    from app.models.user import User  # noqa: PLC0415
    from app.models.rol import Rol  # noqa: PLC0415
    from app.models.usuario_rol import UsuarioRol  # noqa: PLC0415
    from app.repositories.usuario_rol import UsuarioRolRepository  # noqa: PLC0415

    tid_a, tid_b = two_rbac_tenants

    user_a = User(tenant_id=tid_a, email=f"ua_{uuid.uuid4().hex[:6]}@test.com", password_hash="x")
    user_b = User(tenant_id=tid_b, email=f"ub_{uuid.uuid4().hex[:6]}@test.com", password_hash="x")
    rol_a = Rol(tenant_id=tid_a, nombre=f"RA_{uuid.uuid4().hex[:6]}")
    rol_b = Rol(tenant_id=tid_b, nombre=f"RB_{uuid.uuid4().hex[:6]}")
    rbac_repo_session.add_all([user_a, user_b, rol_a, rol_b])
    await rbac_repo_session.flush()
    for obj in [user_a, user_b, rol_a, rol_b]:
        await rbac_repo_session.refresh(obj)

    past = datetime(2020, 1, 1, tzinfo=timezone.utc)

    assignment_b = UsuarioRol(
        tenant_id=tid_b,
        user_id=user_b.id,
        rol_id=rol_b.id,
        vigente_desde=past,
        vigente_hasta=None,
    )
    rbac_repo_session.add(assignment_b)
    await rbac_repo_session.flush()
    await rbac_repo_session.refresh(assignment_b)

    # Repo A tries to get assignment_b — must return None
    repo_a = UsuarioRolRepository(session=rbac_repo_session, tenant_id=tid_a)
    result = await repo_a.get(assignment_b.id)
    assert result is None, "Tenant A repo must not see tenant B assignment"

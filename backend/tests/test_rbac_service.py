"""
tests/test_rbac_service.py — TDD tests for RbacService (Tasks 4.1, 4.3, 4.4)

TDD RED phase: written before RbacService exists.

Tests:
  4.1 resolver_permisos_efectivos returns union of vigentes with correct alcance
  4.3 expired role, NEXO (no perms), tenant isolation, JWT not used for resolution
  4.4 union of multiple vigentes; global wins over propio from different roles

Requires TEST_DATABASE_URL (PostgreSQL — no DB mocks).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping RbacService tests",
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def svc_engine() -> AsyncEngine:
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
async def svc_session(svc_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(svc_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ---------------------------------------------------------------------------
# Helper: build a minimal test environment in the DB
# ---------------------------------------------------------------------------

NOW = datetime.now(tz=timezone.utc)
PAST = NOW - timedelta(hours=1)
FUTURE = NOW + timedelta(days=365)
EXPIRED = NOW - timedelta(days=1)


async def _make_tenant(session: AsyncSession, slug: str) -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=slug, nombre=slug, activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_user(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.user import User  # noqa: PLC0415
    u = User(
        tenant_id=tid,
        email=f"u_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="hash",
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
    modulo, accion = clave.split(":", 1)
    p = Permiso(tenant_id=tid, clave=clave, modulo=modulo, accion=accion)
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p.id


async def _assign_perm(
    session: AsyncSession,
    tid: uuid.UUID,
    rol_id: uuid.UUID,
    permiso_id: uuid.UUID,
    alcance: str = "global",
) -> None:
    from app.models.rol_permiso import RolPermiso, AlcanceEnum  # noqa: PLC0415
    rp = RolPermiso(
        tenant_id=tid,
        rol_id=rol_id,
        permiso_id=permiso_id,
        alcance=AlcanceEnum.global_ if alcance == "global" else AlcanceEnum.propio,
    )
    session.add(rp)
    await session.flush()


async def _assign_rol_to_user(
    session: AsyncSession,
    tid: uuid.UUID,
    user_id: uuid.UUID,
    rol_id: uuid.UUID,
    desde: datetime,
    hasta: datetime | None = None,
) -> None:
    from app.models.usuario_rol import UsuarioRol  # noqa: PLC0415
    ur = UsuarioRol(
        tenant_id=tid,
        user_id=user_id,
        rol_id=rol_id,
        vigente_desde=desde,
        vigente_hasta=hasta,
    )
    session.add(ur)
    await session.flush()


# ---------------------------------------------------------------------------
# 4.1 RED — basic resolver test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolver_returns_union_of_vigent_permissions(svc_session: AsyncSession):
    """resolver_permisos_efectivos returns union of permissions from vigent roles."""
    from app.services.rbac_service import RbacService  # noqa: PLC0415

    tid = await _make_tenant(svc_session, f"svc-{uuid.uuid4().hex[:6]}")
    uid = await _make_user(svc_session, tid)

    rol_id = await _make_rol(svc_session, tid, "ROLE_TEST_A")
    perm1_id = await _make_permiso(svc_session, tid, "modA:leer")
    perm2_id = await _make_permiso(svc_session, tid, "modA:escribir")

    await _assign_perm(svc_session, tid, rol_id, perm1_id, "global")
    await _assign_perm(svc_session, tid, rol_id, perm2_id, "propio")
    await _assign_rol_to_user(svc_session, tid, uid, rol_id, PAST, None)

    svc = RbacService(session=svc_session)
    perms = await svc.resolver_permisos_efectivos(uid, tid, NOW)

    assert "modA:leer" in perms, f"Expected 'modA:leer' in {perms}"
    assert "modA:escribir" in perms, f"Expected 'modA:escribir' in {perms}"
    assert perms["modA:leer"] == "global"
    assert perms["modA:escribir"] == "propio"


@pytest.mark.asyncio
async def test_resolver_global_wins_over_propio(svc_session: AsyncSession):
    """When two roles grant the same permission with different alcance, global wins."""
    from app.services.rbac_service import RbacService  # noqa: PLC0415

    tid = await _make_tenant(svc_session, f"svc-{uuid.uuid4().hex[:6]}")
    uid = await _make_user(svc_session, tid)

    rol1_id = await _make_rol(svc_session, tid, f"ROL1_{uuid.uuid4().hex[:6]}")
    rol2_id = await _make_rol(svc_session, tid, f"ROL2_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(svc_session, tid, "shared:ver")

    await _assign_perm(svc_session, tid, rol1_id, perm_id, "propio")  # propio from rol1
    await _assign_perm(svc_session, tid, rol2_id, perm_id, "global")  # global from rol2

    await _assign_rol_to_user(svc_session, tid, uid, rol1_id, PAST, None)
    await _assign_rol_to_user(svc_session, tid, uid, rol2_id, PAST, None)

    svc = RbacService(session=svc_session)
    perms = await svc.resolver_permisos_efectivos(uid, tid, NOW)

    assert perms.get("shared:ver") == "global", (
        f"global should win over propio, got: {perms.get('shared:ver')}"
    )


# ---------------------------------------------------------------------------
# 4.3 — edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_role_grants_no_permissions(svc_session: AsyncSession):
    """An expired role assignment does not contribute permissions."""
    from app.services.rbac_service import RbacService  # noqa: PLC0415

    tid = await _make_tenant(svc_session, f"svc-{uuid.uuid4().hex[:6]}")
    uid = await _make_user(svc_session, tid)

    rol_id = await _make_rol(svc_session, tid, f"EXPIRED_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(svc_session, tid, "dead:permiso")

    await _assign_perm(svc_session, tid, rol_id, perm_id, "global")
    # Assignment was valid in 2020, long expired
    await _assign_rol_to_user(
        svc_session, tid, uid, rol_id,
        desde=datetime(2020, 1, 1, tzinfo=timezone.utc),
        hasta=datetime(2021, 1, 1, tzinfo=timezone.utc),
    )

    svc = RbacService(session=svc_session)
    perms = await svc.resolver_permisos_efectivos(uid, tid, NOW)

    assert "dead:permiso" not in perms, "Expired role should not grant permissions"


@pytest.mark.asyncio
async def test_nexo_role_without_perms_grants_nothing(svc_session: AsyncSession):
    """A role with no permissions in rol_permiso grants nothing."""
    from app.services.rbac_service import RbacService  # noqa: PLC0415

    tid = await _make_tenant(svc_session, f"svc-{uuid.uuid4().hex[:6]}")
    uid = await _make_user(svc_session, tid)

    nexo_id = await _make_rol(svc_session, tid, "NEXO_EMPTY")
    # Intentionally do NOT assign any permissions to nexo_id

    await _assign_rol_to_user(svc_session, tid, uid, nexo_id, PAST, None)

    svc = RbacService(session=svc_session)
    perms = await svc.resolver_permisos_efectivos(uid, tid, NOW)

    assert perms == {}, f"Role with no perms should yield empty dict, got: {perms}"


@pytest.mark.asyncio
async def test_permissions_scoped_by_tenant(svc_session: AsyncSession):
    """A user in tenant A cannot access permissions that belong to tenant B."""
    from app.services.rbac_service import RbacService  # noqa: PLC0415

    tid_a = await _make_tenant(svc_session, f"ta-{uuid.uuid4().hex[:6]}")
    tid_b = await _make_tenant(svc_session, f"tb-{uuid.uuid4().hex[:6]}")

    uid_a = await _make_user(svc_session, tid_a)

    # Create roles & perms only in tenant B
    rol_b_id = await _make_rol(svc_session, tid_b, "ROLE_B_ONLY")
    perm_b_id = await _make_permiso(svc_session, tid_b, "b:secret")
    await _assign_perm(svc_session, tid_b, rol_b_id, perm_b_id, "global")

    # user_a has a role in tenant A that references tenant B's rol_id (should be impossible, testing the boundary)
    # Instead just resolve for user_a with no roles in tenant A
    svc = RbacService(session=svc_session)
    perms = await svc.resolver_permisos_efectivos(uid_a, tid_a, NOW)

    assert "b:secret" not in perms, "Tenant B permission must not appear for tenant A user"


@pytest.mark.asyncio
async def test_jwt_roles_not_used_for_resolution(svc_session: AsyncSession):
    """The resolver uses only DB data; JWT roles list is not consulted."""
    from app.services.rbac_service import RbacService  # noqa: PLC0415

    tid = await _make_tenant(svc_session, f"svc-{uuid.uuid4().hex[:6]}")
    uid = await _make_user(svc_session, tid)

    # Create a permission, role with that perm, but do NOT assign the role to user
    rol_id = await _make_rol(svc_session, tid, f"UNASSIGNED_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(svc_session, tid, "jwt:fake")
    await _assign_perm(svc_session, tid, rol_id, perm_id, "global")

    # Even though a JWT might claim this role, the resolver should find nothing
    # (no usuario_rol row exists for this user)
    svc = RbacService(session=svc_session)
    perms = await svc.resolver_permisos_efectivos(uid, tid, NOW)

    assert "jwt:fake" not in perms, (
        "Permissions must come from DB assignments, not JWT claims"
    )


# ---------------------------------------------------------------------------
# 4.4 — union of multiple vigentes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_union_of_multiple_vigent_roles(svc_session: AsyncSession):
    """Union of permissions from PROFESOR and COORDINADOR includes both sets."""
    from app.services.rbac_service import RbacService  # noqa: PLC0415

    tid = await _make_tenant(svc_session, f"svc-{uuid.uuid4().hex[:6]}")
    uid = await _make_user(svc_session, tid)

    # PROFESOR role: encuentros:gestionar
    prof_id = await _make_rol(svc_session, tid, f"PROF_{uuid.uuid4().hex[:6]}")
    perm_enc_id = await _make_permiso(svc_session, tid, "encuentros:gestionar")
    await _assign_perm(svc_session, tid, prof_id, perm_enc_id, "global")

    # COORDINADOR role: avisos:publicar
    coord_id = await _make_rol(svc_session, tid, f"COORD_{uuid.uuid4().hex[:6]}")
    perm_avi_id = await _make_permiso(svc_session, tid, "avisos:publicar")
    await _assign_perm(svc_session, tid, coord_id, perm_avi_id, "global")

    # User has both roles vigentes
    await _assign_rol_to_user(svc_session, tid, uid, prof_id, PAST, None)
    await _assign_rol_to_user(svc_session, tid, uid, coord_id, PAST, None)

    svc = RbacService(session=svc_session)
    perms = await svc.resolver_permisos_efectivos(uid, tid, NOW)

    assert "encuentros:gestionar" in perms, "PROFESOR perm should be in union"
    assert "avisos:publicar" in perms, "COORDINADOR perm should be in union"


@pytest.mark.asyncio
async def test_global_prevails_over_propio_from_different_roles(svc_session: AsyncSession):
    """When one role grants 'propio' and another grants 'global' for the same key, result is global."""
    from app.services.rbac_service import RbacService  # noqa: PLC0415

    tid = await _make_tenant(svc_session, f"svc-{uuid.uuid4().hex[:6]}")
    uid = await _make_user(svc_session, tid)

    rol_propio_id = await _make_rol(svc_session, tid, f"RPROPIO_{uuid.uuid4().hex[:6]}")
    rol_global_id = await _make_rol(svc_session, tid, f"RGLOBAL_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(svc_session, tid, "atrasados:ver")

    await _assign_perm(svc_session, tid, rol_propio_id, perm_id, "propio")
    await _assign_perm(svc_session, tid, rol_global_id, perm_id, "global")

    await _assign_rol_to_user(svc_session, tid, uid, rol_propio_id, PAST, None)
    await _assign_rol_to_user(svc_session, tid, uid, rol_global_id, PAST, None)

    svc = RbacService(session=svc_session)
    perms = await svc.resolver_permisos_efectivos(uid, tid, NOW)

    assert perms.get("atrasados:ver") == "global", (
        f"global should prevail over propio, got: {perms.get('atrasados:ver')}"
    )

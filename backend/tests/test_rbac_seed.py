"""
tests/test_rbac_seed.py — TDD tests for rbac_seed.py (Task 2.4)

Verifies:
  - Seed plants 7 domain roles for the tenant
  - Seed plants the base permission matrix
  - Re-running seed does not duplicate rows (idempotence)
  - NEXO has no permissions assigned
  - ADMIN has impersonacion:usar

Requires TEST_DATABASE_URL (PostgreSQL — no DB mocks).

TDD cycle:
  RED   — written before seed implementation; tests import seed and check DB
  GREEN — seed implemented in rbac_seed.py
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

# Skip if no DB
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping rbac_seed tests",
)


# ---------------------------------------------------------------------------
# Fixtures (function-scoped to avoid event_loop scope mismatch)
# ---------------------------------------------------------------------------

def _register_models():
    import app.models.tenant  # noqa: F401
    import app.models.user  # noqa: F401
    import app.models.rol  # noqa: F401
    import app.models.permiso  # noqa: F401
    import app.models.rol_permiso  # noqa: F401
    import app.models.usuario_rol  # noqa: F401
    import app.features.auth.models  # noqa: F401


def _create_enum(conn):
    try:
        conn.execute(sa.text("CREATE TYPE alcance_enum AS ENUM ('global', 'propio')"))
    except Exception:
        pass  # already exists


def _drop_enum(conn):
    try:
        conn.execute(sa.text("DROP TYPE IF EXISTS alcance_enum CASCADE"))
    except Exception:
        pass


@pytest_asyncio.fixture
async def seed_engine() -> AsyncEngine:
    """Function-scoped engine with full RBAC schema."""
    _register_models()
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


@pytest_asyncio.fixture
async def seed_session(seed_engine: AsyncEngine) -> AsyncSession:
    """Per-test async session."""
    factory = async_sessionmaker(seed_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def seeded_tenant(seed_session: AsyncSession) -> uuid.UUID:
    """Create a tenant, run the seed, and return the tenant_id."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    t = Tenant(slug=f"test-seed-{uuid.uuid4().hex[:8]}", nombre="Seed Test", activo=True)
    seed_session.add(t)
    await seed_session.flush()
    await seed_session.refresh(t)
    tid = t.id

    # Run the sync seed via run_sync
    from app.services.rbac_seed import seed_rbac_for_tenant  # noqa: PLC0415
    conn = await seed_session.connection()
    await conn.run_sync(seed_rbac_for_tenant, tid)
    await seed_session.flush()

    return tid


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

async def _count_roles(session: AsyncSession, tenant_id: uuid.UUID) -> int:
    result = await session.execute(
        sa.text("SELECT COUNT(*) FROM roles WHERE tenant_id = :tid AND deleted_at IS NULL"),
        {"tid": str(tenant_id)},
    )
    return result.scalar_one()


async def _count_permissions(session: AsyncSession, tenant_id: uuid.UUID) -> int:
    result = await session.execute(
        sa.text("SELECT COUNT(*) FROM permisos WHERE tenant_id = :tid AND deleted_at IS NULL"),
        {"tid": str(tenant_id)},
    )
    return result.scalar_one()


async def _count_matrix_rows(session: AsyncSession, tenant_id: uuid.UUID) -> int:
    result = await session.execute(
        sa.text("SELECT COUNT(*) FROM rol_permiso WHERE tenant_id = :tid AND deleted_at IS NULL"),
        {"tid": str(tenant_id)},
    )
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seed_creates_seven_domain_roles(seeded_tenant: uuid.UUID, seed_session: AsyncSession):
    """After seeding, exactly 7 domain roles exist for the tenant."""
    count = await _count_roles(seed_session, seeded_tenant)
    assert count == 7, f"Expected 7 roles, got {count}"


@pytest.mark.asyncio
async def test_seed_creates_expected_role_names(seeded_tenant: uuid.UUID, seed_session: AsyncSession):
    """All 7 domain role names are present."""
    result = await seed_session.execute(
        sa.text("SELECT nombre FROM roles WHERE tenant_id = :tid AND deleted_at IS NULL"),
        {"tid": str(seeded_tenant)},
    )
    nombres = {row[0] for row in result}
    expected = {"ALUMNO", "TUTOR", "PROFESOR", "COORDINADOR", "NEXO", "ADMIN", "FINANZAS"}
    assert expected == nombres, f"Role names mismatch: {nombres}"


@pytest.mark.asyncio
async def test_seed_creates_permissions(seeded_tenant: uuid.UUID, seed_session: AsyncSession):
    """After seeding, at least the expected permissions exist for the tenant."""
    count = await _count_permissions(seed_session, seeded_tenant)
    assert count >= 20, f"Expected at least 20 permissions, got {count}"


@pytest.mark.asyncio
async def test_seed_creates_matrix_rows(seeded_tenant: uuid.UUID, seed_session: AsyncSession):
    """After seeding, matrix rows exist linking roles to permissions."""
    count = await _count_matrix_rows(seed_session, seeded_tenant)
    assert count > 0, "Expected matrix rows to be seeded"


@pytest.mark.asyncio
async def test_nexo_has_no_permissions(seeded_tenant: uuid.UUID, seed_session: AsyncSession):
    """NEXO is seeded with no permission assignments (OQ-C04-01 / PA-25 unresolved)."""
    result = await seed_session.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM rol_permiso rp
            JOIN roles r ON r.id = rp.rol_id
            WHERE r.tenant_id = :tid AND r.nombre = 'NEXO'
              AND rp.tenant_id = :tid AND rp.deleted_at IS NULL
            """
        ),
        {"tid": str(seeded_tenant)},
    )
    count = result.scalar_one()
    assert count == 0, f"NEXO should have no permissions, got {count}"


@pytest.mark.asyncio
async def test_admin_has_impersonacion_usar(seeded_tenant: uuid.UUID, seed_session: AsyncSession):
    """ADMIN is assigned impersonacion:usar (OQ-C04-03)."""
    result = await seed_session.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM rol_permiso rp
            JOIN roles r ON r.id = rp.rol_id
            JOIN permisos p ON p.id = rp.permiso_id
            WHERE r.tenant_id = :tid AND r.nombre = 'ADMIN'
              AND p.tenant_id = :tid AND p.clave = 'impersonacion:usar'
              AND rp.deleted_at IS NULL
            """
        ),
        {"tid": str(seeded_tenant)},
    )
    count = result.scalar_one()
    assert count == 1, "ADMIN should have impersonacion:usar assigned"


@pytest.mark.asyncio
async def test_admin_has_calificaciones_importar_global(seeded_tenant: uuid.UUID, seed_session: AsyncSession):
    """ADMIN has calificaciones:importar with alcance global (from spec scenario)."""
    result = await seed_session.execute(
        sa.text(
            """
            SELECT rp.alcance FROM rol_permiso rp
            JOIN roles r ON r.id = rp.rol_id
            JOIN permisos p ON p.id = rp.permiso_id
            WHERE r.tenant_id = :tid AND r.nombre = 'ADMIN'
              AND p.tenant_id = :tid AND p.clave = 'calificaciones:importar'
              AND rp.deleted_at IS NULL
            """
        ),
        {"tid": str(seeded_tenant)},
    )
    row = result.fetchone()
    assert row is not None, "ADMIN should have calificaciones:importar"
    assert str(row[0]) == "global", f"Expected alcance=global, got {row[0]}"


@pytest.mark.asyncio
async def test_profesor_has_calificaciones_importar_propio(seeded_tenant: uuid.UUID, seed_session: AsyncSession):
    """PROFESOR has calificaciones:importar with alcance propio (from spec scenario)."""
    result = await seed_session.execute(
        sa.text(
            """
            SELECT rp.alcance FROM rol_permiso rp
            JOIN roles r ON r.id = rp.rol_id
            JOIN permisos p ON p.id = rp.permiso_id
            WHERE r.tenant_id = :tid AND r.nombre = 'PROFESOR'
              AND p.tenant_id = :tid AND p.clave = 'calificaciones:importar'
              AND rp.deleted_at IS NULL
            """
        ),
        {"tid": str(seeded_tenant)},
    )
    row = result.fetchone()
    assert row is not None, "PROFESOR should have calificaciones:importar"
    assert str(row[0]) == "propio", f"Expected alcance=propio, got {row[0]}"


@pytest.mark.asyncio
async def test_seed_is_idempotent(seeded_tenant: uuid.UUID, seed_session: AsyncSession):
    """Re-running the seed does not duplicate rows."""
    before_roles = await _count_roles(seed_session, seeded_tenant)
    before_perms = await _count_permissions(seed_session, seeded_tenant)
    before_matrix = await _count_matrix_rows(seed_session, seeded_tenant)

    # Run seed a second time
    from app.services.rbac_seed import seed_rbac_for_tenant  # noqa: PLC0415
    conn = await seed_session.connection()
    await conn.run_sync(seed_rbac_for_tenant, seeded_tenant)
    await seed_session.flush()

    after_roles = await _count_roles(seed_session, seeded_tenant)
    after_perms = await _count_permissions(seed_session, seeded_tenant)
    after_matrix = await _count_matrix_rows(seed_session, seeded_tenant)

    assert after_roles == before_roles, f"Roles duplicated: {before_roles} → {after_roles}"
    assert after_perms == before_perms, f"Perms duplicated: {before_perms} → {after_perms}"
    assert after_matrix == before_matrix, f"Matrix rows duplicated: {before_matrix} → {after_matrix}"


@pytest.mark.asyncio
async def test_roles_isolated_between_tenants(seed_engine: AsyncEngine):
    """Roles seeded for tenant A do not appear in tenant B's catalog."""
    from app.models.tenant import Tenant  # noqa: PLC0415
    from app.services.rbac_seed import seed_rbac_for_tenant  # noqa: PLC0415

    factory = async_sessionmaker(seed_engine, expire_on_commit=False)

    async with factory() as session:
        t_a = Tenant(slug=f"ta-{uuid.uuid4().hex[:6]}", nombre="Tenant A", activo=True)
        t_b = Tenant(slug=f"tb-{uuid.uuid4().hex[:6]}", nombre="Tenant B", activo=True)
        session.add_all([t_a, t_b])
        await session.flush()
        await session.refresh(t_a)
        await session.refresh(t_b)
        tid_a, tid_b = t_a.id, t_b.id

        # Only seed tenant A
        conn = await session.connection()
        await conn.run_sync(seed_rbac_for_tenant, tid_a)
        await session.flush()

        roles_a = await _count_roles(session, tid_a)
        roles_b = await _count_roles(session, tid_b)

        await session.rollback()

    assert roles_a == 7, f"Tenant A should have 7 roles, got {roles_a}"
    assert roles_b == 0, f"Tenant B should have 0 roles (not seeded), got {roles_b}"

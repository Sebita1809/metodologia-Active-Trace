"""
tests/test_rbac_seed_c05.py — TDD tests for C-05 RBAC seed extensions (Task 10).

Verifies:
  - Seed includes auditoria:ver (COORDINADOR/propio, ADMIN/global, FINANZAS/global)
  - Seed includes impersonacion:usar (ADMIN/global)
  - Seed is idempotent (re-run doesn't duplicate)

Requires TEST_DATABASE_URL (PostgreSQL — no mocks).

TDD cycle:
  RED   — written before seed extension was confirmed in place
  GREEN — rbac_seed.py already has the required entries from C-04/C-05
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping rbac_seed_c05 tests",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _register_models():
    import app.models.tenant       # noqa: F401
    import app.models.user         # noqa: F401
    import app.models.rol          # noqa: F401
    import app.models.permiso      # noqa: F401
    import app.models.rol_permiso  # noqa: F401
    import app.models.usuario_rol  # noqa: F401
    import app.features.auth.models  # noqa: F401


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
async def c05_seed_engine() -> AsyncEngine:
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
async def c05_seed_session(c05_seed_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(c05_seed_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def c05_seeded_tenant(c05_seed_session: AsyncSession) -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    from app.services.rbac_seed import seed_rbac_for_tenant  # noqa: PLC0415

    t = Tenant(slug=f"c05s-{uuid.uuid4().hex[:8]}", nombre="C05 Seed Test", activo=True)
    c05_seed_session.add(t)
    await c05_seed_session.flush()
    await c05_seed_session.refresh(t)
    tid = t.id

    conn = await c05_seed_session.connection()
    await conn.run_sync(seed_rbac_for_tenant, tid)
    await c05_seed_session.flush()
    return tid


# ---------------------------------------------------------------------------
# Task 10.1 — auditoria:ver assignments
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seed_assigns_auditoria_ver_to_coordinador_propio(
    c05_seeded_tenant: uuid.UUID,
    c05_seed_session: AsyncSession,
):
    """COORDINADOR has auditoria:ver with alcance=propio."""
    result = await c05_seed_session.execute(
        sa.text(
            """
            SELECT rp.alcance FROM rol_permiso rp
            JOIN roles r ON r.id = rp.rol_id
            JOIN permisos p ON p.id = rp.permiso_id
            WHERE r.tenant_id = :tid AND r.nombre = 'COORDINADOR'
              AND p.tenant_id = :tid AND p.clave = 'auditoria:ver'
              AND rp.deleted_at IS NULL
            """
        ),
        {"tid": str(c05_seeded_tenant)},
    )
    row = result.fetchone()
    assert row is not None, "COORDINADOR should have auditoria:ver"
    assert str(row[0]) == "propio", f"Expected propio, got {row[0]}"


@pytest.mark.asyncio
async def test_seed_assigns_auditoria_ver_to_admin_global(
    c05_seeded_tenant: uuid.UUID,
    c05_seed_session: AsyncSession,
):
    """ADMIN has auditoria:ver with alcance=global."""
    result = await c05_seed_session.execute(
        sa.text(
            """
            SELECT rp.alcance FROM rol_permiso rp
            JOIN roles r ON r.id = rp.rol_id
            JOIN permisos p ON p.id = rp.permiso_id
            WHERE r.tenant_id = :tid AND r.nombre = 'ADMIN'
              AND p.tenant_id = :tid AND p.clave = 'auditoria:ver'
              AND rp.deleted_at IS NULL
            """
        ),
        {"tid": str(c05_seeded_tenant)},
    )
    row = result.fetchone()
    assert row is not None, "ADMIN should have auditoria:ver"
    assert str(row[0]) == "global", f"Expected global, got {row[0]}"


@pytest.mark.asyncio
async def test_seed_assigns_auditoria_ver_to_finanzas_global(
    c05_seeded_tenant: uuid.UUID,
    c05_seed_session: AsyncSession,
):
    """FINANZAS has auditoria:ver with alcance=global."""
    result = await c05_seed_session.execute(
        sa.text(
            """
            SELECT rp.alcance FROM rol_permiso rp
            JOIN roles r ON r.id = rp.rol_id
            JOIN permisos p ON p.id = rp.permiso_id
            WHERE r.tenant_id = :tid AND r.nombre = 'FINANZAS'
              AND p.tenant_id = :tid AND p.clave = 'auditoria:ver'
              AND rp.deleted_at IS NULL
            """
        ),
        {"tid": str(c05_seeded_tenant)},
    )
    row = result.fetchone()
    assert row is not None, "FINANZAS should have auditoria:ver"
    assert str(row[0]) == "global", f"Expected global, got {row[0]}"


@pytest.mark.asyncio
async def test_seed_assigns_impersonacion_usar_to_admin_global(
    c05_seeded_tenant: uuid.UUID,
    c05_seed_session: AsyncSession,
):
    """ADMIN has impersonacion:usar with alcance=global."""
    result = await c05_seed_session.execute(
        sa.text(
            """
            SELECT rp.alcance FROM rol_permiso rp
            JOIN roles r ON r.id = rp.rol_id
            JOIN permisos p ON p.id = rp.permiso_id
            WHERE r.tenant_id = :tid AND r.nombre = 'ADMIN'
              AND p.tenant_id = :tid AND p.clave = 'impersonacion:usar'
              AND rp.deleted_at IS NULL
            """
        ),
        {"tid": str(c05_seeded_tenant)},
    )
    row = result.fetchone()
    assert row is not None, "ADMIN should have impersonacion:usar"
    assert str(row[0]) == "global", f"Expected global, got {row[0]}"


# ---------------------------------------------------------------------------
# Task 10.3 — Seed is idempotent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seed_c05_permissions_are_idempotent(
    c05_seeded_tenant: uuid.UUID,
    c05_seed_session: AsyncSession,
):
    """Re-running the seed doesn't duplicate auditoria:ver or impersonacion:usar."""
    async def _count_perm(clave: str) -> int:
        result = await c05_seed_session.execute(
            sa.text(
                """
                SELECT COUNT(*) FROM rol_permiso rp
                JOIN permisos p ON p.id = rp.permiso_id
                WHERE p.tenant_id = :tid AND p.clave = :clave
                  AND rp.tenant_id = :tid AND rp.deleted_at IS NULL
                """
            ),
            {"tid": str(c05_seeded_tenant), "clave": clave},
        )
        return result.scalar_one()

    before_aud = await _count_perm("auditoria:ver")
    before_imp = await _count_perm("impersonacion:usar")

    from app.services.rbac_seed import seed_rbac_for_tenant  # noqa: PLC0415
    conn = await c05_seed_session.connection()
    await conn.run_sync(seed_rbac_for_tenant, c05_seeded_tenant)
    await c05_seed_session.flush()

    after_aud = await _count_perm("auditoria:ver")
    after_imp = await _count_perm("impersonacion:usar")

    assert after_aud == before_aud, f"auditoria:ver count changed: {before_aud} → {after_aud}"
    assert after_imp == before_imp, f"impersonacion:usar count changed: {before_imp} → {after_imp}"

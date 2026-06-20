"""
tests/test_padron_modelos_repositories.py — TDD tests for VersionPadronRepository
and EntradaPadronRepository (tasks 2.1, 2.3).

Tests:
  - VersionPadronRepository isolates by tenant (T1 cannot see T2 versions)
  - EntradaPadronRepository isolates by tenant; bulk_create; list_by_version

Requires TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping padron repository tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def padron_engine() -> AsyncEngine:
    import app.models.tenant         # noqa: F401
    import app.models.user           # noqa: F401
    import app.models.rol            # noqa: F401
    import app.models.permiso        # noqa: F401
    import app.models.rol_permiso    # noqa: F401
    import app.models.usuario_rol    # noqa: F401
    import app.models.audit_log      # noqa: F401
    import app.models.carrera        # noqa: F401
    import app.models.cohorte        # noqa: F401
    import app.models.materia        # noqa: F401
    import app.models.usuario        # noqa: F401
    import app.models.asignacion     # noqa: F401
    import app.models.version_padron  # noqa: F401
    import app.models.entrada_padron  # noqa: F401
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
async def padron_session(padron_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(padron_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# DB Helpers
# ---------------------------------------------------------------------------

async def _make_tenant(session: AsyncSession, slug_suffix: str = "") -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=f"padron-{uuid.uuid4().hex[:8]}{slug_suffix}", nombre="Padron Test Tenant", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_materia(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(tenant_id=tid, codigo=f"MAT_{uuid.uuid4().hex[:6]}", nombre="Materia Padron Test")
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


async def _make_cohorte(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.models.cohorte import Cohorte  # noqa: PLC0415
    c = Carrera(tenant_id=tid, codigo=f"CAR_{uuid.uuid4().hex[:6]}", nombre="Carrera Test")
    session.add(c)
    await session.flush()
    await session.refresh(c)
    cohorte = Cohorte(
        tenant_id=tid, carrera_id=c.id,
        nombre=f"COH_{uuid.uuid4().hex[:6]}", anio=2024, vig_desde=date.today(),
    )
    session.add(cohorte)
    await session.flush()
    await session.refresh(cohorte)
    return cohorte.id


async def _make_domain_usuario(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.usuario import Usuario  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    email = f"usr_{uuid.uuid4().hex[:8]}@example.com"
    u = Usuario(
        tenant_id=tid,
        nombre="Test", apellidos="User",
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


async def _make_version(
    session: AsyncSession,
    tid: uuid.UUID,
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    usuario_id: uuid.UUID,
    activa: bool = True,
) -> uuid.UUID:
    from app.models.version_padron import VersionPadron  # noqa: PLC0415
    v = VersionPadron(
        tenant_id=tid,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        cargado_por=usuario_id,
        cargado_at=datetime.now(tz=timezone.utc),
        activa=activa,
        origen="archivo",
    )
    session.add(v)
    await session.flush()
    await session.refresh(v)
    return v.id


# ---------------------------------------------------------------------------
# Task 2.1 — VersionPadronRepository tenant isolation
# ---------------------------------------------------------------------------

async def test_version_padron_repository_tenant_isolation(padron_session: AsyncSession):
    """T1 repository cannot see versions created for T2."""
    from app.repositories.version_padron_repository import VersionPadronRepository  # noqa: PLC0415

    tid1 = await _make_tenant(padron_session, "-t1")
    tid2 = await _make_tenant(padron_session, "-t2")

    materia1 = await _make_materia(padron_session, tid1)
    cohorte1 = await _make_cohorte(padron_session, tid1)
    usuario1 = await _make_domain_usuario(padron_session, tid1)

    materia2 = await _make_materia(padron_session, tid2)
    cohorte2 = await _make_cohorte(padron_session, tid2)
    usuario2 = await _make_domain_usuario(padron_session, tid2)

    # Create a version under T2
    await _make_version(padron_session, tid2, materia2, cohorte2, usuario2, activa=True)
    await padron_session.commit()

    # T1 repository should NOT see T2 versions
    repo_t1 = VersionPadronRepository(session=padron_session, tenant_id=tid1)
    all_t1 = await repo_t1.list_versiones(materia2, cohorte2)
    assert all_t1 == [], "T1 should not see T2 versions"


async def test_version_padron_get_activa(padron_session: AsyncSession):
    """get_activa returns the active version for (materia, cohorte)."""
    from app.repositories.version_padron_repository import VersionPadronRepository  # noqa: PLC0415

    tid = await _make_tenant(padron_session)
    materia = await _make_materia(padron_session, tid)
    cohorte = await _make_cohorte(padron_session, tid)
    usuario = await _make_domain_usuario(padron_session, tid)

    vid = await _make_version(padron_session, tid, materia, cohorte, usuario, activa=True)
    await padron_session.commit()

    repo = VersionPadronRepository(session=padron_session, tenant_id=tid)
    activa = await repo.get_activa(materia, cohorte)
    assert activa is not None
    assert activa.id == vid
    assert activa.activa is True


async def test_version_padron_desactivar_activa(padron_session: AsyncSession):
    """desactivar_activa sets activa=False on the current active version."""
    from app.repositories.version_padron_repository import VersionPadronRepository  # noqa: PLC0415

    tid = await _make_tenant(padron_session)
    materia = await _make_materia(padron_session, tid)
    cohorte = await _make_cohorte(padron_session, tid)
    usuario = await _make_domain_usuario(padron_session, tid)

    await _make_version(padron_session, tid, materia, cohorte, usuario, activa=True)
    await padron_session.commit()

    repo = VersionPadronRepository(session=padron_session, tenant_id=tid)
    updated = await repo.desactivar_activa(materia, cohorte)
    await padron_session.commit()

    assert updated == 1

    activa = await repo.get_activa(materia, cohorte)
    assert activa is None


async def test_version_padron_soft_delete_scope(padron_session: AsyncSession):
    """soft_delete_scope only deletes (tenant, materia, cohorte) combination."""
    from app.repositories.version_padron_repository import VersionPadronRepository  # noqa: PLC0415

    tid = await _make_tenant(padron_session)
    materia_a = await _make_materia(padron_session, tid)
    materia_b = await _make_materia(padron_session, tid)
    cohorte_x = await _make_cohorte(padron_session, tid)
    cohorte_y = await _make_cohorte(padron_session, tid)
    usuario = await _make_domain_usuario(padron_session, tid)

    # Create versions for (A, X), (B, X), (A, Y)
    await _make_version(padron_session, tid, materia_a, cohorte_x, usuario, activa=True)
    await _make_version(padron_session, tid, materia_b, cohorte_x, usuario, activa=True)
    await _make_version(padron_session, tid, materia_a, cohorte_y, usuario, activa=True)
    await padron_session.commit()

    repo = VersionPadronRepository(session=padron_session, tenant_id=tid)
    # Soft-delete only (A, X)
    deleted = await repo.soft_delete_scope(materia_a, cohorte_x)
    await padron_session.commit()

    assert deleted == 1

    # (B, X) should still be active
    versiones_bx = await repo.list_versiones(materia_b, cohorte_x)
    assert len(versiones_bx) == 1

    # (A, Y) should still be active
    versiones_ay = await repo.list_versiones(materia_a, cohorte_y)
    assert len(versiones_ay) == 1

    # (A, X) should be gone from active list
    versiones_ax = await repo.list_versiones(materia_a, cohorte_x)
    assert len(versiones_ax) == 0


# ---------------------------------------------------------------------------
# Task 2.3 — EntradaPadronRepository tenant isolation + bulk_create + list_by_version
# ---------------------------------------------------------------------------

async def test_entrada_padron_repository_bulk_create(padron_session: AsyncSession):
    """bulk_create inserts all entries and returns them with server-generated IDs."""
    from app.models.entrada_padron import EntradaPadron  # noqa: PLC0415
    from app.repositories.entrada_padron_repository import EntradaPadronRepository  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415

    tid = await _make_tenant(padron_session)
    materia = await _make_materia(padron_session, tid)
    cohorte = await _make_cohorte(padron_session, tid)
    usuario = await _make_domain_usuario(padron_session, tid)
    vid = await _make_version(padron_session, tid, materia, cohorte, usuario, activa=True)
    await padron_session.commit()

    crypto = CryptoService(_TEST_KEY)
    repo = EntradaPadronRepository(session=padron_session, tenant_id=tid)

    entradas = [
        EntradaPadron(
            tenant_id=tid,
            version_id=vid,
            nombre=f"Alumno{i}",
            apellidos="Apellido",
            email=crypto.encrypt(f"alumno{i}@test.com"),
        )
        for i in range(3)
    ]

    result = await repo.bulk_create(entradas)
    await padron_session.commit()

    assert len(result) == 3
    for e in result:
        assert e.id is not None


async def test_entrada_padron_repository_list_by_version(padron_session: AsyncSession):
    """list_by_version filters by version_id + tenant + not deleted."""
    from app.models.entrada_padron import EntradaPadron  # noqa: PLC0415
    from app.repositories.entrada_padron_repository import EntradaPadronRepository  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415

    tid = await _make_tenant(padron_session)
    materia = await _make_materia(padron_session, tid)
    cohorte = await _make_cohorte(padron_session, tid)
    usuario = await _make_domain_usuario(padron_session, tid)
    vid1 = await _make_version(padron_session, tid, materia, cohorte, usuario, activa=True)
    vid2 = await _make_version(padron_session, tid, materia, cohorte, usuario, activa=False)
    await padron_session.commit()

    crypto = CryptoService(_TEST_KEY)
    repo = EntradaPadronRepository(session=padron_session, tenant_id=tid)

    # Add 2 entries to version 1, 1 entry to version 2
    await repo.bulk_create([
        EntradaPadron(
            tenant_id=tid, version_id=vid1,
            nombre="A1", apellidos="Ap", email=crypto.encrypt("a1@test.com"),
        ),
        EntradaPadron(
            tenant_id=tid, version_id=vid1,
            nombre="A2", apellidos="Ap", email=crypto.encrypt("a2@test.com"),
        ),
        EntradaPadron(
            tenant_id=tid, version_id=vid2,
            nombre="B1", apellidos="Ap", email=crypto.encrypt("b1@test.com"),
        ),
    ])
    await padron_session.commit()

    entries_v1 = await repo.list_by_version(vid1)
    assert len(entries_v1) == 2

    entries_v2 = await repo.list_by_version(vid2)
    assert len(entries_v2) == 1


async def test_entrada_padron_repository_tenant_isolation(padron_session: AsyncSession):
    """EntradaPadron from T2 is not visible to T1 repository."""
    from app.models.entrada_padron import EntradaPadron  # noqa: PLC0415
    from app.repositories.entrada_padron_repository import EntradaPadronRepository  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415

    tid1 = await _make_tenant(padron_session, "-e1")
    tid2 = await _make_tenant(padron_session, "-e2")

    materia2 = await _make_materia(padron_session, tid2)
    cohorte2 = await _make_cohorte(padron_session, tid2)
    usuario2 = await _make_domain_usuario(padron_session, tid2)
    vid2 = await _make_version(padron_session, tid2, materia2, cohorte2, usuario2, activa=True)
    await padron_session.commit()

    crypto = CryptoService(_TEST_KEY)
    repo2 = EntradaPadronRepository(session=padron_session, tenant_id=tid2)
    await repo2.bulk_create([
        EntradaPadron(
            tenant_id=tid2, version_id=vid2,
            nombre="X", apellidos="Y", email=crypto.encrypt("x@test.com"),
        )
    ])
    await padron_session.commit()

    # T1 should see nothing
    repo1 = EntradaPadronRepository(session=padron_session, tenant_id=tid1)
    entries = await repo1.list_by_version(vid2)
    assert entries == []

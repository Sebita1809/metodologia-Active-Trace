"""
tests/test_padron_sync_moodle_service.py — TDD tests for PadronService.sync_moodle (tasks 5.5, 5.6).

Tests:
  5.5 — sync_moodle with successful Moodle client creates active version
        with origen="moodle" and emits PADRON_CARGAR audit
  5.6 — sync_moodle propagates MoodleIntegrationError and does NOT create
        a partial version (rollback semantics)

Requires TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base
from app.integrations.moodle_ws import EntradaCruda, MoodleIntegrationError

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping padron sync_moodle tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def sync_engine() -> AsyncEngine:
    import app.models.tenant          # noqa: F401
    import app.models.user            # noqa: F401
    import app.models.rol             # noqa: F401
    import app.models.permiso         # noqa: F401
    import app.models.rol_permiso     # noqa: F401
    import app.models.usuario_rol     # noqa: F401
    import app.models.audit_log       # noqa: F401
    import app.models.carrera         # noqa: F401
    import app.models.cohorte         # noqa: F401
    import app.models.materia         # noqa: F401
    import app.models.usuario         # noqa: F401
    import app.models.asignacion      # noqa: F401
    import app.models.version_padron  # noqa: F401
    import app.models.entrada_padron  # noqa: F401
    import app.features.auth.models   # noqa: F401

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
async def sync_session(sync_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(sync_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# DB Helpers
# ---------------------------------------------------------------------------

async def _make_tenant(session: AsyncSession) -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=f"sm-{uuid.uuid4().hex[:8]}", nombre="Sync Moodle Test", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_materia(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(tenant_id=tid, codigo=f"MAT_{uuid.uuid4().hex[:6]}", nombre="Mat SM")
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


async def _make_cohorte(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.models.cohorte import Cohorte  # noqa: PLC0415
    c = Carrera(tenant_id=tid, codigo=f"CAR_{uuid.uuid4().hex[:6]}", nombre="Car SM")
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
        tenant_id=tid, nombre="Test", apellidos="User",
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


def _make_service(session: AsyncSession, tenant_id: uuid.UUID):
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.services.audit_service import AuditService  # noqa: PLC0415
    from app.services.padron_service import PadronService  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    audit_svc = AuditService(session=session, tenant_id=tenant_id)
    return PadronService(session=session, tenant_id=tenant_id, crypto=crypto, audit_svc=audit_svc)


def _make_current_user(uid: uuid.UUID, tid: uuid.UUID):
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    return CurrentUser(user_id=uid, tenant_id=tid, roles=[])


def _make_moodle_client(entradas: list[EntradaCruda]):
    """Build a mock MoodleWSClient that returns the given entradas."""
    from app.integrations.moodle_ws import MoodleWSClient  # noqa: PLC0415
    mock = AsyncMock(spec=MoodleWSClient)
    mock.fetch_padron = AsyncMock(return_value=entradas)
    return mock


# ---------------------------------------------------------------------------
# Task 5.5 — sync_moodle creates active version with origen="moodle" + audits
# ---------------------------------------------------------------------------

async def test_sync_moodle_creates_version_with_origen_moodle(sync_session: AsyncSession):
    """sync_moodle creates a version with activa=True and origen="moodle"."""
    from app.models.version_padron import VersionPadron  # noqa: PLC0415
    from app.models.audit_log import AuditLog  # noqa: PLC0415

    tid = await _make_tenant(sync_session)
    uid = await _make_domain_usuario(sync_session, tid)
    materia = await _make_materia(sync_session, tid)
    cohorte = await _make_cohorte(sync_session, tid)
    await sync_session.commit()

    current_user = _make_current_user(uid, tid)
    svc = _make_service(sync_session, tid)

    moodle_client = _make_moodle_client([
        EntradaCruda(nombre="Moodle", apellidos="User", email="moodle@lms.com"),
    ])

    resp = await svc.sync_moodle(
        current_user=current_user,
        materia_id=materia,
        cohorte_id=cohorte,
        moodle_client=moodle_client,
        curso_ref="COURSE_001",
    )
    await sync_session.commit()

    assert resp.version.origen == "moodle"
    assert resp.version.activa is True
    assert resp.entradas_cargadas == 1

    # Verify audit
    audit = await sync_session.scalar(
        sa.select(AuditLog)
        .where(AuditLog.tenant_id == tid)
        .where(AuditLog.accion == "PADRON_CARGAR")
    )
    assert audit is not None
    assert audit.filas_afectadas == 1


# ---------------------------------------------------------------------------
# Task 5.6 — sync_moodle rollback on MoodleIntegrationError
# ---------------------------------------------------------------------------

async def test_sync_moodle_rollback_on_moodle_error(sync_session: AsyncSession):
    """When Moodle fails, MoodleIntegrationError propagates and no version is created."""
    from app.models.version_padron import VersionPadron  # noqa: PLC0415

    tid = await _make_tenant(sync_session)
    uid = await _make_domain_usuario(sync_session, tid)
    materia = await _make_materia(sync_session, tid)
    cohorte = await _make_cohorte(sync_session, tid)
    await sync_session.commit()

    current_user = _make_current_user(uid, tid)
    svc = _make_service(sync_session, tid)

    failing_client = AsyncMock()
    failing_client.fetch_padron = AsyncMock(
        side_effect=MoodleIntegrationError("LMS unavailable")
    )

    with pytest.raises(MoodleIntegrationError):
        await svc.sync_moodle(
            current_user=current_user,
            materia_id=materia,
            cohorte_id=cohorte,
            moodle_client=failing_client,
            curso_ref="BAD_COURSE",
        )

    await sync_session.rollback()

    # No version should exist
    count = await sync_session.scalar(
        sa.select(sa.func.count()).select_from(VersionPadron)
        .where(VersionPadron.tenant_id == tid)
    )
    assert count == 0, "No version should be created when Moodle fails"

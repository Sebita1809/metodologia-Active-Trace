"""
tests/test_comunicacion_repository.py — TDD integration tests for ComunicacionRepository.

Group 4 tasks:
  4.1 — create_many persists N rows scoped to tenant; other-tenant rows not returned
  4.2 — list_cola filters by tenant, lote_id, estado
  4.3 — aplicar_transicion_condicional: race-safe conditional UPDATE
  4.4 — marcar_aprobado: sets aprobado_at/aprobado_por only on Pendiente

These tests require TEST_DATABASE_URL (real DB — no mocks per project rules).
DB fixture builds the full schema (including comunicacion) from scratch.

Implemented: C-12 (comunicaciones-cola-worker)
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine
from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.repositories.comunicacion_repository import ComunicacionRepository

_requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping comunicacion repository integration tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Schema fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def comunicacion_engine() -> AsyncEngine:
    """Module-scoped engine with full domain schema including comunicacion."""
    # Import all models to register them on Base.metadata
    import app.models.tenant           # noqa: F401
    import app.models.user             # noqa: F401
    import app.models.rol              # noqa: F401
    import app.models.permiso          # noqa: F401
    import app.models.rol_permiso      # noqa: F401
    import app.models.usuario_rol      # noqa: F401
    import app.models.audit_log        # noqa: F401
    import app.models.carrera          # noqa: F401
    import app.models.cohorte          # noqa: F401
    import app.models.materia          # noqa: F401
    import app.models.usuario          # noqa: F401
    import app.models.asignacion       # noqa: F401
    import app.models.version_padron   # noqa: F401
    import app.models.entrada_padron   # noqa: F401
    import app.models.umbral_materia   # noqa: F401
    import app.models.calificacion     # noqa: F401
    import app.models.comunicacion     # noqa: F401
    import app.features.auth.models    # noqa: F401

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
async def com_session(comunicacion_engine: AsyncEngine) -> AsyncSession:
    """Per-test session that DOES NOT auto-rollback (to test across flush boundaries)."""
    factory = async_sessionmaker(comunicacion_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _make_tenant(session: AsyncSession, suffix: str = "") -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=f"comtest-{uuid.uuid4().hex[:8]}{suffix}", nombre="Com Test", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_materia(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(tenant_id=tid, codigo=f"MAT_{uuid.uuid4().hex[:6]}", nombre="Materia Test")
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


async def _make_usuario(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.models.usuario import Usuario  # noqa: PLC0415
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


def _make_com(
    tid: uuid.UUID,
    usuario_id: uuid.UUID,
    materia_id: uuid.UUID,
    lote_id: uuid.UUID,
    destinatario: str = "ciphertext_dummy",
    estado: EstadoComunicacion = EstadoComunicacion.Pendiente,
) -> Comunicacion:
    """Build a Comunicacion object (not yet persisted)."""
    return Comunicacion(
        tenant_id=tid,
        enviado_por=usuario_id,
        materia_id=materia_id,
        destinatario=destinatario,
        asunto="Test asunto",
        cuerpo="Test cuerpo",
        estado=estado.value,
        lote_id=lote_id,
    )


# ---------------------------------------------------------------------------
# Task 4.1 — create_many
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_create_many_persiste_n_filas(com_session):
    """create_many persists N rows for the same tenant."""
    tid = await _make_tenant(com_session)
    mid = await _make_materia(com_session, tid)
    uid = await _make_usuario(com_session, tid)
    lote_id = uuid.uuid4()

    repo = ComunicacionRepository(session=com_session, tenant_id=tid)

    coms = [_make_com(tid, uid, mid, lote_id, f"ct_{i}") for i in range(3)]
    result = await repo.create_many(coms)

    assert len(result) == 3
    assert all(c.id is not None for c in result)
    assert all(c.tenant_id == tid for c in result)
    await com_session.commit()


@_requires_db
@pytest.mark.asyncio
async def test_create_many_tenant_isolation(com_session):
    """Rows from another tenant are NOT returned by the repo."""
    tid1 = await _make_tenant(com_session, "A")
    tid2 = await _make_tenant(com_session, "B")
    mid1 = await _make_materia(com_session, tid1)
    mid2 = await _make_materia(com_session, tid2)
    uid1 = await _make_usuario(com_session, tid1)
    uid2 = await _make_usuario(com_session, tid2)
    lote_id = uuid.uuid4()

    repo1 = ComunicacionRepository(session=com_session, tenant_id=tid1)
    repo2 = ComunicacionRepository(session=com_session, tenant_id=tid2)

    coms1 = [_make_com(tid1, uid1, mid1, lote_id)]
    coms2 = [_make_com(tid2, uid2, mid2, lote_id)]

    await repo1.create_many(coms1)
    await repo2.create_many(coms2)
    await com_session.commit()

    all_t1 = await repo1.list_cola()
    all_t2 = await repo2.list_cola()

    # Each repo only sees its own tenant's rows
    assert all(c.tenant_id == tid1 for c in all_t1)
    assert all(c.tenant_id == tid2 for c in all_t2)
    # No cross-tenant leakage
    t1_ids = {c.id for c in all_t1}
    t2_ids = {c.id for c in all_t2}
    assert t1_ids.isdisjoint(t2_ids)


# ---------------------------------------------------------------------------
# Task 4.2 — list_cola
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_list_cola_filtra_por_lote_id(com_session):
    """list_cola(lote_id=X) returns only rows with that lote_id."""
    tid = await _make_tenant(com_session)
    mid = await _make_materia(com_session, tid)
    uid = await _make_usuario(com_session, tid)
    lote_a = uuid.uuid4()
    lote_b = uuid.uuid4()

    repo = ComunicacionRepository(session=com_session, tenant_id=tid)

    await repo.create_many([
        _make_com(tid, uid, mid, lote_a, "ct_a1"),
        _make_com(tid, uid, mid, lote_a, "ct_a2"),
        _make_com(tid, uid, mid, lote_b, "ct_b1"),
    ])
    await com_session.commit()

    result = await repo.list_cola(lote_id=lote_a)
    assert len(result) == 2
    assert all(c.lote_id == lote_a for c in result)


@_requires_db
@pytest.mark.asyncio
async def test_list_cola_filtra_por_estado(com_session):
    """list_cola(estado=Pendiente) returns only Pendiente rows."""
    tid = await _make_tenant(com_session)
    mid = await _make_materia(com_session, tid)
    uid = await _make_usuario(com_session, tid)
    lote_id = uuid.uuid4()

    repo = ComunicacionRepository(session=com_session, tenant_id=tid)

    # Create one Pendiente and one Enviando
    com_p = _make_com(tid, uid, mid, lote_id, estado=EstadoComunicacion.Pendiente)
    com_e = _make_com(tid, uid, mid, lote_id, estado=EstadoComunicacion.Enviando)
    await repo.create_many([com_p, com_e])
    await com_session.commit()

    pendientes = await repo.list_cola(estado=EstadoComunicacion.Pendiente)
    assert all(c.estado == EstadoComunicacion.Pendiente.value for c in pendientes)

    enviando = await repo.list_cola(estado=EstadoComunicacion.Enviando)
    assert all(c.estado == EstadoComunicacion.Enviando.value for c in enviando)


@_requires_db
@pytest.mark.asyncio
async def test_list_cola_aislamiento_tenant(com_session):
    """list_cola only returns rows for the repo's tenant."""
    tid_x = await _make_tenant(com_session, "X")
    tid_y = await _make_tenant(com_session, "Y")
    mid_x = await _make_materia(com_session, tid_x)
    mid_y = await _make_materia(com_session, tid_y)
    uid_x = await _make_usuario(com_session, tid_x)
    uid_y = await _make_usuario(com_session, tid_y)
    lote_id = uuid.uuid4()

    repo_x = ComunicacionRepository(session=com_session, tenant_id=tid_x)
    repo_y = ComunicacionRepository(session=com_session, tenant_id=tid_y)

    await repo_x.create_many([_make_com(tid_x, uid_x, mid_x, lote_id)])
    await repo_y.create_many([_make_com(tid_y, uid_y, mid_y, lote_id)])
    await com_session.commit()

    result_x = await repo_x.list_cola(lote_id=lote_id)
    result_y = await repo_y.list_cola(lote_id=lote_id)

    assert all(c.tenant_id == tid_x for c in result_x)
    assert all(c.tenant_id == tid_y for c in result_y)


# ---------------------------------------------------------------------------
# Task 4.3 — aplicar_transicion_condicional
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_transicion_condicional_actualiza_cuando_estado_coincide(com_session):
    """aplicar_transicion_condicional updates state when current state matches."""
    tid = await _make_tenant(com_session)
    mid = await _make_materia(com_session, tid)
    uid = await _make_usuario(com_session, tid)
    lote_id = uuid.uuid4()

    repo = ComunicacionRepository(session=com_session, tenant_id=tid)

    [com] = await repo.create_many([_make_com(tid, uid, mid, lote_id)])
    await com_session.commit()

    rowcount = await repo.aplicar_transicion_condicional(
        com.id,
        desde=EstadoComunicacion.Pendiente,
        hacia=EstadoComunicacion.Enviando,
    )
    await com_session.commit()

    assert rowcount == 1
    updated = await repo.get(com.id)
    assert updated.estado == EstadoComunicacion.Enviando.value


@_requires_db
@pytest.mark.asyncio
async def test_transicion_condicional_no_actualiza_si_estado_cambio(com_session):
    """aplicar_transicion_condicional returns 0 if state already changed (race)."""
    tid = await _make_tenant(com_session)
    mid = await _make_materia(com_session, tid)
    uid = await _make_usuario(com_session, tid)
    lote_id = uuid.uuid4()

    repo = ComunicacionRepository(session=com_session, tenant_id=tid)

    # Create already-Cancelado (simulates cancellation winning the race)
    com_cancelado = _make_com(tid, uid, mid, lote_id, estado=EstadoComunicacion.Cancelado)
    [com] = await repo.create_many([com_cancelado])
    await com_session.commit()

    # Worker tries to take it to Enviando, but it's already Cancelado
    rowcount = await repo.aplicar_transicion_condicional(
        com.id,
        desde=EstadoComunicacion.Pendiente,  # wrong expected state
        hacia=EstadoComunicacion.Enviando,
    )
    await com_session.commit()

    assert rowcount == 0
    # State unchanged
    refreshed = await repo.get(com.id)
    assert refreshed.estado == EstadoComunicacion.Cancelado.value


# ---------------------------------------------------------------------------
# Task 4.4 — marcar_aprobado
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_marcar_aprobado_por_lote_setea_aprobado_at(com_session):
    """marcar_aprobado_por_lote sets aprobado_at on all Pendiente rows."""
    tid = await _make_tenant(com_session)
    mid = await _make_materia(com_session, tid)
    uid = await _make_usuario(com_session, tid)
    aprobador_id = await _make_usuario(com_session, tid)
    lote_id = uuid.uuid4()

    repo = ComunicacionRepository(session=com_session, tenant_id=tid)

    coms = [_make_com(tid, uid, mid, lote_id, f"ct_{i}") for i in range(3)]
    await repo.create_many(coms)
    await com_session.commit()

    updated = await repo.marcar_aprobado_por_lote(lote_id, aprobado_por=aprobador_id)
    await com_session.commit()

    assert updated == 3

    all_coms = await repo.list_cola(lote_id=lote_id)
    assert all(c.aprobado_at is not None for c in all_coms)
    assert all(c.aprobado_por == aprobador_id for c in all_coms)


@_requires_db
@pytest.mark.asyncio
async def test_marcar_aprobado_por_lote_no_toca_no_pendientes(com_session):
    """marcar_aprobado_por_lote does NOT update non-Pendiente rows."""
    tid = await _make_tenant(com_session)
    mid = await _make_materia(com_session, tid)
    uid = await _make_usuario(com_session, tid)
    aprobador_id = await _make_usuario(com_session, tid)
    lote_id = uuid.uuid4()

    repo = ComunicacionRepository(session=com_session, tenant_id=tid)

    com_pendiente = _make_com(tid, uid, mid, lote_id, "ct_p", EstadoComunicacion.Pendiente)
    com_enviado = _make_com(tid, uid, mid, lote_id, "ct_e", EstadoComunicacion.Enviado)
    await repo.create_many([com_pendiente, com_enviado])
    await com_session.commit()

    updated = await repo.marcar_aprobado_por_lote(lote_id, aprobado_por=aprobador_id)
    await com_session.commit()

    # Only the Pendiente row is updated
    assert updated == 1

    all_coms = await repo.list_cola(lote_id=lote_id, include_deleted=False)
    pendientes = [c for c in all_coms if c.estado == EstadoComunicacion.Pendiente.value]
    enviados = [c for c in all_coms if c.estado == EstadoComunicacion.Enviado.value]

    assert all(c.aprobado_at is not None for c in pendientes)
    assert all(c.aprobado_at is None for c in enviados)


@_requires_db
@pytest.mark.asyncio
async def test_marcar_aprobado_por_id_item_individual(com_session):
    """marcar_aprobado_por_id approves only the specified Comunicacion."""
    tid = await _make_tenant(com_session)
    mid = await _make_materia(com_session, tid)
    uid = await _make_usuario(com_session, tid)
    aprobador_id = await _make_usuario(com_session, tid)
    lote_id = uuid.uuid4()

    repo = ComunicacionRepository(session=com_session, tenant_id=tid)

    coms = [_make_com(tid, uid, mid, lote_id, f"ct_{i}") for i in range(3)]
    persisted = await repo.create_many(coms)
    await com_session.commit()

    # Approve only the first one
    target_id = persisted[0].id
    updated = await repo.marcar_aprobado_por_id(target_id, aprobado_por=aprobador_id)
    await com_session.commit()

    assert updated == 1

    # Check: only the target is approved
    all_coms = await repo.list_cola(lote_id=lote_id)
    approved = [c for c in all_coms if c.aprobado_at is not None]
    not_approved = [c for c in all_coms if c.aprobado_at is None]

    assert len(approved) == 1
    assert approved[0].id == target_id
    assert len(not_approved) == 2

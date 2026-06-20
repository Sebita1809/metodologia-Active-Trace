"""
tests/test_comunicacion_worker.py — TDD integration tests for ComunicacionWorker.

Group 6 tasks:
  6.1 — procesar_pendientes: canal.enviar success → Pendiente→Enviando→Enviado + enviado_at
  6.2 — canal.enviar failure → Pendiente→Enviando→Error
  6.3 — fault isolation: one failure in lote, rest succeed
  6.4 — approval gate: tenant requires approval → only approved dispatched
  6.5 — cancellation race: cancelled before worker takes it → skipped

Requires TEST_DATABASE_URL (real DB). The canal IS mocked (it's the external channel).
The DB is NEVER mocked (project rule 4).

Implemented: C-12 (comunicaciones-cola-worker)
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.crypto import CryptoService
from app.core.database import Base, build_engine
from app.models.comunicacion import Comunicacion, EstadoComunicacion

_requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping worker integration tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Schema fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def worker_engine() -> AsyncEngine:
    """Module-scoped engine for worker tests."""
    import app.models.tenant            # noqa: F401
    import app.models.user              # noqa: F401
    import app.models.rol               # noqa: F401
    import app.models.permiso           # noqa: F401
    import app.models.rol_permiso       # noqa: F401
    import app.models.usuario_rol       # noqa: F401
    import app.models.audit_log         # noqa: F401
    import app.models.carrera           # noqa: F401
    import app.models.cohorte           # noqa: F401
    import app.models.materia           # noqa: F401
    import app.models.usuario           # noqa: F401
    import app.models.asignacion        # noqa: F401
    import app.models.version_padron    # noqa: F401
    import app.models.entrada_padron    # noqa: F401
    import app.models.umbral_materia    # noqa: F401
    import app.models.calificacion      # noqa: F401
    import app.models.comunicacion      # noqa: F401
    import app.features.auth.models     # noqa: F401

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
async def worker_session(worker_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(worker_engine, expire_on_commit=False)
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
    t = Tenant(slug=f"wtest-{uuid.uuid4().hex[:8]}", nombre="Worker Test", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_materia(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(tenant_id=tid, codigo=f"MAT_{uuid.uuid4().hex[:6]}", nombre="Mat Test")
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


def _make_canal_exitoso() -> AsyncMock:
    """Mock canal that always returns True (success)."""
    canal = AsyncMock()
    canal.enviar = AsyncMock(return_value=True)
    return canal


def _make_canal_fallido() -> AsyncMock:
    """Mock canal that always returns False (failure)."""
    canal = AsyncMock()
    canal.enviar = AsyncMock(return_value=False)
    return canal


def _make_canal_excepcion() -> AsyncMock:
    """Mock canal that raises an exception."""
    canal = AsyncMock()
    canal.enviar = AsyncMock(side_effect=ConnectionError("SMTP unreachable"))
    return canal


async def _encolar_comunicacion(
    session: AsyncSession,
    tid: uuid.UUID,
    uid: uuid.UUID,
    mid: uuid.UUID,
    lote_id: uuid.UUID,
    email: str = "alumno@example.com",
    aprobado: bool = False,
    aprobador_id: uuid.UUID | None = None,
    estado: EstadoComunicacion = EstadoComunicacion.Pendiente,
) -> Comunicacion:
    """Helper: create and persist a Comunicacion directly."""
    crypto = CryptoService(_TEST_KEY)
    now = datetime.now(tz=timezone.utc)
    com = Comunicacion(
        tenant_id=tid,
        enviado_por=uid,
        materia_id=mid,
        destinatario=crypto.encrypt(email),
        asunto="Test asunto",
        cuerpo="Test cuerpo",
        estado=estado.value,
        lote_id=lote_id,
        aprobado_at=now if aprobado else None,
        aprobado_por=aprobador_id if aprobado else None,
    )
    session.add(com)
    await session.flush()
    await session.refresh(com)
    return com


# ---------------------------------------------------------------------------
# Task 6.1 — canal success → Enviado + enviado_at
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_procesar_pendientes_despacho_exitoso(worker_session):
    """Worker: Pendiente → Enviando → Enviado, sets enviado_at on success."""
    from app.workers.comunicacion_worker import procesar_pendientes  # noqa: PLC0415
    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415

    tid = await _make_tenant(worker_session)
    uid = await _make_usuario(worker_session, tid)
    mid = await _make_materia(worker_session, tid)
    lote_id = uuid.uuid4()

    com = await _encolar_comunicacion(worker_session, tid, uid, mid, lote_id)
    await worker_session.commit()

    canal = _make_canal_exitoso()
    crypto = CryptoService(_TEST_KEY)

    result = await procesar_pendientes(
        worker_session, canal,
        tenant_id=tid, crypto=crypto, requiere_aprobacion=False,
    )
    await worker_session.commit()

    assert result["enviados"] == 1
    assert result["errores"] == 0

    repo = ComunicacionRepository(session=worker_session, tenant_id=tid)
    updated = await repo.get(com.id)
    assert updated.estado == EstadoComunicacion.Enviado.value
    assert updated.enviado_at is not None

    # Canal was called before transitioning to Enviando
    canal.enviar.assert_called_once()


@_requires_db
@pytest.mark.asyncio
async def test_procesar_transiciona_a_enviando_antes_de_canal(worker_session):
    """Worker transitions to Enviando BEFORE calling canal.enviar."""
    from app.workers.comunicacion_worker import procesar_pendientes  # noqa: PLC0415
    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415

    tid = await _make_tenant(worker_session)
    uid = await _make_usuario(worker_session, tid)
    mid = await _make_materia(worker_session, tid)
    lote_id = uuid.uuid4()

    com = await _encolar_comunicacion(worker_session, tid, uid, mid, lote_id)
    await worker_session.commit()

    # Canal that checks state when called
    estados_durante_envio = []

    async def canal_spy(destinatario, asunto, cuerpo):
        repo = ComunicacionRepository(session=worker_session, tenant_id=tid)
        current_com = await repo.get(com.id)
        estados_durante_envio.append(current_com.estado)
        return True

    canal = MagicMock()
    canal.enviar = canal_spy
    crypto = CryptoService(_TEST_KEY)

    await procesar_pendientes(
        worker_session, canal,
        tenant_id=tid, crypto=crypto, requiere_aprobacion=False,
    )
    await worker_session.commit()

    # When canal was called, state was already Enviando
    assert estados_durante_envio == [EstadoComunicacion.Enviando.value]


# ---------------------------------------------------------------------------
# Task 6.2 — canal failure → Error
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_procesar_despacho_fallido_transiciona_a_error(worker_session):
    """Worker: canal returns False → Comunicacion transitions to Error."""
    from app.workers.comunicacion_worker import procesar_pendientes  # noqa: PLC0415
    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415

    tid = await _make_tenant(worker_session)
    uid = await _make_usuario(worker_session, tid)
    mid = await _make_materia(worker_session, tid)
    lote_id = uuid.uuid4()

    com = await _encolar_comunicacion(worker_session, tid, uid, mid, lote_id)
    await worker_session.commit()

    canal = _make_canal_fallido()
    crypto = CryptoService(_TEST_KEY)

    result = await procesar_pendientes(
        worker_session, canal,
        tenant_id=tid, crypto=crypto, requiere_aprobacion=False,
    )
    await worker_session.commit()

    assert result["errores"] == 1
    assert result["enviados"] == 0

    repo = ComunicacionRepository(session=worker_session, tenant_id=tid)
    updated = await repo.get(com.id)
    assert updated.estado == EstadoComunicacion.Error.value


@_requires_db
@pytest.mark.asyncio
async def test_procesar_excepcion_canal_capturada_como_error(worker_session):
    """Worker: canal raises exception → captured as Error, NOT propagated."""
    from app.workers.comunicacion_worker import procesar_pendientes  # noqa: PLC0415
    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415

    tid = await _make_tenant(worker_session)
    uid = await _make_usuario(worker_session, tid)
    mid = await _make_materia(worker_session, tid)
    lote_id = uuid.uuid4()

    com = await _encolar_comunicacion(worker_session, tid, uid, mid, lote_id)
    await worker_session.commit()

    canal = _make_canal_excepcion()
    crypto = CryptoService(_TEST_KEY)

    # Must NOT raise — exception is captured
    result = await procesar_pendientes(
        worker_session, canal,
        tenant_id=tid, crypto=crypto, requiere_aprobacion=False,
    )
    await worker_session.commit()

    assert result["errores"] == 1

    repo = ComunicacionRepository(session=worker_session, tenant_id=tid)
    updated = await repo.get(com.id)
    assert updated.estado == EstadoComunicacion.Error.value


# ---------------------------------------------------------------------------
# Task 6.3 — fault isolation: one fails, rest succeed
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_fallo_aislado_no_detiene_resto_del_lote(worker_session):
    """Worker: one message fails, the rest succeed; worker does NOT stop."""
    from app.workers.comunicacion_worker import procesar_pendientes  # noqa: PLC0415
    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415

    tid = await _make_tenant(worker_session)
    uid = await _make_usuario(worker_session, tid)
    mid = await _make_materia(worker_session, tid)
    lote_id = uuid.uuid4()

    coms = []
    for i in range(3):
        c = await _encolar_comunicacion(
            worker_session, tid, uid, mid, lote_id, email=f"d{i}@x.com"
        )
        coms.append(c)
    await worker_session.commit()

    # Canal: fails for the first call, succeeds for the rest
    call_count = 0

    async def canal_selective(destinatario, asunto, cuerpo):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("First one fails")
        return True

    canal = MagicMock()
    canal.enviar = canal_selective
    crypto = CryptoService(_TEST_KEY)

    result = await procesar_pendientes(
        worker_session, canal,
        tenant_id=tid, crypto=crypto, requiere_aprobacion=False,
    )
    await worker_session.commit()

    assert result["errores"] == 1
    assert result["enviados"] == 2

    repo = ComunicacionRepository(session=worker_session, tenant_id=tid)
    all_coms = await repo.list_cola(lote_id=lote_id)
    estados = {c.estado for c in all_coms}
    assert EstadoComunicacion.Error.value in estados
    assert EstadoComunicacion.Enviado.value in estados


# ---------------------------------------------------------------------------
# Task 6.4 — approval gate
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_approval_gate_solo_despacha_aprobados(worker_session):
    """With requiere_aprobacion=True, only approved messages are dispatched."""
    from app.workers.comunicacion_worker import procesar_pendientes  # noqa: PLC0415
    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415

    tid = await _make_tenant(worker_session)
    uid = await _make_usuario(worker_session, tid)
    mid = await _make_materia(worker_session, tid)
    lote_id = uuid.uuid4()

    # Create 2: one approved, one not
    com_aprobado = await _encolar_comunicacion(
        worker_session, tid, uid, mid, lote_id,
        email="aprobado@x.com", aprobado=True, aprobador_id=uid,
    )
    com_no_aprobado = await _encolar_comunicacion(
        worker_session, tid, uid, mid, lote_id,
        email="noaprobado@x.com", aprobado=False,
    )
    await worker_session.commit()

    canal = _make_canal_exitoso()
    crypto = CryptoService(_TEST_KEY)

    result = await procesar_pendientes(
        worker_session, canal,
        tenant_id=tid, crypto=crypto, requiere_aprobacion=True,
    )
    await worker_session.commit()

    assert result["enviados"] == 1
    assert result["errores"] == 0

    repo = ComunicacionRepository(session=worker_session, tenant_id=tid)
    aprobado_updated = await repo.get(com_aprobado.id)
    no_aprobado_updated = await repo.get(com_no_aprobado.id)

    assert aprobado_updated.estado == EstadoComunicacion.Enviado.value
    assert no_aprobado_updated.estado == EstadoComunicacion.Pendiente.value  # untouched


@_requires_db
@pytest.mark.asyncio
async def test_sin_aprobacion_requerida_despacha_todos(worker_session):
    """With requiere_aprobacion=False, all Pendiente messages are dispatched."""
    from app.workers.comunicacion_worker import procesar_pendientes  # noqa: PLC0415
    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415

    tid = await _make_tenant(worker_session)
    uid = await _make_usuario(worker_session, tid)
    mid = await _make_materia(worker_session, tid)
    lote_id = uuid.uuid4()

    for i in range(3):
        await _encolar_comunicacion(
            worker_session, tid, uid, mid, lote_id, email=f"d{i}@x.com", aprobado=False
        )
    await worker_session.commit()

    canal = _make_canal_exitoso()
    crypto = CryptoService(_TEST_KEY)

    result = await procesar_pendientes(
        worker_session, canal,
        tenant_id=tid, crypto=crypto, requiere_aprobacion=False,
    )
    await worker_session.commit()

    assert result["enviados"] == 3
    assert result["errores"] == 0


@_requires_db
@pytest.mark.asyncio
async def test_config_ausente_fail_safe_no_despacha(worker_session):
    """When requiere_aprobacion is omitted (default True), unapproved are not dispatched."""
    from app.workers.comunicacion_worker import procesar_pendientes  # noqa: PLC0415

    tid = await _make_tenant(worker_session)
    uid = await _make_usuario(worker_session, tid)
    mid = await _make_materia(worker_session, tid)
    lote_id = uuid.uuid4()

    await _encolar_comunicacion(
        worker_session, tid, uid, mid, lote_id, email="d@x.com", aprobado=False
    )
    await worker_session.commit()

    canal = _make_canal_exitoso()
    crypto = CryptoService(_TEST_KEY)

    # Call WITHOUT requiere_aprobacion — default is True (fail-safe)
    result = await procesar_pendientes(
        worker_session, canal,
        tenant_id=tid, crypto=crypto,
    )
    await worker_session.commit()

    # Nothing was dispatched — fail-safe holds
    assert result["enviados"] == 0
    assert result["errores"] == 0
    canal.enviar.assert_not_called()


# ---------------------------------------------------------------------------
# Task 6.5 — cancellation race
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_mensaje_cancelado_no_se_despacha(worker_session):
    """Worker skips a message that was cancelled before it could take it."""
    from app.workers.comunicacion_worker import procesar_pendientes  # noqa: PLC0415
    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415

    tid = await _make_tenant(worker_session)
    uid = await _make_usuario(worker_session, tid)
    mid = await _make_materia(worker_session, tid)
    lote_id = uuid.uuid4()

    # Create in Cancelado state (simulates cancellation winning the race)
    com = await _encolar_comunicacion(
        worker_session, tid, uid, mid, lote_id,
        estado=EstadoComunicacion.Cancelado,
    )
    await worker_session.commit()

    canal = _make_canal_exitoso()
    crypto = CryptoService(_TEST_KEY)

    result = await procesar_pendientes(
        worker_session, canal,
        tenant_id=tid, crypto=crypto, requiere_aprobacion=False,
    )
    await worker_session.commit()

    assert result["enviados"] == 0
    assert result["saltados"] == 0  # not even in the list (list_despachables filters out Cancelado)
    canal.enviar.assert_not_called()

    # State unchanged
    repo = ComunicacionRepository(session=worker_session, tenant_id=tid)
    refreshed = await repo.get(com.id)
    assert refreshed.estado == EstadoComunicacion.Cancelado.value


@_requires_db
@pytest.mark.asyncio
async def test_resto_del_lote_procesado_cuando_uno_cancelado(worker_session):
    """When one message was cancelled, the worker still processes the rest."""
    from app.workers.comunicacion_worker import procesar_pendientes  # noqa: PLC0415
    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415

    tid = await _make_tenant(worker_session)
    uid = await _make_usuario(worker_session, tid)
    mid = await _make_materia(worker_session, tid)
    lote_id = uuid.uuid4()

    # One Pendiente, one Cancelado
    com_pendiente = await _encolar_comunicacion(
        worker_session, tid, uid, mid, lote_id, email="d1@x.com",
        estado=EstadoComunicacion.Pendiente,
    )
    com_cancelado = await _encolar_comunicacion(
        worker_session, tid, uid, mid, lote_id, email="d2@x.com",
        estado=EstadoComunicacion.Cancelado,
    )
    await worker_session.commit()

    canal = _make_canal_exitoso()
    crypto = CryptoService(_TEST_KEY)

    result = await procesar_pendientes(
        worker_session, canal,
        tenant_id=tid, crypto=crypto, requiere_aprobacion=False,
    )
    await worker_session.commit()

    assert result["enviados"] == 1

    repo = ComunicacionRepository(session=worker_session, tenant_id=tid)
    p_updated = await repo.get(com_pendiente.id)
    c_updated = await repo.get(com_cancelado.id)

    assert p_updated.estado == EstadoComunicacion.Enviado.value
    assert c_updated.estado == EstadoComunicacion.Cancelado.value  # unchanged

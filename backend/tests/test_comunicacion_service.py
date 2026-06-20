"""
tests/test_comunicacion_service.py — TDD integration tests for ComunicacionService.

Group 5 tasks:
  5.1 — preview renders variables and does NOT persist any Comunicacion
  5.2 — encolar_lote creates N Comunicacion rows, destinatario is ciphertext in DB
  5.3 — encolar_lote emits a single COMUNICACION_ENVIAR audit event
  5.4 — aprobar sets aprobado_at/aprobado_por from JWT
  5.5 — cancelar: Pendiente → Cancelado; rejecting Enviando → error
  5.6 — listar_cola decrypts destinatario in response

Requires TEST_DATABASE_URL (real DB — no mocks per project rules).
Canal (SMTP) is mocked only in worker tests; service tests do not invoke the canal.

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

from app.core.auth_context import CurrentUser
from app.core.crypto import CryptoService
from app.core.database import Base, build_engine
from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.schemas.comunicacion import (
    AprobarItemRequest,
    AprobarLoteRequest,
    CancelarItemRequest,
    CancelarLoteRequest,
    ColaQuery,
    DestinatarioLote,
    DestinatarioPreview,
    EncolarLoteRequest,
    PreviewRequest,
)

_requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping comunicacion service integration tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Schema fixtures (reuse pattern from test_calificaciones.py)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def svc_engine() -> AsyncEngine:
    """Module-scoped engine with full schema including audit_log and comunicacion."""
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
async def svc_session(svc_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(svc_engine, expire_on_commit=False)
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
    t = Tenant(slug=f"svctest-{uuid.uuid4().hex[:8]}", nombre="Svc Test", activo=True)
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


def _make_current_user(user_id: uuid.UUID, tenant_id: uuid.UUID) -> CurrentUser:
    return CurrentUser(user_id=user_id, tenant_id=tenant_id, roles=[])


def _make_service(session: AsyncSession, tenant_id: uuid.UUID):
    from app.services.audit_service import AuditService  # noqa: PLC0415
    from app.services.comunicacion_service import ComunicacionService  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    audit_svc = AuditService(session=session, tenant_id=tenant_id)
    return ComunicacionService(
        session=session, tenant_id=tenant_id, crypto=crypto, audit_svc=audit_svc
    )


# ---------------------------------------------------------------------------
# Task 5.1 — preview does NOT persist
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_preview_renderiza_variables(svc_session):
    """preview renders variables and returns results without persisting."""
    tid = await _make_tenant(svc_session)
    uid = await _make_usuario(svc_session, tid)
    mid = await _make_materia(svc_session, tid)
    await svc_session.commit()

    svc = _make_service(svc_session, tid)
    current_user = _make_current_user(uid, tid)

    req = PreviewRequest(
        materia_id=mid,
        asunto="Hola {{nombre_alumno}}",
        cuerpo="Tu nota en {{materia}} es {{nota}}",
        destinatarios=[
            DestinatarioPreview(
                email="ana@example.com",
                variables={"nombre_alumno": "Ana", "materia": "Prog I", "nota": "8"},
            )
        ],
    )
    resp = await svc.preview(req, current_user)

    assert len(resp.resultados) == 1
    assert resp.resultados[0].asunto_renderizado == "Hola Ana"
    assert resp.resultados[0].cuerpo_renderizado == "Tu nota en Prog I es 8"


@_requires_db
@pytest.mark.asyncio
async def test_preview_no_persiste(svc_session):
    """preview does NOT create any Comunicacion rows."""
    import sqlalchemy as sa  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    uid = await _make_usuario(svc_session, tid)
    mid = await _make_materia(svc_session, tid)
    await svc_session.commit()

    svc = _make_service(svc_session, tid)
    current_user = _make_current_user(uid, tid)

    req = PreviewRequest(
        materia_id=mid,
        asunto="Hola {{nombre}}",
        cuerpo="body",
        destinatarios=[DestinatarioPreview(email="x@x.com", variables={"nombre": "X"})],
    )
    await svc.preview(req, current_user)
    await svc_session.commit()

    # Verify table is empty for this tenant
    from app.models.comunicacion import Comunicacion  # noqa: PLC0415
    result = await svc_session.execute(
        sa.select(Comunicacion).where(Comunicacion.tenant_id == tid)
    )
    rows = result.scalars().all()
    assert len(rows) == 0


@_requires_db
@pytest.mark.asyncio
async def test_preview_variable_ausente(svc_session):
    """preview leaves missing variables as literal tokens."""
    tid = await _make_tenant(svc_session)
    uid = await _make_usuario(svc_session, tid)
    mid = await _make_materia(svc_session, tid)
    await svc_session.commit()

    svc = _make_service(svc_session, tid)
    current_user = _make_current_user(uid, tid)

    req = PreviewRequest(
        materia_id=mid,
        asunto="Hola {{desconocido}}",
        cuerpo="body",
        destinatarios=[DestinatarioPreview(email="x@x.com", variables={})],
    )
    resp = await svc.preview(req, current_user)
    assert resp.resultados[0].asunto_renderizado == "Hola {{desconocido}}"


# ---------------------------------------------------------------------------
# Task 5.2 — encolar_lote persists with encrypted destinatario
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_encolar_lote_crea_una_comunicacion_por_destinatario(svc_session):
    """encolar_lote creates one Comunicacion per recipient."""
    import sqlalchemy as sa  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    uid = await _make_usuario(svc_session, tid)
    mid = await _make_materia(svc_session, tid)
    await svc_session.commit()

    svc = _make_service(svc_session, tid)
    current_user = _make_current_user(uid, tid)

    req = EncolarLoteRequest(
        materia_id=mid,
        asunto="Hola {{nombre}}",
        cuerpo="body",
        destinatarios=[
            DestinatarioLote(email=f"d{i}@example.com", variables={"nombre": f"D{i}"})
            for i in range(3)
        ],
    )
    resp = await svc.encolar_lote(req, current_user)
    await svc_session.commit()

    assert resp.cantidad == 3
    assert resp.lote_id is not None

    # Verify 3 rows in DB
    from app.models.comunicacion import Comunicacion  # noqa: PLC0415
    result = await svc_session.execute(
        sa.select(Comunicacion).where(Comunicacion.tenant_id == tid)
    )
    rows = result.scalars().all()
    assert len(rows) == 3
    assert all(r.lote_id == resp.lote_id for r in rows)


@_requires_db
@pytest.mark.asyncio
async def test_encolar_lote_destinatario_cifrado_en_db(svc_session):
    """encolar_lote stores ciphertext (not plaintext email) in DB."""
    import sqlalchemy as sa  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    uid = await _make_usuario(svc_session, tid)
    mid = await _make_materia(svc_session, tid)
    await svc_session.commit()

    svc = _make_service(svc_session, tid)
    current_user = _make_current_user(uid, tid)
    plaintext_email = "alumno@ejemplo.com"

    req = EncolarLoteRequest(
        materia_id=mid,
        asunto="subj",
        cuerpo="body",
        destinatarios=[DestinatarioLote(email=plaintext_email, variables={})],
    )
    resp = await svc.encolar_lote(req, current_user)
    await svc_session.commit()

    # Fetch raw DB value — must be ciphertext, not plaintext
    from app.models.comunicacion import Comunicacion  # noqa: PLC0415
    result = await svc_session.execute(
        sa.select(Comunicacion).where(Comunicacion.tenant_id == tid)
    )
    row = result.scalars().first()
    assert row is not None
    assert row.destinatario != plaintext_email   # must be ciphertext
    assert "@" not in row.destinatario            # no plain email in DB


@_requires_db
@pytest.mark.asyncio
async def test_encolar_lote_enviado_por_del_jwt(svc_session):
    """encolar_lote sets enviado_por from the JWT actor, ignoring any body value."""
    import sqlalchemy as sa  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    uid = await _make_usuario(svc_session, tid)
    mid = await _make_materia(svc_session, tid)
    await svc_session.commit()

    svc = _make_service(svc_session, tid)
    current_user = _make_current_user(uid, tid)

    req = EncolarLoteRequest(
        materia_id=mid,
        asunto="subj",
        cuerpo="body",
        destinatarios=[DestinatarioLote(email="x@x.com", variables={})],
    )
    await svc.encolar_lote(req, current_user)
    await svc_session.commit()

    from app.models.comunicacion import Comunicacion  # noqa: PLC0415
    result = await svc_session.execute(
        sa.select(Comunicacion).where(Comunicacion.tenant_id == tid)
    )
    row = result.scalars().first()
    assert row.enviado_por == uid  # must come from JWT


# ---------------------------------------------------------------------------
# Task 5.3 — encolar_lote emits ONE audit event
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_encolar_lote_emite_un_unico_audit_event(svc_session):
    """encolar_lote emits exactly ONE COMUNICACION_ENVIAR audit log per lote."""
    import sqlalchemy as sa  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    uid = await _make_usuario(svc_session, tid)
    mid = await _make_materia(svc_session, tid)
    await svc_session.commit()

    svc = _make_service(svc_session, tid)
    current_user = _make_current_user(uid, tid)

    req = EncolarLoteRequest(
        materia_id=mid,
        asunto="subj",
        cuerpo="body",
        destinatarios=[
            DestinatarioLote(email=f"d{i}@example.com", variables={})
            for i in range(5)
        ],
    )
    await svc.encolar_lote(req, current_user)
    await svc_session.commit()

    # Exactly one audit event should exist
    from app.models.audit_log import AuditLog  # noqa: PLC0415
    from app.services.audit_codes import AccionAuditoria  # noqa: PLC0415
    result = await svc_session.execute(
        sa.select(AuditLog).where(
            AuditLog.tenant_id == tid,
            AuditLog.accion == str(AccionAuditoria.COMUNICACION_ENVIAR),
        )
    )
    audit_rows = result.scalars().all()
    assert len(audit_rows) == 1  # ONE per lote, not per recipient


# ---------------------------------------------------------------------------
# Task 5.4 — aprobar
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_aprobar_lote_setea_aprobado_por_del_jwt(svc_session):
    """aprobar_lote sets aprobado_por from the JWT."""
    tid = await _make_tenant(svc_session)
    uid = await _make_usuario(svc_session, tid)
    aprobador_id = await _make_usuario(svc_session, tid)
    mid = await _make_materia(svc_session, tid)
    await svc_session.commit()

    svc_encolador = _make_service(svc_session, tid)
    svc_aprobador = _make_service(svc_session, tid)
    actor = _make_current_user(uid, tid)
    aprobador = _make_current_user(aprobador_id, tid)

    # Enqueue a batch
    req = EncolarLoteRequest(
        materia_id=mid,
        asunto="subj",
        cuerpo="body",
        destinatarios=[DestinatarioLote(email="x@x.com", variables={})],
    )
    enqueue_resp = await svc_encolador.encolar_lote(req, actor)
    await svc_session.commit()

    # Approve by lote
    updated = await svc_aprobador.aprobar_lote(
        AprobarLoteRequest(lote_id=enqueue_resp.lote_id),
        aprobador,
    )
    await svc_session.commit()

    assert updated == 1

    # Check aprobado_por == aprobador_id (from JWT, not from body)
    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415
    repo = ComunicacionRepository(session=svc_session, tenant_id=tid)
    coms = await repo.list_cola(lote_id=enqueue_resp.lote_id)
    assert coms[0].aprobado_por == aprobador_id


@_requires_db
@pytest.mark.asyncio
async def test_aprobar_item_individual(svc_session):
    """aprobar_item approves only the specified Comunicacion."""
    import sqlalchemy as sa  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    uid = await _make_usuario(svc_session, tid)
    aprobador_id = await _make_usuario(svc_session, tid)
    mid = await _make_materia(svc_session, tid)
    await svc_session.commit()

    svc = _make_service(svc_session, tid)
    actor = _make_current_user(uid, tid)
    aprobador = _make_current_user(aprobador_id, tid)

    req = EncolarLoteRequest(
        materia_id=mid,
        asunto="subj",
        cuerpo="body",
        destinatarios=[
            DestinatarioLote(email="a@x.com", variables={}),
            DestinatarioLote(email="b@x.com", variables={}),
        ],
    )
    enqueue_resp = await svc.encolar_lote(req, actor)
    await svc_session.commit()

    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415
    repo = ComunicacionRepository(session=svc_session, tenant_id=tid)
    coms = await repo.list_cola(lote_id=enqueue_resp.lote_id)
    target_id = coms[0].id

    await svc.aprobar_item(AprobarItemRequest(comunicacion_id=target_id), aprobador)
    await svc_session.commit()

    refreshed = await repo.list_cola(lote_id=enqueue_resp.lote_id)
    approved = [c for c in refreshed if c.aprobado_at is not None]
    not_approved = [c for c in refreshed if c.aprobado_at is None]

    assert len(approved) == 1
    assert approved[0].id == target_id
    assert len(not_approved) == 1


# ---------------------------------------------------------------------------
# Task 5.5 — cancelar
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_cancelar_pendiente_ok(svc_session):
    """cancelar_item transitions Pendiente → Cancelado successfully."""
    tid = await _make_tenant(svc_session)
    uid = await _make_usuario(svc_session, tid)
    mid = await _make_materia(svc_session, tid)
    await svc_session.commit()

    svc = _make_service(svc_session, tid)
    actor = _make_current_user(uid, tid)

    req = EncolarLoteRequest(
        materia_id=mid,
        asunto="subj",
        cuerpo="body",
        destinatarios=[DestinatarioLote(email="x@x.com", variables={})],
    )
    enqueue_resp = await svc.encolar_lote(req, actor)
    await svc_session.commit()

    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415
    repo = ComunicacionRepository(session=svc_session, tenant_id=tid)
    coms = await repo.list_cola(lote_id=enqueue_resp.lote_id)
    target_id = coms[0].id

    await svc.cancelar_item(CancelarItemRequest(comunicacion_id=target_id), actor)
    await svc_session.commit()

    updated = await repo.get(target_id)
    assert updated.estado == EstadoComunicacion.Cancelado.value


@_requires_db
@pytest.mark.asyncio
async def test_cancelar_enviando_lanza_error(svc_session):
    """cancelar_item raises ValueError when state is Enviando (invalid transition)."""
    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    uid = await _make_usuario(svc_session, tid)
    mid = await _make_materia(svc_session, tid)
    await svc_session.commit()

    svc = _make_service(svc_session, tid)
    actor = _make_current_user(uid, tid)

    req = EncolarLoteRequest(
        materia_id=mid,
        asunto="subj",
        cuerpo="body",
        destinatarios=[DestinatarioLote(email="x@x.com", variables={})],
    )
    enqueue_resp = await svc.encolar_lote(req, actor)
    await svc_session.commit()

    # Transition to Enviando to simulate worker taking it
    repo = ComunicacionRepository(session=svc_session, tenant_id=tid)
    coms = await repo.list_cola(lote_id=enqueue_resp.lote_id)
    com_id = coms[0].id

    await repo.aplicar_transicion_condicional(
        com_id, desde=EstadoComunicacion.Pendiente, hacia=EstadoComunicacion.Enviando
    )
    await svc_session.commit()

    # Try to cancel — should raise ValueError
    with pytest.raises(ValueError, match="cancelar"):
        await svc.cancelar_item(CancelarItemRequest(comunicacion_id=com_id), actor)


# ---------------------------------------------------------------------------
# Task 5.6 — listar_cola decrypts destinatario
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_listar_cola_descifra_destinatario(svc_session):
    """listar_cola returns plaintext email in destinatario (decrypted)."""
    tid = await _make_tenant(svc_session)
    uid = await _make_usuario(svc_session, tid)
    mid = await _make_materia(svc_session, tid)
    await svc_session.commit()

    svc = _make_service(svc_session, tid)
    actor = _make_current_user(uid, tid)
    plaintext_email = "alumno.real@example.com"

    req = EncolarLoteRequest(
        materia_id=mid,
        asunto="subj",
        cuerpo="body",
        destinatarios=[DestinatarioLote(email=plaintext_email, variables={})],
    )
    enqueue_resp = await svc.encolar_lote(req, actor)
    await svc_session.commit()

    result = await svc.listar_cola(ColaQuery(lote_id=enqueue_resp.lote_id), actor)

    assert len(result) == 1
    assert result[0].destinatario == plaintext_email  # decrypted in response


@_requires_db
@pytest.mark.asyncio
async def test_listar_cola_aislamiento_tenant(svc_session):
    """listar_cola only returns rows for the requesting tenant."""
    tid_a = await _make_tenant(svc_session)
    tid_b = await _make_tenant(svc_session)
    uid_a = await _make_usuario(svc_session, tid_a)
    uid_b = await _make_usuario(svc_session, tid_b)
    mid_a = await _make_materia(svc_session, tid_a)
    mid_b = await _make_materia(svc_session, tid_b)
    await svc_session.commit()

    svc_a = _make_service(svc_session, tid_a)
    svc_b = _make_service(svc_session, tid_b)
    actor_a = _make_current_user(uid_a, tid_a)
    actor_b = _make_current_user(uid_b, tid_b)

    shared_lote_id_concept = None  # they get different lote_ids

    req_a = EncolarLoteRequest(
        materia_id=mid_a, asunto="s", cuerpo="b",
        destinatarios=[DestinatarioLote(email="a@a.com", variables={})],
    )
    req_b = EncolarLoteRequest(
        materia_id=mid_b, asunto="s", cuerpo="b",
        destinatarios=[DestinatarioLote(email="b@b.com", variables={})],
    )
    resp_a = await svc_a.encolar_lote(req_a, actor_a)
    resp_b = await svc_b.encolar_lote(req_b, actor_b)
    await svc_session.commit()

    # Tenant A querying for Tenant B's lote returns empty
    result = await svc_a.listar_cola(ColaQuery(lote_id=resp_b.lote_id), actor_a)
    assert result == []

    # Each tenant only sees their own
    result_a = await svc_a.listar_cola(ColaQuery(), actor_a)
    result_b = await svc_b.listar_cola(ColaQuery(), actor_b)

    a_ids = {r.lote_id for r in result_a}
    b_ids = {r.lote_id for r in result_b}
    assert a_ids.isdisjoint(b_ids)

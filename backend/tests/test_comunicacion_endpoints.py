"""
tests/test_comunicacion_endpoints.py — Integration HTTP tests for comunicaciones endpoints.

Group 9 tasks:
  9.1 — POST /preview renders variables, no DB rows; 403 without permission
  9.2 — POST / encola lote; destinatario cifrado en DB; enviado_por del JWT; auditoría; 403
  9.3 — GET / filtra por lote_id/estado; descifra destinatario; 403
  9.4 — POST /aprobar: aprueba lote e ítem individual; aprobado_por del JWT; 403
  9.5 — POST /cancelar: cancela Pendiente; rechaza Enviando; 403
  9.6 — aislamiento multi-tenant: lote_id de otro tenant → vacío/404
  9.7 — E2E FL-04: encolar → aprobar parte → worker → aprobados=Enviado, resto=Pendiente
  9.8 — coverage note (no automated assertion — see pytest --cov)

Requires TEST_DATABASE_URL (real DB; canal de email es mock en tests de worker).

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
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine
from app.models.comunicacion import Comunicacion, EstadoComunicacion

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping comunicacion endpoint integration tests",
)

_TEST_KEY = "a" * 64
NOW = datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def ep_engine() -> AsyncEngine:
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
async def ep_session(ep_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(ep_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# DB Helpers
# ---------------------------------------------------------------------------

async def _make_tenant(session: AsyncSession, suffix: str = "") -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=f"comep-{uuid.uuid4().hex[:8]}{suffix}", nombre="Com EP Test", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_auth_user(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.user import User  # noqa: PLC0415
    u = User(tenant_id=tid, email=f"ep_{uuid.uuid4().hex[:8]}@test.com", password_hash="x")
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


async def _make_domain_usuario(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.models.usuario import Usuario  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    email = f"du_{uuid.uuid4().hex[:8]}@test.com"
    u = Usuario(
        tenant_id=tid, nombre="Test", apellidos="User",
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


async def _make_materia(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(tenant_id=tid, codigo=f"MAT_{uuid.uuid4().hex[:6]}", nombre="Mat EP")
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


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


async def _assign_perm(session, tid, rol_id, perm_id, alcance="global"):
    from app.models.rol_permiso import AlcanceEnum, RolPermiso  # noqa: PLC0415
    rp = RolPermiso(
        tenant_id=tid, rol_id=rol_id, permiso_id=perm_id,
        alcance=AlcanceEnum.global_ if alcance == "global" else AlcanceEnum.propio,
    )
    session.add(rp)
    await session.flush()


async def _assign_rol(session, tid, uid, rol_id):
    from datetime import timedelta  # noqa: PLC0415
    from app.models.usuario_rol import UsuarioRol  # noqa: PLC0415
    ur = UsuarioRol(
        tenant_id=tid, user_id=uid, rol_id=rol_id,
        vigente_desde=NOW - timedelta(hours=1),
    )
    session.add(ur)
    await session.flush()


async def _setup_user_with_perms(
    session: AsyncSession, tid: uuid.UUID, perms: list[str]
) -> uuid.UUID:
    """Create auth user + rol + given perms. Returns user_id."""
    uid = await _make_auth_user(session, tid)
    rol_id = await _make_rol(session, tid, f"ROL_{uuid.uuid4().hex[:6]}")
    for clave in perms:
        perm_id = await _make_permiso(session, tid, clave)
        await _assign_perm(session, tid, rol_id, perm_id, alcance="global")
    await _assign_rol(session, tid, uid, rol_id)
    await session.commit()
    return uid


def _build_app(engine: AsyncEngine, uid: uuid.UUID, tid: uuid.UUID) -> FastAPI:
    """FastAPI app with comunicaciones router and mocked auth."""
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.core.dependencies import get_current_user, get_db  # noqa: PLC0415
    from app.api.v1.routers.comunicaciones import router as com_router  # noqa: PLC0415

    app = FastAPI()

    def mock_user() -> CurrentUser:
        return CurrentUser(user_id=uid, tenant_id=tid, roles=[])

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def mock_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_db] = mock_db

    app.include_router(com_router, prefix="/api/comunicaciones", tags=["comunicaciones"])
    return app


# ---------------------------------------------------------------------------
# Task 9.1 — POST /preview
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preview_renderiza_variables_sin_persistir(ep_session, ep_engine):
    """POST /preview renders variables and does NOT create any Comunicacion row."""
    tid = await _make_tenant(ep_session)
    mid = await _make_materia(ep_session, tid)
    uid = await _setup_user_with_perms(ep_session, tid, ["comunicacion:enviar"])

    app = _build_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/comunicaciones/preview", json={
            "materia_id": str(mid),
            "asunto": "Hola {{nombre_alumno}}",
            "cuerpo": "Tu nota en {{materia}} es {{nota}}",
            "destinatarios": [
                {"email": "ana@example.com", "variables": {"nombre_alumno": "Ana", "materia": "Prog I", "nota": "8"}},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["resultados"][0]["asunto_renderizado"] == "Hola Ana"

    # Verify no Comunicacion rows created
    count = await ep_session.scalar(
        sa.select(sa.func.count()).select_from(Comunicacion).where(Comunicacion.tenant_id == tid)
    )
    assert count == 0


@pytest.mark.asyncio
async def test_preview_sin_permiso_retorna_403(ep_session, ep_engine):
    """POST /preview without comunicacion:enviar → 403."""
    tid = await _make_tenant(ep_session)
    mid = await _make_materia(ep_session, tid)
    uid = await _setup_user_with_perms(ep_session, tid, [])  # no permissions

    app = _build_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/comunicaciones/preview", json={
            "materia_id": str(mid),
            "asunto": "subj",
            "cuerpo": "body",
            "destinatarios": [],
        })
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Task 9.2 — POST / (encolar lote)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_encolar_lote_crea_filas_cifradas_con_audit(ep_session, ep_engine):
    """POST / creates encrypted rows with correct enviado_por and emits audit."""
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.models.audit_log import AuditLog  # noqa: PLC0415

    tid = await _make_tenant(ep_session)
    mid = await _make_materia(ep_session, tid)
    uid = await _setup_user_with_perms(ep_session, tid, ["comunicacion:enviar"])

    app = _build_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/comunicaciones/", json={
            "materia_id": str(mid),
            "asunto": "Hola {{nombre}}",
            "cuerpo": "body",
            "destinatarios": [
                {"email": f"d{i}@example.com", "variables": {"nombre": f"D{i}"}}
                for i in range(3)
            ],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["cantidad"] == 3
        lote_id = uuid.UUID(data["lote_id"])

    # DB: 3 rows, encrypted destinatario, enviado_por=uid
    rows = (await ep_session.execute(
        sa.select(Comunicacion).where(Comunicacion.tenant_id == tid)
    )).scalars().all()
    assert len(rows) == 3
    assert all(r.lote_id == lote_id for r in rows)
    assert all(r.enviado_por == uid for r in rows)
    # Destinatario must be ciphertext (no @ in raw DB value)
    assert all("@" not in r.destinatario for r in rows)

    # Audit: exactly 1 event
    audits = (await ep_session.execute(
        sa.select(AuditLog).where(
            AuditLog.tenant_id == tid,
            AuditLog.accion == "COMUNICACION_ENVIAR",
        )
    )).scalars().all()
    assert len(audits) == 1


@pytest.mark.asyncio
async def test_encolar_sin_permiso_retorna_403(ep_session, ep_engine):
    """POST / without comunicacion:enviar → 403."""
    tid = await _make_tenant(ep_session)
    mid = await _make_materia(ep_session, tid)
    uid = await _setup_user_with_perms(ep_session, tid, [])

    app = _build_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/comunicaciones/", json={
            "materia_id": str(mid),
            "asunto": "s",
            "cuerpo": "b",
            "destinatarios": [],
        })
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Task 9.3 — GET / (queue listing)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_listar_cola_filtra_y_descifra(ep_session, ep_engine):
    """GET / returns filtered results with decrypted destinatario."""
    from app.core.crypto import CryptoService  # noqa: PLC0415

    tid = await _make_tenant(ep_session)
    mid = await _make_materia(ep_session, tid)
    uid = await _setup_user_with_perms(ep_session, tid, ["comunicacion:enviar"])
    plaintext_email = "alumno.conocido@example.com"

    app = _build_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Enqueue first
        enqueue_resp = await client.post("/api/comunicaciones/", json={
            "materia_id": str(mid),
            "asunto": "subj",
            "cuerpo": "body",
            "destinatarios": [{"email": plaintext_email, "variables": {}}],
        })
        assert enqueue_resp.status_code == 201
        lote_id = enqueue_resp.json()["lote_id"]

        # List by lote_id
        list_resp = await client.get(f"/api/comunicaciones/?lote_id={lote_id}")
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert len(items) == 1
        assert items[0]["destinatario"] == plaintext_email  # decrypted

        # Filter by estado=Pendiente
        list_pendiente = await client.get(
            f"/api/comunicaciones/?lote_id={lote_id}&estado=Pendiente"
        )
        assert list_pendiente.status_code == 200
        assert len(list_pendiente.json()) == 1


@pytest.mark.asyncio
async def test_listar_sin_permiso_retorna_403(ep_session, ep_engine):
    """GET / without comunicacion:enviar → 403."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_perms(ep_session, tid, [])

    app = _build_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/comunicaciones/")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Task 9.4 — POST /aprobar
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aprobar_lote_setea_aprobado_por_del_jwt(ep_session, ep_engine):
    """POST /aprobar sets aprobado_por from the JWT, not from the body."""
    tid = await _make_tenant(ep_session)
    mid = await _make_materia(ep_session, tid)
    uid_enviar = await _setup_user_with_perms(ep_session, tid, ["comunicacion:enviar"])
    uid_aprobar = await _setup_user_with_perms(ep_session, tid, ["comunicacion:aprobar"])

    # Enqueue with the sender user
    app_sender = _build_app(ep_engine, uid_enviar, tid)
    transport = ASGITransport(app=app_sender)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        enqueue_resp = await client.post("/api/comunicaciones/", json={
            "materia_id": str(mid),
            "asunto": "s",
            "cuerpo": "b",
            "destinatarios": [{"email": "x@x.com", "variables": {}}],
        })
        assert enqueue_resp.status_code == 201
        lote_id = enqueue_resp.json()["lote_id"]

    # Approve with the approver user
    app_approver = _build_app(ep_engine, uid_aprobar, tid)
    transport2 = ASGITransport(app=app_approver)
    async with AsyncClient(transport=transport2, base_url="http://test") as client:
        approve_resp = await client.post("/api/comunicaciones/aprobar", json={
            "lote_id": lote_id,
        })
        assert approve_resp.status_code == 200
        assert approve_resp.json()["actualizados"] == 1

    # Check aprobado_por == uid_aprobar (from JWT)
    rows = (await ep_session.execute(
        sa.select(Comunicacion).where(Comunicacion.tenant_id == tid)
    )).scalars().all()
    assert all(r.aprobado_por == uid_aprobar for r in rows)


@pytest.mark.asyncio
async def test_aprobar_sin_permiso_retorna_403(ep_session, ep_engine):
    """POST /aprobar without comunicacion:aprobar → 403."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_perms(ep_session, tid, ["comunicacion:enviar"])  # only enviar

    app = _build_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/comunicaciones/aprobar", json={
            "lote_id": str(uuid.uuid4()),
        })
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Task 9.5 — POST /cancelar
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancelar_pendiente_ok_via_endpoint(ep_session, ep_engine):
    """POST /cancelar cancels a Pendiente message successfully."""
    tid = await _make_tenant(ep_session)
    mid = await _make_materia(ep_session, tid)
    uid = await _setup_user_with_perms(
        ep_session, tid, ["comunicacion:enviar", "comunicacion:aprobar"]
    )

    app = _build_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        enqueue_resp = await client.post("/api/comunicaciones/", json={
            "materia_id": str(mid),
            "asunto": "s",
            "cuerpo": "b",
            "destinatarios": [{"email": "x@x.com", "variables": {}}],
        })
        lote_id = enqueue_resp.json()["lote_id"]

        cancel_resp = await client.post("/api/comunicaciones/cancelar", json={
            "lote_id": lote_id,
        })
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["cancelados"] >= 1

    # Verify state
    rows = (await ep_session.execute(
        sa.select(Comunicacion).where(Comunicacion.tenant_id == tid)
    )).scalars().all()
    assert all(r.estado == EstadoComunicacion.Cancelado.value for r in rows)


@pytest.mark.asyncio
async def test_cancelar_sin_permiso_retorna_403(ep_session, ep_engine):
    """POST /cancelar without comunicacion:aprobar → 403."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_perms(ep_session, tid, ["comunicacion:enviar"])

    app = _build_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/comunicaciones/cancelar", json={
            "lote_id": str(uuid.uuid4()),
        })
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Task 9.6 — Multi-tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lote_otro_tenant_retorna_vacio(ep_session, ep_engine):
    """GET / with lote_id from another tenant returns empty list."""
    tid_a = await _make_tenant(ep_session, "A")
    tid_b = await _make_tenant(ep_session, "B")
    mid_a = await _make_materia(ep_session, tid_a)
    mid_b = await _make_materia(ep_session, tid_b)
    uid_a = await _setup_user_with_perms(ep_session, tid_a, ["comunicacion:enviar"])
    uid_b = await _setup_user_with_perms(ep_session, tid_b, ["comunicacion:enviar"])

    # Tenant B enqueues a lote
    app_b = _build_app(ep_engine, uid_b, tid_b)
    transport_b = ASGITransport(app=app_b)
    async with AsyncClient(transport=transport_b, base_url="http://test") as client:
        resp = await client.post("/api/comunicaciones/", json={
            "materia_id": str(mid_b),
            "asunto": "s",
            "cuerpo": "b",
            "destinatarios": [{"email": "x@b.com", "variables": {}}],
        })
        lote_id_b = resp.json()["lote_id"]

    # Tenant A queries for Tenant B's lote — should get empty list
    app_a = _build_app(ep_engine, uid_a, tid_a)
    transport_a = ASGITransport(app=app_a)
    async with AsyncClient(transport=transport_a, base_url="http://test") as client:
        resp = await client.get(f"/api/comunicaciones/?lote_id={lote_id_b}")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Task 9.7 — E2E FL-04: encolar → aprobar parte → worker → estados correctos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_encolar_aprobar_worker(ep_session, ep_engine):
    """FL-04: encolar → approve half → worker processes → approved=Enviado, rest=Pendiente."""
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.workers.comunicacion_worker import procesar_pendientes  # noqa: PLC0415
    from app.repositories.comunicacion_repository import ComunicacionRepository  # noqa: PLC0415

    tid = await _make_tenant(ep_session)
    mid = await _make_materia(ep_session, tid)
    uid = await _setup_user_with_perms(
        ep_session, tid, ["comunicacion:enviar", "comunicacion:aprobar"]
    )

    app = _build_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)

    # Step 1: Encolar 4 recipients
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        enqueue_resp = await client.post("/api/comunicaciones/", json={
            "materia_id": str(mid),
            "asunto": "Hola {{nombre}}",
            "cuerpo": "body",
            "destinatarios": [
                {"email": f"d{i}@example.com", "variables": {"nombre": f"D{i}"}}
                for i in range(4)
            ],
        })
        assert enqueue_resp.status_code == 201
        lote_id = uuid.UUID(enqueue_resp.json()["lote_id"])

    # Step 2: Get the IDs
    repo = ComunicacionRepository(session=ep_session, tenant_id=tid)
    all_coms = await repo.list_cola(lote_id=lote_id)
    assert len(all_coms) == 4

    # Approve only 2 out of 4
    approved_ids = [all_coms[0].id, all_coms[1].id]
    for cid in approved_ids:
        await repo.marcar_aprobado_por_id(cid, aprobado_por=uid)
    await ep_session.commit()

    # Cancel one more
    await repo.aplicar_transicion_condicional(
        all_coms[2].id,
        desde=EstadoComunicacion.Pendiente,
        hacia=EstadoComunicacion.Cancelado,
    )
    await ep_session.commit()

    # Step 3: Run worker (with approval gate)
    canal = AsyncMock()
    canal.enviar = AsyncMock(return_value=True)
    crypto = CryptoService(_TEST_KEY)

    factory = async_sessionmaker(ep_engine, expire_on_commit=False)
    async with factory() as worker_session:
        result = await procesar_pendientes(
            worker_session, canal,
            tenant_id=tid, crypto=crypto, requiere_aprobacion=True,
        )
        await worker_session.commit()

    assert result["enviados"] == 2  # only the 2 approved ones

    # Verify final states
    final_coms = await repo.list_cola(lote_id=lote_id, include_deleted=False)
    states = {c.id: c.estado for c in final_coms}

    # Approved ones → Enviado
    assert states[all_coms[0].id] == EstadoComunicacion.Enviado.value
    assert states[all_coms[1].id] == EstadoComunicacion.Enviado.value
    # Cancelled one → Cancelado
    assert states[all_coms[2].id] == EstadoComunicacion.Cancelado.value
    # Unapproved one → still Pendiente
    assert states[all_coms[3].id] == EstadoComunicacion.Pendiente.value

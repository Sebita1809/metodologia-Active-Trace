"""
tests/test_equipos.py — Integration tests for Equipos API (C-08).

Tests for /api/equipos/* endpoints covering:
  Group 6  — mis-equipos and buscar usuarios
  Group 7  — asignacion masiva
  Group 8  — clonar equipo
  Group 9  — modificar vigencia y exportar
  Group 10 — multi-tenancy e integración

Requires TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import csv
import io
import os
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
import sqlalchemy as sa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping equipos endpoint tests",
)

_TEST_KEY = "a" * 64
NOW = datetime.now(tz=timezone.utc)
PAST = NOW - timedelta(hours=1)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def ep_engine() -> AsyncEngine:
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
async def ep_session(ep_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(ep_engine, expire_on_commit=False)
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
    t = Tenant(slug=f"eq-{uuid.uuid4().hex[:8]}", nombre="Equipo Test Tenant", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_user(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.user import User  # noqa: PLC0415
    u = User(
        tenant_id=tid,
        email=f"eq_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="x",
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
    m, a = clave.split(":", 1)
    p = Permiso(tenant_id=tid, clave=clave, modulo=m, accion=a)
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p.id


async def _assign_perm(
    session: AsyncSession, tid: uuid.UUID,
    rol_id: uuid.UUID, perm_id: uuid.UUID, alcance: str = "global",
) -> None:
    from app.models.rol_permiso import RolPermiso, AlcanceEnum  # noqa: PLC0415
    rp = RolPermiso(
        tenant_id=tid, rol_id=rol_id, permiso_id=perm_id,
        alcance=AlcanceEnum.global_ if alcance == "global" else AlcanceEnum.propio,
    )
    session.add(rp)
    await session.flush()


async def _assign_rol(
    session: AsyncSession, tid: uuid.UUID, uid: uuid.UUID, rol_id: uuid.UUID
) -> None:
    from app.models.usuario_rol import UsuarioRol  # noqa: PLC0415
    ur = UsuarioRol(tenant_id=tid, user_id=uid, rol_id=rol_id, vigente_desde=PAST)
    session.add(ur)
    await session.flush()


async def _make_domain_usuario(
    session: AsyncSession, tid: uuid.UUID,
    nombre: str = "Test", apellidos: str = "User", email: str | None = None,
) -> uuid.UUID:
    """Create a domain Usuario (not auth User) for FK references."""
    from app.models.usuario import Usuario  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    if email is None:
        email = f"usr_{uuid.uuid4().hex[:8]}@example.com"
    u = Usuario(
        tenant_id=tid,
        nombre=nombre,
        apellidos=apellidos,
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


async def _make_carrera(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.carrera import Carrera  # noqa: PLC0415
    c = Carrera(tenant_id=tid, codigo=f"CAR_{uuid.uuid4().hex[:6]}", nombre="Carrera Test")
    session.add(c)
    await session.flush()
    await session.refresh(c)
    return c.id


async def _make_cohorte(session: AsyncSession, tid: uuid.UUID, carrera_id: uuid.UUID) -> uuid.UUID:
    from app.models.cohorte import Cohorte  # noqa: PLC0415
    c = Cohorte(
        tenant_id=tid,
        carrera_id=carrera_id,
        nombre=f"COH_{uuid.uuid4().hex[:6]}",
        anio=2024,
        vig_desde=date.today(),
    )
    session.add(c)
    await session.flush()
    await session.refresh(c)
    return c.id


async def _make_materia(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(tenant_id=tid, codigo=f"MAT_{uuid.uuid4().hex[:6]}", nombre="Materia Test")
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


# ---------------------------------------------------------------------------
# App builders
# ---------------------------------------------------------------------------

def _build_equipos_app(engine: AsyncEngine, uid: uuid.UUID, tid: uuid.UUID) -> FastAPI:
    """Build FastAPI app with equipos router + dependency overrides."""
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.core.dependencies import get_current_user, get_db  # noqa: PLC0415
    from app.api.v1.routers.equipos import router as equipos_router  # noqa: PLC0415

    app = FastAPI()

    def mock_user() -> CurrentUser:
        return CurrentUser(user_id=uid, tenant_id=tid, roles=[])

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def mock_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_db] = mock_db

    app.include_router(equipos_router, prefix="/api/equipos", tags=["equipos"])
    return app


def _build_no_auth_equipos_app(engine: AsyncEngine) -> FastAPI:
    """Build equipos app WITHOUT overriding get_current_user — real 401 check fires."""
    from app.core.dependencies import get_db  # noqa: PLC0415
    from app.api.v1.routers.equipos import router as equipos_router  # noqa: PLC0415

    app = FastAPI()
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def mock_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = mock_db
    app.include_router(equipos_router, prefix="/api/equipos", tags=["equipos"])
    return app


# ---------------------------------------------------------------------------
# Helper: set up a user WITH equipos:asignar permission
# ---------------------------------------------------------------------------

async def _setup_user_with_asignar_perm(
    session: AsyncSession, tid: uuid.UUID
) -> uuid.UUID:
    """Create auth User + rol + equipos:asignar permiso + assign, return user id."""
    uid = await _make_user(session, tid)
    rol_id = await _make_rol(session, tid, f"COORD_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(session, tid, "equipos:asignar")
    await _assign_perm(session, tid, rol_id, perm_id)
    await _assign_rol(session, tid, uid, rol_id)
    return uid


# ---------------------------------------------------------------------------
# Group 6: mis-equipos and buscar usuarios
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_6_1_mis_equipos_returns_own_assignments(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """6.1 GET /api/equipos/mis-equipos — docente sees only their own assignments."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)

    # Create domain usuario matching the auth user
    domain_uid = await _make_domain_usuario(ep_session, tid)
    other_uid = await _make_domain_usuario(ep_session, tid)

    from app.models.asignacion import Asignacion  # noqa: PLC0415
    today = date.today()
    asig_mine = Asignacion(
        tenant_id=tid, usuario_id=domain_uid, rol="PROFESSOR",
        desde=today, comisiones=[],
    )
    asig_other = Asignacion(
        tenant_id=tid, usuario_id=other_uid, rol="TUTOR",
        desde=today, comisiones=[],
    )
    ep_session.add_all([asig_mine, asig_other])
    await ep_session.commit()

    # uid maps to domain_uid in the service because _get_svc uses current_user.user_id
    # BUT the app overrides with uid (auth user) — so we need to set uid = domain_uid
    # We build app with uid=domain_uid so the JWT identity matches domain usuario
    app = _build_equipos_app(ep_engine, domain_uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/equipos/mis-equipos")

    assert resp.status_code == 200
    body = resp.json()
    ids = {item["usuario_id"] for item in body}
    assert str(domain_uid) in ids
    assert str(other_uid) not in ids


@pytest.mark.asyncio
async def test_6_2_mis_equipos_filter_by_materia(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """6.2 GET /api/equipos/mis-equipos?materia_id=... returns correct subset."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    domain_uid = await _make_domain_usuario(ep_session, tid)
    materia_a = await _make_materia(ep_session, tid)
    materia_b = await _make_materia(ep_session, tid)

    from app.models.asignacion import Asignacion  # noqa: PLC0415
    today = date.today()
    asig_a = Asignacion(
        tenant_id=tid, usuario_id=domain_uid, rol="PROFESOR",
        desde=today, materia_id=materia_a, comisiones=[],
    )
    asig_b = Asignacion(
        tenant_id=tid, usuario_id=domain_uid, rol="TUTOR",
        desde=today, materia_id=materia_b, comisiones=[],
    )
    ep_session.add_all([asig_a, asig_b])
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, domain_uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/equipos/mis-equipos?materia_id={materia_a}")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["materia_id"] == str(materia_a)


@pytest.mark.asyncio
async def test_6_3_mis_equipos_estado_vigencia_computed(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """6.3 estado_vigencia is computed correctly (Vigente/Vencida based on dates)."""
    tid = await _make_tenant(ep_session)
    domain_uid = await _make_domain_usuario(ep_session, tid)

    from app.models.asignacion import Asignacion  # noqa: PLC0415
    today = date.today()
    yesterday = today - timedelta(days=1)

    asig_vigente = Asignacion(
        tenant_id=tid, usuario_id=domain_uid, rol="PROFESOR",
        desde=today - timedelta(days=5),
        hasta=today + timedelta(days=30),
        comisiones=[],
    )
    asig_vencida = Asignacion(
        tenant_id=tid, usuario_id=domain_uid, rol="TUTOR",
        desde=today - timedelta(days=10),
        hasta=yesterday,
        comisiones=[],
    )
    ep_session.add_all([asig_vigente, asig_vencida])
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, domain_uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/equipos/mis-equipos")

    assert resp.status_code == 200
    body = resp.json()
    estados = {item["estado_vigencia"] for item in body}
    assert "Vigente" in estados
    assert "Vencida" in estados


@pytest.mark.asyncio
async def test_6_4_mis_equipos_identity_not_spoofable(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """6.4 Identity cannot be spoofed via querystring — JWT identity always used."""
    tid = await _make_tenant(ep_session)
    domain_uid_a = await _make_domain_usuario(ep_session, tid)
    domain_uid_b = await _make_domain_usuario(ep_session, tid)

    from app.models.asignacion import Asignacion  # noqa: PLC0415
    today = date.today()
    # Create assignment for user A only
    asig_a = Asignacion(
        tenant_id=tid, usuario_id=domain_uid_a, rol="PROFESOR",
        desde=today, comisiones=[],
    )
    ep_session.add(asig_a)
    await ep_session.commit()

    # Authenticate as user B, try to pass user A's id as query param
    app = _build_equipos_app(ep_engine, domain_uid_b, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Even if user_id is passed as a query param, JWT identity should prevail
        resp = await client.get(f"/api/equipos/mis-equipos?usuario_id={domain_uid_a}")

    assert resp.status_code == 200
    body = resp.json()
    # User B has no assignments — must be empty (not seeing A's)
    ids = [item["usuario_id"] for item in body]
    assert str(domain_uid_a) not in ids


@pytest.mark.asyncio
async def test_6_5_mis_equipos_without_token_returns_401(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """6.5 GET /api/equipos/mis-equipos without token → 401."""
    app = _build_no_auth_equipos_app(ep_engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/equipos/mis-equipos")

    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


@pytest.mark.asyncio
async def test_6_6_buscar_usuarios_returns_matching(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """6.6 GET /api/equipos/usuarios/buscar?q=mar — returns users with match."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)

    await _make_domain_usuario(ep_session, tid, nombre="María", apellidos="García")
    await _make_domain_usuario(ep_session, tid, nombre="Marco", apellidos="López")
    await _make_domain_usuario(ep_session, tid, nombre="Juan", apellidos="Pérez")
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/equipos/usuarios/buscar?q=mar")

    assert resp.status_code == 200
    body = resp.json()
    # Should match María and Marco, not Juan
    nombres = [item["nombre"] for item in body]
    assert any("mar" in n.lower() for n in nombres)
    assert "Juan" not in nombres


@pytest.mark.asyncio
async def test_6_7_buscar_usuarios_short_query_returns_422(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """6.7 GET /api/equipos/usuarios/buscar?q=m — HTTP 422 for short query."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/equipos/usuarios/buscar?q=m")

    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"


@pytest.mark.asyncio
async def test_6_8_buscar_usuarios_no_pii_exposed(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """6.8 buscar_usuarios response does not expose email or PII ciphertexts."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)
    await _make_domain_usuario(ep_session, tid, nombre="Carlos", apellidos="Ruiz")
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/equipos/usuarios/buscar?q=car")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    item = body[0]
    # Only id, nombre, apellidos should be present — no email, no email_hash, no dni, etc.
    assert "email" not in item
    assert "email_hash" not in item
    assert "dni" not in item
    assert "cbu" not in item
    assert "id" in item
    assert "nombre" in item
    assert "apellidos" in item


# ---------------------------------------------------------------------------
# Group 7: asignación masiva
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_1_masiva_creates_3_assignments(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """7.1 POST /api/equipos/asignaciones/masiva with 3 usuario_ids → 201 + asignadas=3."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)

    u1 = await _make_domain_usuario(ep_session, tid)
    u2 = await _make_domain_usuario(ep_session, tid)
    u3 = await _make_domain_usuario(ep_session, tid)
    await ep_session.commit()

    today = date.today()
    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/equipos/asignaciones/masiva",
            json={
                "usuario_ids": [str(u1), str(u2), str(u3)],
                "rol": "TUTOR",
                "desde": str(today),
                "comisiones": [],
            },
        )

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["asignadas"] == 3


@pytest.mark.asyncio
async def test_7_2_masiva_empty_list_returns_422(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """7.2 POST /api/equipos/asignaciones/masiva with empty usuario_ids → 422."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/equipos/asignaciones/masiva",
            json={
                "usuario_ids": [],
                "rol": "TUTOR",
                "desde": str(date.today()),
                "comisiones": [],
            },
        )

    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"


@pytest.mark.asyncio
async def test_7_3_masiva_without_permission_returns_403(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """7.3 POST /api/equipos/asignaciones/masiva without equipos:asignar → 403."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)  # no permission
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/equipos/asignaciones/masiva",
            json={
                "usuario_ids": [str(uuid.uuid4())],
                "rol": "TUTOR",
                "desde": str(date.today()),
                "comisiones": [],
            },
        )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_7_4_masiva_invalid_usuario_rollback(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """7.4 masiva with non-existent usuario_id causes FK violation → rollback, no assignments created."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)
    valid_uid = await _make_domain_usuario(ep_session, tid)
    await ep_session.commit()

    # Use a random UUID that has no matching usuario row
    fake_uid = uuid.uuid4()

    today = date.today()
    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/equipos/asignaciones/masiva",
            json={
                "usuario_ids": [str(fake_uid)],
                "rol": "TUTOR",
                "desde": str(today),
                "comisiones": [],
            },
        )

    # FK violation should cause a 500 or similar error — not 201
    assert resp.status_code != 201, f"Expected non-201 for invalid FK, got {resp.status_code}"


@pytest.mark.asyncio
async def test_7_5_masiva_registers_audit_log(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """7.5 masiva registers AuditLog with accion=ASIGNACION_MODIFICAR and filas_afectadas=3."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)

    u1 = await _make_domain_usuario(ep_session, tid)
    u2 = await _make_domain_usuario(ep_session, tid)
    u3 = await _make_domain_usuario(ep_session, tid)
    await ep_session.commit()

    today = date.today()
    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/equipos/asignaciones/masiva",
            json={
                "usuario_ids": [str(u1), str(u2), str(u3)],
                "rol": "PROFESOR",
                "desde": str(today),
                "comisiones": [],
            },
        )

    assert resp.status_code == 201

    # Check AuditLog in DB
    from app.models.audit_log import AuditLog  # noqa: PLC0415
    result = await ep_session.execute(
        sa.select(AuditLog)
        .where(AuditLog.tenant_id == tid)
        .where(AuditLog.accion == "ASIGNACION_MODIFICAR")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1
    log = logs[-1]
    assert log.filas_afectadas == 3


# ---------------------------------------------------------------------------
# Group 8: clonar equipo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_8_1_clonar_clones_vigentes_to_destino(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """8.1 POST /api/equipos/asignaciones/clonar — clones 3 vigentes to destination."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)

    carrera_id = await _make_carrera(ep_session, tid)
    materia_origen = await _make_materia(ep_session, tid)
    cohorte_origen = await _make_cohorte(ep_session, tid, carrera_id)
    materia_destino = await _make_materia(ep_session, tid)
    cohorte_destino = await _make_cohorte(ep_session, tid, carrera_id)

    today = date.today()
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    u1 = await _make_domain_usuario(ep_session, tid)
    u2 = await _make_domain_usuario(ep_session, tid)
    u3 = await _make_domain_usuario(ep_session, tid)

    # 3 vigentes in origen
    for u in [u1, u2, u3]:
        asig = Asignacion(
            tenant_id=tid, usuario_id=u, rol="TUTOR",
            materia_id=materia_origen, cohorte_id=cohorte_origen,
            desde=today - timedelta(days=5),
            hasta=today + timedelta(days=30),
            comisiones=[],
        )
        ep_session.add(asig)
    await ep_session.commit()

    new_since = today + timedelta(days=31)
    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/equipos/asignaciones/clonar",
            json={
                "origen": {
                    "materia_id": str(materia_origen),
                    "cohorte_id": str(cohorte_origen),
                },
                "destino": {
                    "materia_id": str(materia_destino),
                    "cohorte_id": str(cohorte_destino),
                },
                "desde": str(new_since),
            },
        )

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["clonadas"] == 3


@pytest.mark.asyncio
async def test_8_2_clonar_empty_origin_returns_zero(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """8.2 clonar with no vigentes in origin → clonadas=0."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)
    carrera_id = await _make_carrera(ep_session, tid)
    materia_origen = await _make_materia(ep_session, tid)
    materia_destino = await _make_materia(ep_session, tid)
    cohorte_destino = await _make_cohorte(ep_session, tid, carrera_id)
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/equipos/asignaciones/clonar",
            json={
                "origen": {"materia_id": str(materia_origen)},
                "destino": {
                    "materia_id": str(materia_destino),
                    "cohorte_id": str(cohorte_destino),
                },
                "desde": str(date.today()),
            },
        )

    assert resp.status_code == 201
    assert resp.json()["clonadas"] == 0


@pytest.mark.asyncio
async def test_8_3_clonar_other_tenant_origin_isolation(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """8.3 clonar with origin from another tenant → clonadas=0 (isolation)."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    tid_a = await _make_tenant(ep_session)
    uid_a = await _setup_user_with_asignar_perm(ep_session, tid_a)

    t_b = Tenant(slug=f"eq-b-{uuid.uuid4().hex[:6]}", nombre="Tenant B", activo=True)
    ep_session.add(t_b)
    await ep_session.flush()
    await ep_session.refresh(t_b)
    tid_b = t_b.id

    # Create materia in tenant B
    materia_b = await _make_materia(ep_session, tid_b)
    user_b = await _make_domain_usuario(ep_session, tid_b)

    from app.models.asignacion import Asignacion  # noqa: PLC0415
    today = date.today()
    asig_b = Asignacion(
        tenant_id=tid_b, usuario_id=user_b, rol="TUTOR",
        materia_id=materia_b,
        desde=today - timedelta(days=5),
        hasta=today + timedelta(days=30),
        comisiones=[],
    )
    ep_session.add(asig_b)

    # Materia in tenant A for destination
    materia_a = await _make_materia(ep_session, tid_a)
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid_a, tid_a)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/equipos/asignaciones/clonar",
            json={
                # Try to reference tenant B's materia as origin
                "origen": {"materia_id": str(materia_b)},
                "destino": {"materia_id": str(materia_a)},
                "desde": str(today),
            },
        )

    assert resp.status_code == 201
    # Tenant A cannot see tenant B's assignments — should be 0
    assert resp.json()["clonadas"] == 0


@pytest.mark.asyncio
async def test_8_4_clonar_origin_assignments_unchanged(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """8.4 clonar — origin assignments are NOT modified (independent copies)."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)

    materia_origen = await _make_materia(ep_session, tid)
    materia_destino = await _make_materia(ep_session, tid)

    today = date.today()
    original_hasta = today + timedelta(days=30)

    from app.models.asignacion import Asignacion  # noqa: PLC0415
    u1 = await _make_domain_usuario(ep_session, tid)
    asig_orig = Asignacion(
        tenant_id=tid, usuario_id=u1, rol="TUTOR",
        materia_id=materia_origen,
        desde=today - timedelta(days=5),
        hasta=original_hasta,
        comisiones=[],
    )
    ep_session.add(asig_orig)
    await ep_session.commit()
    orig_id = asig_orig.id

    new_since = today + timedelta(days=31)
    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/equipos/asignaciones/clonar",
            json={
                "origen": {"materia_id": str(materia_origen)},
                "destino": {"materia_id": str(materia_destino)},
                "desde": str(new_since),
                "hasta": str(new_since + timedelta(days=60)),
            },
        )

    # Refresh origin from DB
    await ep_session.refresh(asig_orig)
    # Origin must still have original dates
    assert asig_orig.desde == today - timedelta(days=5)
    assert asig_orig.hasta == original_hasta
    assert asig_orig.materia_id == materia_origen


@pytest.mark.asyncio
async def test_8_5_clonar_registers_audit_log(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """8.5 clonar registers AuditLog with filas_afectadas = cloned count."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)
    materia_origen = await _make_materia(ep_session, tid)
    materia_destino = await _make_materia(ep_session, tid)

    today = date.today()
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    u1 = await _make_domain_usuario(ep_session, tid)
    u2 = await _make_domain_usuario(ep_session, tid)
    for u in [u1, u2]:
        ep_session.add(Asignacion(
            tenant_id=tid, usuario_id=u, rol="TUTOR",
            materia_id=materia_origen,
            desde=today - timedelta(days=1),
            comisiones=[],
        ))
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/equipos/asignaciones/clonar",
            json={
                "origen": {"materia_id": str(materia_origen)},
                "destino": {"materia_id": str(materia_destino)},
                "desde": str(today + timedelta(days=1)),
            },
        )

    assert resp.status_code == 201
    clonadas = resp.json()["clonadas"]

    from app.models.audit_log import AuditLog  # noqa: PLC0415
    result = await ep_session.execute(
        sa.select(AuditLog)
        .where(AuditLog.tenant_id == tid)
        .where(AuditLog.accion == "ASIGNACION_MODIFICAR")
        .order_by(AuditLog.created_at.desc())
    )
    logs = result.scalars().all()
    assert len(logs) >= 1
    assert logs[0].filas_afectadas == clonadas


# ---------------------------------------------------------------------------
# Group 9: modificar vigencia y exportar
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_9_1_modificar_vigencia_updates_and_returns_count(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.1 PATCH /api/equipos/asignaciones/vigencia → updates desde/hasta, returns {modificadas: N}."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)
    materia_id = await _make_materia(ep_session, tid)

    today = date.today()
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    u1 = await _make_domain_usuario(ep_session, tid)
    u2 = await _make_domain_usuario(ep_session, tid)
    for u in [u1, u2]:
        ep_session.add(Asignacion(
            tenant_id=tid, usuario_id=u, rol="TUTOR",
            materia_id=materia_id,
            desde=today - timedelta(days=5),
            comisiones=[],
        ))
    await ep_session.commit()

    new_desde = today + timedelta(days=1)
    new_hasta = today + timedelta(days=90)
    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            "/api/equipos/asignaciones/vigencia",
            json={
                "filtro": {"materia_id": str(materia_id)},
                "desde": str(new_desde),
                "hasta": str(new_hasta),
            },
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["modificadas"] == 2


@pytest.mark.asyncio
async def test_9_2_modificar_vigencia_no_matches_returns_zero(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.2 modificar vigencia with no matching filter → {modificadas: 0}."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            "/api/equipos/asignaciones/vigencia",
            json={
                "filtro": {"materia_id": str(uuid.uuid4())},
                "desde": str(date.today()),
            },
        )

    assert resp.status_code == 200
    assert resp.json()["modificadas"] == 0


@pytest.mark.asyncio
async def test_9_3_modificar_vigencia_null_hasta_sets_open_ended(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.3 modificar vigencia with hasta=null → sets open-ended validity."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)
    materia_id = await _make_materia(ep_session, tid)

    today = date.today()
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    u1 = await _make_domain_usuario(ep_session, tid)
    asig = Asignacion(
        tenant_id=tid, usuario_id=u1, rol="TUTOR",
        materia_id=materia_id,
        desde=today - timedelta(days=5),
        hasta=today + timedelta(days=10),
        comisiones=[],
    )
    ep_session.add(asig)
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            "/api/equipos/asignaciones/vigencia",
            json={
                "filtro": {"materia_id": str(materia_id)},
                "desde": str(today),
                "hasta": None,
            },
        )

    assert resp.status_code == 200
    assert resp.json()["modificadas"] == 1

    # Verify in DB that hasta is now NULL
    await ep_session.refresh(asig)
    assert asig.hasta is None


@pytest.mark.asyncio
async def test_9_4_modificar_vigencia_registers_audit_log(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.4 modificar vigencia registers AuditLog with filas_afectadas correct."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)
    materia_id = await _make_materia(ep_session, tid)

    today = date.today()
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    u1 = await _make_domain_usuario(ep_session, tid)
    ep_session.add(Asignacion(
        tenant_id=tid, usuario_id=u1, rol="TUTOR",
        materia_id=materia_id,
        desde=today - timedelta(days=1),
        comisiones=[],
    ))
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            "/api/equipos/asignaciones/vigencia",
            json={
                "filtro": {"materia_id": str(materia_id)},
                "desde": str(today),
            },
        )

    assert resp.status_code == 200
    modificadas = resp.json()["modificadas"]

    from app.models.audit_log import AuditLog  # noqa: PLC0415
    result = await ep_session.execute(
        sa.select(AuditLog)
        .where(AuditLog.tenant_id == tid)
        .where(AuditLog.accion == "ASIGNACION_MODIFICAR")
        .order_by(AuditLog.created_at.desc())
    )
    logs = result.scalars().all()
    assert logs[0].filas_afectadas == modificadas


@pytest.mark.asyncio
async def test_9_5_exportar_returns_200_csv(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.5 GET /api/equipos/asignaciones/exportar → 200, Content-Type text/csv."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/equipos/asignaciones/exportar")

    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "content-disposition" in resp.headers


@pytest.mark.asyncio
async def test_9_6_exportar_filter_by_materia(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.6 exportar with materia_id filter → CSV contains only rows for that materia."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)
    materia_a = await _make_materia(ep_session, tid)
    materia_b = await _make_materia(ep_session, tid)

    today = date.today()
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    u1 = await _make_domain_usuario(ep_session, tid)
    u2 = await _make_domain_usuario(ep_session, tid)
    ep_session.add(Asignacion(
        tenant_id=tid, usuario_id=u1, rol="TUTOR",
        materia_id=materia_a, desde=today, comisiones=[],
    ))
    ep_session.add(Asignacion(
        tenant_id=tid, usuario_id=u2, rol="PROFESOR",
        materia_id=materia_b, desde=today, comisiones=[],
    ))
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/equipos/asignaciones/exportar?materia_id={materia_a}")

    assert resp.status_code == 200
    content = resp.text
    lines = [l for l in content.strip().splitlines() if l]
    # Header + 1 data row
    assert len(lines) == 2


@pytest.mark.asyncio
async def test_9_7_exportar_without_permission_returns_403(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.7 exportar without equipos:asignar → 403."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)  # no permission
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/equipos/asignaciones/exportar")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_9_8_exportar_csv_has_expected_columns(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.8 exportar CSV has expected column headers."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)

    materia_id = await _make_materia(ep_session, tid)
    u1 = await _make_domain_usuario(ep_session, tid, nombre="Ana", apellidos="Soto")
    today = date.today()
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    ep_session.add(Asignacion(
        tenant_id=tid, usuario_id=u1, rol="TUTOR",
        materia_id=materia_id, desde=today, comisiones=[],
    ))
    await ep_session.commit()

    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/equipos/asignaciones/exportar")

    assert resp.status_code == 200
    content = resp.text
    reader = csv.reader(io.StringIO(content))
    header = next(reader)
    expected_cols = [
        "usuario_id", "nombre", "apellidos", "rol",
        "materia", "carrera", "cohorte",
        "comisiones", "desde", "hasta", "estado_vigencia",
    ]
    for col in expected_cols:
        assert col in header, f"Missing column: {col}"


# ---------------------------------------------------------------------------
# Group 10: Multi-tenancy e integración
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_10_1_mis_equipos_tenant_isolation(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.1 User from tenant B cannot see mis-equipos from tenant A."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    tid_a = await _make_tenant(ep_session)
    t_b = Tenant(slug=f"eq-iso-b-{uuid.uuid4().hex[:6]}", nombre="Tenant B Iso", activo=True)
    ep_session.add(t_b)
    await ep_session.flush()
    await ep_session.refresh(t_b)
    tid_b = t_b.id

    uid_b = await _make_user(ep_session, tid_b)
    domain_uid_a = await _make_domain_usuario(ep_session, tid_a)

    today = date.today()
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    ep_session.add(Asignacion(
        tenant_id=tid_a, usuario_id=domain_uid_a, rol="TUTOR",
        desde=today, comisiones=[],
    ))
    await ep_session.commit()

    # Authenticate as user from tenant B — same domain_uid_a won't be in tenant B scope
    app = _build_equipos_app(ep_engine, domain_uid_a, tid_b)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/equipos/mis-equipos")

    assert resp.status_code == 200
    # Since we're scoped to tenant B, should return empty
    assert resp.json() == []


@pytest.mark.asyncio
async def test_10_2_masiva_tenant_isolation(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.2 masiva from tenant A cannot assign users from tenant B."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    tid_a = await _make_tenant(ep_session)
    t_b = Tenant(slug=f"eq-iso-b2-{uuid.uuid4().hex[:6]}", nombre="Tenant B2 Iso", activo=True)
    ep_session.add(t_b)
    await ep_session.flush()
    await ep_session.refresh(t_b)
    tid_b = t_b.id

    uid_a = await _setup_user_with_asignar_perm(ep_session, tid_a)
    # Create a domain usuario in tenant B
    user_b = await _make_domain_usuario(ep_session, tid_b)
    await ep_session.commit()

    today = date.today()
    app = _build_equipos_app(ep_engine, uid_a, tid_a)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/equipos/asignaciones/masiva",
            json={
                "usuario_ids": [str(user_b)],
                "rol": "TUTOR",
                "desde": str(today),
                "comisiones": [],
            },
        )

    # FK constraint: usuario from tenant B doesn't satisfy tenant A scope
    # This should fail with a server error (FK violation) — not succeed
    assert resp.status_code != 201, f"Expected non-201 for cross-tenant assign, got {resp.status_code}"


@pytest.mark.asyncio
async def test_10_3_e2e_masiva_clonar_exportar(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.3 E2E: create team with masiva → clone to new cohort → export → verify CSV."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_asignar_perm(ep_session, tid)

    carrera_id = await _make_carrera(ep_session, tid)
    materia_a = await _make_materia(ep_session, tid)
    materia_b = await _make_materia(ep_session, tid)
    cohorte_origen = await _make_cohorte(ep_session, tid, carrera_id)
    cohorte_destino = await _make_cohorte(ep_session, tid, carrera_id)

    u1 = await _make_domain_usuario(ep_session, tid, nombre="Pedro", apellidos="Alves")
    u2 = await _make_domain_usuario(ep_session, tid, nombre="Laura", apellidos="Blanco")
    await ep_session.commit()

    today = date.today()
    app = _build_equipos_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: masiva — assign 2 users to materia_a/cohorte_origen
        masiva_resp = await client.post(
            "/api/equipos/asignaciones/masiva",
            json={
                "usuario_ids": [str(u1), str(u2)],
                "rol": "PROFESOR",
                "materia_id": str(materia_a),
                "cohorte_id": str(cohorte_origen),
                "desde": str(today - timedelta(days=5)),
                "comisiones": [],
            },
        )
        assert masiva_resp.status_code == 201
        assert masiva_resp.json()["asignadas"] == 2

        # Step 2: clonar from materia_a/cohorte_origen to materia_b/cohorte_destino
        clonar_resp = await client.post(
            "/api/equipos/asignaciones/clonar",
            json={
                "origen": {
                    "materia_id": str(materia_a),
                    "cohorte_id": str(cohorte_origen),
                },
                "destino": {
                    "materia_id": str(materia_b),
                    "cohorte_id": str(cohorte_destino),
                },
                "desde": str(today + timedelta(days=1)),
            },
        )
        assert clonar_resp.status_code == 201
        assert clonar_resp.json()["clonadas"] == 2

        # Step 3: export — filter by materia_b
        export_resp = await client.get(
            f"/api/equipos/asignaciones/exportar?materia_id={materia_b}"
        )
        assert export_resp.status_code == 200
        assert "text/csv" in export_resp.headers.get("content-type", "")

        content = export_resp.text
        lines = [l for l in content.strip().splitlines() if l]
        # Header + 2 data rows
        assert len(lines) == 3, f"Expected 3 lines (header + 2 rows), got {len(lines)}: {content}"

        # Verify CSV has expected columns
        reader = csv.reader(io.StringIO(content))
        header = next(reader)
        assert "usuario_id" in header
        assert "nombre" in header
        assert "estado_vigencia" in header

"""
tests/test_estructura_endpoints.py — Integration tests for the estructura academic API.

Group 9 tests: full HTTP integration tests for /api/admin/carreras,
/api/admin/cohortes, /api/admin/materias.

Requires TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

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
    reason="TEST_DATABASE_URL not set — skipping estructura endpoint tests",
)

NOW = datetime.now(tz=timezone.utc)
PAST = NOW - timedelta(hours=1)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def ep_engine() -> AsyncEngine:
    import app.models.tenant       # noqa: F401
    import app.models.user         # noqa: F401
    import app.models.rol          # noqa: F401
    import app.models.permiso      # noqa: F401
    import app.models.rol_permiso  # noqa: F401
    import app.models.usuario_rol  # noqa: F401
    import app.models.audit_log    # noqa: F401
    import app.models.carrera      # noqa: F401
    import app.models.cohorte      # noqa: F401
    import app.models.materia      # noqa: F401
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
    """Per-test session — callers MUST call commit() before HTTP calls."""
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
    t = Tenant(slug=f"ep-{uuid.uuid4().hex[:8]}", nombre="EP Test Tenant", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_user(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.user import User  # noqa: PLC0415
    u = User(
        tenant_id=tid,
        email=f"ep_{uuid.uuid4().hex[:8]}@test.com",
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


def _build_estructura_app(engine: AsyncEngine, uid: uuid.UUID, tid: uuid.UUID) -> FastAPI:
    """Build a minimal FastAPI app with estructura routers mounted.

    Uses dependency overrides so tests control user identity and DB session.
    """
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.core.dependencies import get_current_user, get_db  # noqa: PLC0415
    from app.api.v1.routers.carreras import router as carreras_router  # noqa: PLC0415
    from app.api.v1.routers.cohortes import router as cohortes_router  # noqa: PLC0415
    from app.api.v1.routers.materias import router as materias_router  # noqa: PLC0415

    app = FastAPI()

    def mock_user() -> CurrentUser:
        return CurrentUser(user_id=uid, tenant_id=tid, roles=[])

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def mock_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_db] = mock_db

    app.include_router(carreras_router, prefix="/api/admin/carreras", tags=["estructura"])
    app.include_router(cohortes_router, prefix="/api/admin/cohortes", tags=["estructura"])
    app.include_router(materias_router, prefix="/api/admin/materias", tags=["estructura"])
    return app


def _build_no_auth_app(engine: AsyncEngine, uid: uuid.UUID, tid: uuid.UUID) -> FastAPI:
    """Build app WITHOUT overriding get_current_user — real 401 check fires."""
    from app.core.dependencies import get_db  # noqa: PLC0415
    from app.api.v1.routers.carreras import router as carreras_router  # noqa: PLC0415

    app = FastAPI()

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def mock_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = mock_db
    app.include_router(carreras_router, prefix="/api/admin/carreras", tags=["estructura"])
    return app


# ---------------------------------------------------------------------------
# Group 9: Endpoint integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_9_1_post_carreras_without_token_returns_401(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.1 POST /api/admin/carreras without token → 401."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    await ep_session.commit()

    app = _build_no_auth_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/admin/carreras/",
            json={"codigo": "ISI", "nombre": "Ingeniería en Sistemas"},
        )

    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


@pytest.mark.asyncio
async def test_9_2_post_carreras_without_permission_returns_403(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.2 POST /api/admin/carreras without estructura:gestionar → 403."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    # No permissions assigned
    await ep_session.commit()

    app = _build_estructura_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/admin/carreras/",
            json={"codigo": "ISI", "nombre": "Ingeniería en Sistemas"},
        )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_9_3_post_carreras_with_admin_returns_201(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.3 POST /api/admin/carreras with valid ADMIN → 201 + correct body."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"ADMIN_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "estructura:gestionar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)
    await ep_session.commit()

    app = _build_estructura_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/admin/carreras/",
            json={"codigo": "ISI", "nombre": "Ingeniería en Sistemas"},
        )

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["codigo"] == "ISI"
    assert body["nombre"] == "Ingeniería en Sistemas"
    assert body["estado"] == "Activa"
    assert "id" in body
    assert body["tenant_id"] == str(tid)


@pytest.mark.asyncio
async def test_9_4_get_carreras_returns_only_current_tenant(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.4 GET /api/admin/carreras returns only current tenant's carreras."""
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.models.tenant import Tenant  # noqa: PLC0415

    tid_a = await _make_tenant(ep_session)
    uid_a = await _make_user(ep_session, tid_a)

    # Create another tenant with its own carrera
    t_b = Tenant(slug=f"ep-b-{uuid.uuid4().hex[:6]}", nombre="Tenant B", activo=True)
    ep_session.add(t_b)
    await ep_session.flush()
    await ep_session.refresh(t_b)
    tid_b = t_b.id

    # Carrera for tenant A
    c_a = Carrera(tenant_id=tid_a, codigo="A_ONLY", nombre="Carrera de A")
    # Carrera for tenant B
    c_b = Carrera(tenant_id=tid_b, codigo="B_ONLY", nombre="Carrera de B")
    ep_session.add_all([c_a, c_b])
    await ep_session.flush()
    await ep_session.commit()

    app = _build_estructura_app(ep_engine, uid_a, tid_a)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/admin/carreras/")

    assert resp.status_code == 200
    codigos = [c["codigo"] for c in resp.json()]
    assert "A_ONLY" in codigos
    assert "B_ONLY" not in codigos


@pytest.mark.asyncio
async def test_9_5_get_carrera_from_other_tenant_returns_404(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.5 GET /api/admin/carreras/{id} with ID from another tenant → 404."""
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.models.tenant import Tenant  # noqa: PLC0415

    tid_a = await _make_tenant(ep_session)
    uid_a = await _make_user(ep_session, tid_a)

    t_b = Tenant(slug=f"ep-b2-{uuid.uuid4().hex[:6]}", nombre="Tenant B2", activo=True)
    ep_session.add(t_b)
    await ep_session.flush()
    await ep_session.refresh(t_b)

    c_b = Carrera(tenant_id=t_b.id, codigo="B_PRIV", nombre="Privada de B")
    ep_session.add(c_b)
    await ep_session.flush()
    await ep_session.refresh(c_b)
    await ep_session.commit()

    app = _build_estructura_app(ep_engine, uid_a, tid_a)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/admin/carreras/{c_b.id}")

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_9_6_patch_carrera_updates_estado(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.6 PATCH /api/admin/carreras/{id} → updates estado, returns 200."""
    from app.models.carrera import Carrera  # noqa: PLC0415

    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"ADMIN_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "estructura:gestionar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)

    carrera = Carrera(tenant_id=tid, codigo="PATCH_ME", nombre="Carrera a Parchear")
    ep_session.add(carrera)
    await ep_session.flush()
    await ep_session.refresh(carrera)
    await ep_session.commit()

    app = _build_estructura_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            f"/api/admin/carreras/{carrera.id}",
            json={"estado": "Inactiva"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert resp.json()["estado"] == "Inactiva"


@pytest.mark.asyncio
async def test_9_7_delete_carrera_returns_204_and_not_in_list(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.7 DELETE /api/admin/carreras/{id} → 204, carrera not in subsequent GET."""
    from app.models.carrera import Carrera  # noqa: PLC0415

    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"ADMIN_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "estructura:gestionar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)

    carrera = Carrera(tenant_id=tid, codigo="DEL_ME", nombre="Carrera a Borrar")
    ep_session.add(carrera)
    await ep_session.flush()
    await ep_session.refresh(carrera)
    await ep_session.commit()

    app = _build_estructura_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        del_resp = await client.delete(f"/api/admin/carreras/{carrera.id}")
        assert del_resp.status_code == 204, f"Expected 204, got {del_resp.status_code}"

        list_resp = await client.get("/api/admin/carreras/")
        assert list_resp.status_code == 200
        codigos = [c["codigo"] for c in list_resp.json()]
        assert "DEL_ME" not in codigos


@pytest.mark.asyncio
async def test_9_8_post_cohortes_with_inactive_carrera_returns_422(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.8 POST /api/admin/cohortes with inactive carrera → 422."""
    from app.models.carrera import Carrera  # noqa: PLC0415

    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"ADMIN_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "estructura:gestionar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)

    carrera = Carrera(tenant_id=tid, codigo="INACT_C", nombre="Carrera Inactiva", estado="Inactiva")
    ep_session.add(carrera)
    await ep_session.flush()
    await ep_session.refresh(carrera)
    await ep_session.commit()

    app = _build_estructura_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/admin/cohortes/",
            json={
                "carrera_id": str(carrera.id),
                "nombre": "2024-1",
                "anio": 2024,
                "vig_desde": "2024-03-01",
            },
        )

    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"


@pytest.mark.asyncio
async def test_9_9_post_cohortes_with_active_carrera_returns_201(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.9 POST /api/admin/cohortes with active carrera → 201."""
    from app.models.carrera import Carrera  # noqa: PLC0415

    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"ADMIN_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "estructura:gestionar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)

    carrera = Carrera(tenant_id=tid, codigo="ACT_C", nombre="Carrera Activa", estado="Activa")
    ep_session.add(carrera)
    await ep_session.flush()
    await ep_session.refresh(carrera)
    await ep_session.commit()

    app = _build_estructura_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/admin/cohortes/",
            json={
                "carrera_id": str(carrera.id),
                "nombre": "2024-1",
                "anio": 2024,
                "vig_desde": "2024-03-01",
            },
        )

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["nombre"] == "2024-1"
    assert body["carrera_id"] == str(carrera.id)


@pytest.mark.asyncio
async def test_9_10_get_cohortes_returns_only_current_tenant(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.10 GET /api/admin/cohortes returns only current tenant's cohortes."""
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.models.cohorte import Cohorte  # noqa: PLC0415
    from app.models.tenant import Tenant  # noqa: PLC0415

    tid_a = await _make_tenant(ep_session)
    uid_a = await _make_user(ep_session, tid_a)

    t_b = Tenant(slug=f"ep-coh-b-{uuid.uuid4().hex[:6]}", nombre="Coh Tenant B", activo=True)
    ep_session.add(t_b)
    await ep_session.flush()
    await ep_session.refresh(t_b)
    tid_b = t_b.id

    c_a = Carrera(tenant_id=tid_a, codigo="C_COH_A", nombre="Carrera A para Cohorte")
    c_b = Carrera(tenant_id=tid_b, codigo="C_COH_B", nombre="Carrera B para Cohorte")
    ep_session.add_all([c_a, c_b])
    await ep_session.flush()
    await ep_session.refresh(c_a)
    await ep_session.refresh(c_b)

    coh_a = Cohorte(
        tenant_id=tid_a, carrera_id=c_a.id,
        nombre="COH_A_ONLY", anio=2024, vig_desde=date(2024, 3, 1),
    )
    coh_b = Cohorte(
        tenant_id=tid_b, carrera_id=c_b.id,
        nombre="COH_B_ONLY", anio=2024, vig_desde=date(2024, 3, 1),
    )
    ep_session.add_all([coh_a, coh_b])
    await ep_session.flush()
    await ep_session.commit()

    app = _build_estructura_app(ep_engine, uid_a, tid_a)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/admin/cohortes/")

    assert resp.status_code == 200
    nombres = [c["nombre"] for c in resp.json()]
    assert "COH_A_ONLY" in nombres
    assert "COH_B_ONLY" not in nombres


@pytest.mark.asyncio
async def test_9_11_post_materias_with_admin_returns_201(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.11 POST /api/admin/materias with valid ADMIN → 201."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"ADMIN_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "estructura:gestionar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)
    await ep_session.commit()

    app = _build_estructura_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/admin/materias/",
            json={"codigo": "MAT101", "nombre": "Matemática I"},
        )

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["codigo"] == "MAT101"
    assert body["estado"] == "Activa"


@pytest.mark.asyncio
async def test_9_12_get_materias_returns_only_current_tenant(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.12 GET /api/admin/materias returns only current tenant's materias."""
    from app.models.materia import Materia  # noqa: PLC0415
    from app.models.tenant import Tenant  # noqa: PLC0415

    tid_a = await _make_tenant(ep_session)
    uid_a = await _make_user(ep_session, tid_a)

    t_b = Tenant(slug=f"ep-mat-b-{uuid.uuid4().hex[:6]}", nombre="Mat Tenant B", activo=True)
    ep_session.add(t_b)
    await ep_session.flush()
    await ep_session.refresh(t_b)
    tid_b = t_b.id

    m_a = Materia(tenant_id=tid_a, codigo="MAT_A_ONLY", nombre="Materia de A")
    m_b = Materia(tenant_id=tid_b, codigo="MAT_B_ONLY", nombre="Materia de B")
    ep_session.add_all([m_a, m_b])
    await ep_session.flush()
    await ep_session.commit()

    app = _build_estructura_app(ep_engine, uid_a, tid_a)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/admin/materias/")

    assert resp.status_code == 200
    codigos = [m["codigo"] for m in resp.json()]
    assert "MAT_A_ONLY" in codigos
    assert "MAT_B_ONLY" not in codigos


@pytest.mark.asyncio
async def test_9_13_post_materias_dup_codigo_returns_409(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """9.13 POST /api/admin/materias with dup codigo → 409."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"ADMIN_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "estructura:gestionar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)
    await ep_session.commit()

    app = _build_estructura_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First create
        resp1 = await client.post(
            "/api/admin/materias/",
            json={"codigo": "DUP", "nombre": "Materia Original"},
        )
        assert resp1.status_code == 201

        # Duplicate
        resp2 = await client.post(
            "/api/admin/materias/",
            json={"codigo": "DUP", "nombre": "Materia Duplicada"},
        )
        assert resp2.status_code == 409, f"Expected 409, got {resp2.status_code}: {resp2.text}"

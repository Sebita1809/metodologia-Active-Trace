"""
tests/test_usuarios_endpoints.py — Integration tests for Usuario and Asignacion API.

Group 10 tests (tasks 10.1–10.14): full HTTP integration tests for
  /api/admin/usuarios
  /api/asignaciones

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
    reason="TEST_DATABASE_URL not set — skipping usuario endpoint tests",
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


async def _make_domain_usuario(
    session: AsyncSession, tid: uuid.UUID, email: str = None
) -> uuid.UUID:
    """Create a domain Usuario (not auth User) for FK references."""
    from app.models.usuario import Usuario  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    if email is None:
        email = f"usr_{uuid.uuid4().hex[:8]}@example.com"
    u = Usuario(
        tenant_id=tid,
        nombre="Test",
        apellidos="User",
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


# ---------------------------------------------------------------------------
# App builders
# ---------------------------------------------------------------------------

def _build_usuarios_app(engine: AsyncEngine, uid: uuid.UUID, tid: uuid.UUID) -> FastAPI:
    """Build FastAPI app with usuarios and asignaciones routers + dependency overrides.

    Overrides get_current_user and get_db globally, and also overrides the
    _get_svc factory in the usuarios router to inject the TEST_KEY crypto service.
    """
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.core.dependencies import get_current_user, get_db  # noqa: PLC0415
    from app.api.v1.routers.usuarios import router as usuarios_router  # noqa: PLC0415
    from app.api.v1.routers.asignaciones import router as asignaciones_router  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.services.usuario_service import UsuarioService  # noqa: PLC0415
    from app.api.v1.routers import usuarios as usuarios_module  # noqa: PLC0415

    app = FastAPI()

    def mock_user() -> CurrentUser:
        return CurrentUser(user_id=uid, tenant_id=tid, roles=[])

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def mock_db():
        async with factory() as session:
            yield session

    # Override global auth + db dependencies
    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_db] = mock_db

    # Override _get_svc in usuarios router to inject TEST_KEY crypto service.
    # Since get_db is already overridden and yields from mock_db, we use it again here
    # to get a consistent session from the same factory.
    from fastapi import Depends as _Depends  # noqa: PLC0415

    def mock_usuario_svc(
        session: AsyncSession = _Depends(mock_db),
    ) -> UsuarioService:
        crypto = CryptoService(_TEST_KEY)
        return UsuarioService(
            session=session,
            tenant_id=tid,
            crypto=crypto,
        )

    app.dependency_overrides[usuarios_module._get_svc] = mock_usuario_svc

    app.include_router(usuarios_router, prefix="/api/admin/usuarios", tags=["usuarios"])
    app.include_router(asignaciones_router, prefix="/api/asignaciones", tags=["asignaciones"])
    return app


def _build_no_auth_app(engine: AsyncEngine) -> FastAPI:
    """Build app WITHOUT overriding get_current_user — real 401 check fires."""
    from app.core.dependencies import get_db  # noqa: PLC0415
    from app.api.v1.routers.usuarios import router as usuarios_router  # noqa: PLC0415

    app = FastAPI()
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def mock_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = mock_db
    app.include_router(usuarios_router, prefix="/api/admin/usuarios", tags=["usuarios"])
    return app


# ---------------------------------------------------------------------------
# Group 10: Endpoint integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_10_1_post_usuarios_without_token_returns_401(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.1 POST /api/admin/usuarios without token → 401."""
    app = _build_no_auth_app(ep_engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/admin/usuarios/",
            json={"nombre": "Test", "apellidos": "User", "email": "test@example.com"},
        )

    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


@pytest.mark.asyncio
async def test_10_2_post_usuarios_without_permission_returns_403(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.2 POST /api/admin/usuarios without usuarios:gestionar → 403."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    await ep_session.commit()

    app = _build_usuarios_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/admin/usuarios/",
            json={"nombre": "Test", "apellidos": "User", "email": "test@example.com"},
        )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_10_3_post_usuarios_with_admin_returns_201_no_email_hash(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.3 POST /api/admin/usuarios with ADMIN → 201; PII decrypted; no email_hash."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"ADMIN_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "usuarios:gestionar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)
    await ep_session.commit()

    app = _build_usuarios_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/admin/usuarios/",
            json={
                "nombre": "María",
                "apellidos": "García",
                "email": "maria@example.com",
            },
        )

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["nombre"] == "María"
    assert body["apellidos"] == "García"
    assert body["email"] == "maria@example.com"
    assert "email_hash" not in body
    assert "id" in body
    assert body["tenant_id"] == str(tid)


@pytest.mark.asyncio
async def test_10_4_get_usuarios_returns_only_current_tenant(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.4 GET /api/admin/usuarios returns only usuarios from JWT tenant."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    tid_a = await _make_tenant(ep_session)
    uid_a = await _make_user(ep_session, tid_a)

    t_b = Tenant(slug=f"ep-b-{uuid.uuid4().hex[:6]}", nombre="Tenant B", activo=True)
    ep_session.add(t_b)
    await ep_session.flush()
    await ep_session.refresh(t_b)
    tid_b = t_b.id

    # Create usuarios in both tenants directly
    await _make_domain_usuario(ep_session, tid_a, "user_a@example.com")
    await _make_domain_usuario(ep_session, tid_b, "user_b@example.com")
    await ep_session.commit()

    app = _build_usuarios_app(ep_engine, uid_a, tid_a)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/admin/usuarios/")

    assert resp.status_code == 200
    # All returned emails should belong to tenant A (when decrypted they'd be user_a@example.com)
    # We check tenant_id field directly
    tenants_seen = {item["tenant_id"] for item in resp.json()}
    assert tenants_seen == {str(tid_a)}


@pytest.mark.asyncio
async def test_10_5_get_usuario_from_other_tenant_returns_404(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.5 GET /api/admin/usuarios/{id} with ID from another tenant → 404."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    tid_a = await _make_tenant(ep_session)
    uid_a = await _make_user(ep_session, tid_a)

    t_b = Tenant(slug=f"ep-b2-{uuid.uuid4().hex[:6]}", nombre="Tenant B2", activo=True)
    ep_session.add(t_b)
    await ep_session.flush()
    await ep_session.refresh(t_b)

    # Create a usuario in tenant B
    usuario_b_id = await _make_domain_usuario(ep_session, t_b.id, "b_user@example.com")
    await ep_session.commit()

    app = _build_usuarios_app(ep_engine, uid_a, tid_a)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/admin/usuarios/{usuario_b_id}")

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_10_6_patch_usuario_updates_estado(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.6 PATCH /api/admin/usuarios/{id} → updates estado, returns 200."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"ADMIN_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "usuarios:gestionar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)

    usuario_id = await _make_domain_usuario(ep_session, tid, "patch@example.com")
    await ep_session.commit()

    app = _build_usuarios_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            f"/api/admin/usuarios/{usuario_id}",
            json={"estado": "Inactivo"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert resp.json()["estado"] == "Inactivo"


@pytest.mark.asyncio
async def test_10_7_delete_usuario_returns_204_and_not_in_get(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.7 DELETE /api/admin/usuarios/{id} → 204; usuario not in subsequent GET."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"ADMIN_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "usuarios:gestionar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)

    usuario_id = await _make_domain_usuario(ep_session, tid, "del@example.com")
    await ep_session.commit()

    app = _build_usuarios_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        del_resp = await client.delete(f"/api/admin/usuarios/{usuario_id}")
        assert del_resp.status_code == 204, f"Expected 204, got {del_resp.status_code}"

        list_resp = await client.get("/api/admin/usuarios/")
        assert list_resp.status_code == 200
        ids = [item["id"] for item in list_resp.json()]
        assert str(usuario_id) not in ids


@pytest.mark.asyncio
async def test_10_8_post_usuarios_dup_email_same_tenant_returns_409(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.8 POST /api/admin/usuarios with duplicate email in same tenant → 409."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"ADMIN_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "usuarios:gestionar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)
    await ep_session.commit()

    app = _build_usuarios_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp1 = await client.post(
            "/api/admin/usuarios/",
            json={"nombre": "First", "apellidos": "User", "email": "dup@example.com"},
        )
        assert resp1.status_code == 201

        resp2 = await client.post(
            "/api/admin/usuarios/",
            json={"nombre": "Second", "apellidos": "User", "email": "dup@example.com"},
        )
        assert resp2.status_code == 409, f"Expected 409, got {resp2.status_code}: {resp2.text}"


@pytest.mark.asyncio
async def test_10_9_post_asignaciones_without_token_returns_401(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.9 POST /api/asignaciones without token → 401."""
    from app.core.dependencies import get_db  # noqa: PLC0415
    from app.api.v1.routers.asignaciones import router as asignaciones_router  # noqa: PLC0415

    app_no_auth = FastAPI()
    factory = async_sessionmaker(ep_engine, expire_on_commit=False)

    async def mock_db():
        async with factory() as session:
            yield session

    app_no_auth.dependency_overrides[get_db] = mock_db
    app_no_auth.include_router(asignaciones_router, prefix="/api/asignaciones")

    transport = ASGITransport(app=app_no_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/asignaciones/",
            json={
                "usuario_id": str(uuid.uuid4()),
                "rol": "PROFESOR",
                "desde": str(date.today()),
            },
        )

    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


@pytest.mark.asyncio
async def test_10_10_post_asignaciones_without_permission_returns_403(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.10 POST /api/asignaciones without equipos:asignar → 403."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    await ep_session.commit()

    app = _build_usuarios_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/asignaciones/",
            json={
                "usuario_id": str(uuid.uuid4()),
                "rol": "PROFESOR",
                "desde": str(date.today()),
            },
        )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_10_11_post_asignaciones_with_coordinador_returns_201_with_estado_vigencia(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.11 POST /api/asignaciones with COORDINADOR → 201; estado_vigencia in response."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"COORD_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "equipos:asignar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)

    usuario_id = await _make_domain_usuario(ep_session, tid, "coord_asig@example.com")
    await ep_session.commit()

    today = date.today()
    app = _build_usuarios_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/asignaciones/",
            json={
                "usuario_id": str(usuario_id),
                "rol": "TUTOR",
                "desde": str(today - timedelta(days=5)),
                "hasta": str(today + timedelta(days=60)),
            },
        )

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "estado_vigencia" in body
    assert body["estado_vigencia"] == "Vigente"


@pytest.mark.asyncio
async def test_10_12_get_asignaciones_filters_by_materia_id(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.12 GET /api/asignaciones?materia_id=... filters correctly."""
    from app.models.materia import Materia  # noqa: PLC0415

    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"COORD_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "equipos:asignar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)

    # Create two materias
    m1 = Materia(tenant_id=tid, codigo="MAT_FILTER_A", nombre="Materia A")
    m2 = Materia(tenant_id=tid, codigo="MAT_FILTER_B", nombre="Materia B")
    ep_session.add_all([m1, m2])
    await ep_session.flush()
    await ep_session.refresh(m1)
    await ep_session.refresh(m2)

    usuario_id = await _make_domain_usuario(ep_session, tid, "filter@example.com")
    await ep_session.commit()

    today = date.today()
    app = _build_usuarios_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create asignacion for materia 1
        r1 = await client.post(
            "/api/asignaciones/",
            json={
                "usuario_id": str(usuario_id),
                "rol": "PROFESOR",
                "desde": str(today),
                "materia_id": str(m1.id),
            },
        )
        assert r1.status_code == 201

        # Create asignacion for materia 2
        r2 = await client.post(
            "/api/asignaciones/",
            json={
                "usuario_id": str(usuario_id),
                "rol": "TUTOR",
                "desde": str(today),
                "materia_id": str(m2.id),
            },
        )
        assert r2.status_code == 201

        # Filter by materia 1 only
        resp = await client.get(f"/api/asignaciones/?materia_id={m1.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["materia_id"] == str(m1.id)


@pytest.mark.asyncio
async def test_10_13_get_asignaciones_filters_by_responsable_id(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.13 GET /api/asignaciones?responsable_id=... filters correctly."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"COORD_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "equipos:asignar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)

    # Two domain usuarios
    resp_id = await _make_domain_usuario(ep_session, tid, "resp@example.com")
    docente_id = await _make_domain_usuario(ep_session, tid, "docente@example.com")
    await ep_session.commit()

    today = date.today()
    app = _build_usuarios_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Asignacion WITH responsable
        r1 = await client.post(
            "/api/asignaciones/",
            json={
                "usuario_id": str(docente_id),
                "rol": "TUTOR",
                "desde": str(today),
                "responsable_id": str(resp_id),
            },
        )
        assert r1.status_code == 201

        # Asignacion WITHOUT responsable
        r2 = await client.post(
            "/api/asignaciones/",
            json={
                "usuario_id": str(docente_id),
                "rol": "PROFESOR",
                "desde": str(today),
            },
        )
        assert r2.status_code == 201

        # Filter by responsable_id
        resp = await client.get(f"/api/asignaciones/?responsable_id={resp_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["responsable_id"] == str(resp_id)


@pytest.mark.asyncio
async def test_10_14_get_asignaciones_returns_only_current_tenant(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """10.14 GET /api/asignaciones returns only asignaciones from JWT tenant."""
    from app.models.tenant import Tenant  # noqa: PLC0415
    from app.models.asignacion import Asignacion  # noqa: PLC0415

    tid_a = await _make_tenant(ep_session)
    uid_a = await _make_user(ep_session, tid_a)

    t_b = Tenant(slug=f"ep-asig-b-{uuid.uuid4().hex[:6]}", nombre="Asig Tenant B", activo=True)
    ep_session.add(t_b)
    await ep_session.flush()
    await ep_session.refresh(t_b)
    tid_b = t_b.id

    # Create domain usuarios in each tenant
    usr_a_id = await _make_domain_usuario(ep_session, tid_a, "a@example.com")
    usr_b_id = await _make_domain_usuario(ep_session, tid_b, "b@example.com")

    # Create raw asignaciones in both tenants
    today = date.today()
    asig_a = Asignacion(
        tenant_id=tid_a,
        usuario_id=usr_a_id,
        rol="PROFESOR",
        desde=today,
        comisiones=[],
    )
    asig_b = Asignacion(
        tenant_id=tid_b,
        usuario_id=usr_b_id,
        rol="TUTOR",
        desde=today,
        comisiones=[],
    )
    ep_session.add_all([asig_a, asig_b])
    await ep_session.flush()
    await ep_session.refresh(asig_a)
    await ep_session.refresh(asig_b)
    await ep_session.commit()

    app = _build_usuarios_app(ep_engine, uid_a, tid_a)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/asignaciones/")

    assert resp.status_code == 200
    body = resp.json()
    tenant_ids = {item["tenant_id"] for item in body}
    assert tenant_ids == {str(tid_a)}
    ids_in_response = {item["id"] for item in body}
    assert str(asig_b.id) not in ids_in_response


# ---------------------------------------------------------------------------
# Group 11: Empty-string normalization in PATCH
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_11_1_patch_with_empty_cbu_does_not_clear_field(
    ep_engine: AsyncEngine,
    ep_session: AsyncSession,
):
    """11.1 PATCH /api/admin/usuarios/{id} with cbu='' → cbu unchanged in response."""
    tid = await _make_tenant(ep_session)
    uid = await _make_user(ep_session, tid)
    rol_id = await _make_rol(ep_session, tid, f"ADMIN_{uuid.uuid4().hex[:6]}")
    perm_id = await _make_permiso(ep_session, tid, "usuarios:gestionar")
    await _assign_perm(ep_session, tid, rol_id, perm_id)
    await _assign_rol(ep_session, tid, uid, rol_id)

    # Create usuario with a CBU value
    from app.models.usuario import Usuario  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415

    crypto = CryptoService(_TEST_KEY)
    email = f"cbu_patch_{uuid.uuid4().hex[:8]}@example.com"
    usuario = Usuario(
        tenant_id=tid,
        nombre="CbuPatch",
        apellidos="Test",
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
        cbu=crypto.encrypt("0000003100087654321001"),
    )
    ep_session.add(usuario)
    await ep_session.flush()
    await ep_session.refresh(usuario)
    usuario_id = usuario.id
    await ep_session.commit()

    # The response decrypted CBU should be the original value
    expected_cbu = "0000003100087654321001"

    app = _build_usuarios_app(ep_engine, uid, tid)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get the user first to confirm CBU
        get_resp = await client.get(f"/api/admin/usuarios/{usuario_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["cbu"] == expected_cbu

        # PATCH with empty string CBU
        patch_resp = await client.patch(
            f"/api/admin/usuarios/{usuario_id}",
            json={"cbu": "", "nombre": "Updated"},
        )

    assert patch_resp.status_code == 200, f"Expected 200, got {patch_resp.status_code}: {patch_resp.text}"
    body = patch_resp.json()
    assert body["nombre"] == "Updated"
    assert body["cbu"] == expected_cbu, f"CBU should remain '{expected_cbu}', got '{body['cbu']}'"

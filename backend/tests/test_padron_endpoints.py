"""
tests/test_padron_endpoints.py — Integration HTTP tests for padron endpoints.

Tasks covered:
  5.5 — sync_moodle creates active version with origen="moodle" and audits
  5.6 — Moodle failure after retries → 502, NO active version created
  8.3 — user without padron:* permissions receives 403 (fail-closed)
  9.1 — E2E: preview → confirmar → ver returns loaded padrón; re-confirm deactivates previous
  9.2 — E2E: tenant isolation at endpoints (T1 does NOT see T2 padrón)
  9.3 — E2E: sync-moodle OK creates version; Moodle failure → 502

Requires TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import csv
import io
import os
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import sqlalchemy as sa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping padron endpoint tests",
)

_TEST_KEY = "a" * 64
NOW = datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def ep_engine() -> AsyncEngine:
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
    t = Tenant(slug=f"ep-{uuid.uuid4().hex[:8]}{suffix}", nombre="EP Test", activo=True)
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
    from app.models.usuario import Usuario  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415
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
    from app.models.rol_permiso import RolPermiso, AlcanceEnum  # noqa: PLC0415
    rp = RolPermiso(
        tenant_id=tid, rol_id=rol_id, permiso_id=perm_id,
        alcance=AlcanceEnum.global_ if alcance == "global" else AlcanceEnum.propio,
    )
    session.add(rp)
    await session.flush()


async def _assign_rol(session, tid, uid, rol_id):
    from app.models.usuario_rol import UsuarioRol  # noqa: PLC0415
    from datetime import timedelta  # noqa: PLC0415
    ur = UsuarioRol(tenant_id=tid, user_id=uid, rol_id=rol_id, vigente_desde=NOW - timedelta(hours=1))
    session.add(ur)
    await session.flush()


async def _make_materia(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(tenant_id=tid, codigo=f"MAT_{uuid.uuid4().hex[:6]}", nombre="Mat EP")
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


async def _make_cohorte(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.models.cohorte import Cohorte  # noqa: PLC0415
    c = Carrera(tenant_id=tid, codigo=f"CAR_{uuid.uuid4().hex[:6]}", nombre="Car EP")
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


def _build_csv(rows: list[dict]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["nombre", "apellidos", "email", "comision", "regional"])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def _build_padron_app(engine: AsyncEngine, uid: uuid.UUID, tid: uuid.UUID) -> FastAPI:
    """FastAPI app with padron router and mocked auth dependencies."""
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.core.dependencies import get_current_user, get_db  # noqa: PLC0415
    from app.api.v1.routers.padron import router as padron_router  # noqa: PLC0415

    app = FastAPI()

    def mock_user() -> CurrentUser:
        return CurrentUser(user_id=uid, tenant_id=tid, roles=[])

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def mock_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_db] = mock_db

    app.include_router(padron_router, prefix="/api/padron", tags=["padron"])
    return app


async def _setup_user_with_padron_cargar_perm(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    """Create auth user + rol + padron:cargar/ver/vaciar perms, return user id."""
    uid = await _make_auth_user(session, tid)
    rol_id = await _make_rol(session, tid, f"PROF_{uuid.uuid4().hex[:6]}")
    for clave in ["padron:cargar", "padron:ver", "padron:vaciar"]:
        perm_id = await _make_permiso(session, tid, clave)
        await _assign_perm(session, tid, rol_id, perm_id, alcance="global")
    await _assign_rol(session, tid, uid, rol_id)
    await session.commit()
    return uid


# ---------------------------------------------------------------------------
# Task 8.3 — fail-closed: 403 without permission
# ---------------------------------------------------------------------------

async def test_padron_cargar_403_without_permission(ep_session: AsyncSession, ep_engine: AsyncEngine):
    """Endpoint returns 403 for user without padron:cargar permission."""
    tid = await _make_tenant(ep_session)
    uid = await _make_auth_user(ep_session, tid)
    await ep_session.commit()

    # No role/permission assigned
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.core.dependencies import get_current_user, get_db  # noqa: PLC0415
    from app.api.v1.routers.padron import router as padron_router  # noqa: PLC0415

    app = FastAPI()
    factory = async_sessionmaker(ep_engine, expire_on_commit=False)

    def mock_user():
        return CurrentUser(user_id=uid, tenant_id=tid, roles=[])

    async def mock_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_db] = mock_db
    app.include_router(padron_router, prefix="/api/padron", tags=["padron"])

    csv_data = _build_csv([{"nombre": "A", "apellidos": "B", "email": "a@b.com", "comision": "", "regional": ""}])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/padron/preview",
            files={"file": ("test.csv", csv_data, "text/csv")},
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Task 9.1 — E2E: preview → confirmar → ver; re-confirm deactivates previous
# ---------------------------------------------------------------------------

async def test_e2e_preview_confirmar_ver(ep_session: AsyncSession, ep_engine: AsyncEngine):
    """E2E: preview → confirmar → GET returns the loaded padrón entries."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_padron_cargar_perm(ep_session, tid)
    du_id = await _make_domain_usuario(ep_session, tid)
    materia_id = await _make_materia(ep_session, tid)
    cohorte_id = await _make_cohorte(ep_session, tid)
    await ep_session.commit()

    app = _build_padron_app(ep_engine, uid, tid)
    csv_data = _build_csv([
        {"nombre": "Ana", "apellidos": "García", "email": "ana@test.com", "comision": "A1", "regional": "Norte"}
    ])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Preview — nothing should be in DB yet
        prev_resp = await ac.post(
            "/api/padron/preview",
            files={"file": ("test.csv", csv_data, "text/csv")},
        )
        assert prev_resp.status_code == 200, prev_resp.text
        prev_data = prev_resp.json()
        assert len(prev_data["entradas"]) == 1

        # Confirmar
        conf_resp = await ac.post(
            "/api/padron/confirmar",
            files={"file": ("test.csv", csv_data, "text/csv")},
            data={"materia_id": str(materia_id), "cohorte_id": str(cohorte_id)},
        )
        assert conf_resp.status_code == 201, conf_resp.text
        conf_data = conf_resp.json()
        v1_id = conf_data["version"]["id"]
        assert conf_data["entradas_cargadas"] == 1

        # GET — should return the active padrón
        get_resp = await ac.get(
            "/api/padron/",
            params={"materia_id": str(materia_id), "cohorte_id": str(cohorte_id)},
        )
        assert get_resp.status_code == 200, get_resp.text
        entries = get_resp.json()
        assert len(entries) == 1
        assert entries[0]["nombre"] == "Ana"
        assert entries[0]["email"] == "ana@test.com"  # decrypted

        # Re-confirmar — previous version should be deactivated
        conf_resp2 = await ac.post(
            "/api/padron/confirmar",
            files={"file": ("test.csv", csv_data, "text/csv")},
            data={"materia_id": str(materia_id), "cohorte_id": str(cohorte_id)},
        )
        assert conf_resp2.status_code == 201, conf_resp2.text
        conf_data2 = conf_resp2.json()
        v2_id = conf_data2["version"]["id"]
        assert v1_id != v2_id

        # Version history should have 2 entries
        ver_resp = await ac.get(
            "/api/padron/versiones",
            params={"materia_id": str(materia_id), "cohorte_id": str(cohorte_id)},
        )
        assert ver_resp.status_code == 200, ver_resp.text
        versions = ver_resp.json()
        assert len(versions) == 2
        # First (newest) should be active
        assert versions[0]["activa"] is True
        assert versions[0]["id"] == v2_id
        # Second should be inactive
        assert versions[1]["activa"] is False
        assert versions[1]["id"] == v1_id


# ---------------------------------------------------------------------------
# Task 9.2 — E2E: tenant isolation
# ---------------------------------------------------------------------------

async def test_e2e_tenant_isolation(ep_session: AsyncSession, ep_engine: AsyncEngine):
    """T1 cannot see T2's padrón via the endpoints."""
    tid1 = await _make_tenant(ep_session, "-t1")
    tid2 = await _make_tenant(ep_session, "-t2")

    uid1 = await _setup_user_with_padron_cargar_perm(ep_session, tid1)
    uid2 = await _setup_user_with_padron_cargar_perm(ep_session, tid2)

    materia1 = await _make_materia(ep_session, tid1)
    cohorte1 = await _make_cohorte(ep_session, tid1)
    materia2 = await _make_materia(ep_session, tid2)
    cohorte2 = await _make_cohorte(ep_session, tid2)
    await ep_session.commit()

    csv_data = _build_csv([
        {"nombre": "T2", "apellidos": "User", "email": "t2@secret.com", "comision": "", "regional": ""}
    ])

    # T2 uploads padrón
    app_t2 = _build_padron_app(ep_engine, uid2, tid2)
    async with AsyncClient(transport=ASGITransport(app=app_t2), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/padron/confirmar",
            files={"file": ("test.csv", csv_data, "text/csv")},
            data={"materia_id": str(materia2), "cohorte_id": str(cohorte2)},
        )
        assert resp.status_code == 201, resp.text

    # T1 tries to see T2's padrón — should get empty list (not T2 data)
    app_t1 = _build_padron_app(ep_engine, uid1, tid1)
    async with AsyncClient(transport=ASGITransport(app=app_t1), base_url="http://test") as ac:
        resp = await ac.get(
            "/api/padron/",
            params={"materia_id": str(materia2), "cohorte_id": str(cohorte2)},
        )
        # Either 200 with empty list or just empty
        assert resp.status_code == 200
        entries = resp.json()
        # T1 must not see any T2 entries (tenant isolation)
        for e in entries:
            assert "secret.com" not in e.get("email", "")


# ---------------------------------------------------------------------------
# Task 9.3 — E2E: sync-moodle OK creates version; failure → 502
# ---------------------------------------------------------------------------

async def test_e2e_sync_moodle_ok(ep_session: AsyncSession, ep_engine: AsyncEngine):
    """sync-moodle endpoint creates a version when Moodle WS succeeds."""
    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_padron_cargar_perm(ep_session, tid)
    materia_id = await _make_materia(ep_session, tid)
    cohorte_id = await _make_cohorte(ep_session, tid)
    await ep_session.commit()

    moodle_users = [
        {"firstname": "Moodle", "lastname": "User", "email": "moodle@lms.com"}
    ]

    app = _build_padron_app(ep_engine, uid, tid)

    with patch("app.api.v1.routers.padron.MoodleWSClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.fetch_padron = AsyncMock(return_value=[
            __import__("app.integrations.moodle_ws", fromlist=["EntradaCruda"]).EntradaCruda(
                nombre="Moodle", apellidos="User", email="moodle@lms.com"
            )
        ])
        mock_cls.return_value = mock_instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/padron/sync-moodle",
                json={
                    "materia_id": str(materia_id),
                    "cohorte_id": str(cohorte_id),
                    "curso_ref": "COURSE_001",
                },
            )

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["version"]["origen"] == "moodle"
    assert data["entradas_cargadas"] == 1


async def test_e2e_sync_moodle_failure_returns_502(ep_session: AsyncSession, ep_engine: AsyncEngine):
    """sync-moodle returns 502 when Moodle WS fails; no version is created."""
    from app.integrations.moodle_ws import MoodleIntegrationError  # noqa: PLC0415
    from app.models.version_padron import VersionPadron  # noqa: PLC0415

    tid = await _make_tenant(ep_session)
    uid = await _setup_user_with_padron_cargar_perm(ep_session, tid)
    materia_id = await _make_materia(ep_session, tid)
    cohorte_id = await _make_cohorte(ep_session, tid)
    await ep_session.commit()

    app = _build_padron_app(ep_engine, uid, tid)

    with patch("app.api.v1.routers.padron.MoodleWSClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.fetch_padron = AsyncMock(
            side_effect=MoodleIntegrationError("LMS down")
        )
        mock_cls.return_value = mock_instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/padron/sync-moodle",
                json={
                    "materia_id": str(materia_id),
                    "cohorte_id": str(cohorte_id),
                    "curso_ref": "BAD_COURSE",
                },
            )

    assert resp.status_code == 502
    # Verify no partial version was created
    async with async_sessionmaker(ep_engine, expire_on_commit=False)() as session:
        count = await session.scalar(
            sa.select(sa.func.count()).select_from(VersionPadron)
            .where(VersionPadron.tenant_id == tid)
        )
    assert count == 0, "No version should be created when Moodle fails"

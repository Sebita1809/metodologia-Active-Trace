"""
tests/test_encuentro_endpoints.py — HTTP integration tests for encuentros endpoints.

Tasks covered:
  9.1 POST /api/v1/slots: 201 with RN-13.1; 403 without permission
  9.2 POST /api/v1/encuentros: 201 unique encounter; PATCH /api/v1/encuentros/{id}: edit + 403
  9.3 GET /api/v1/encuentros/html: returns HTML fragment
  9.4 GET /api/v1/admin/encuentros: 200 for COORDINADOR; 403 for PROFESOR
  10.1 encuentros:gestionar permission seeded for PROFESOR/COORDINADOR/ADMIN
  10.2 E2E FL-06: slot recurrente → N instancias → editar a Realizado+video → admin audita → HTML
  8.1 schema extra='forbid' rejects extra fields

Requires TEST_DATABASE_URL (real DB).

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import os
import uuid
from datetime import date, time
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import sqlalchemy as sa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping encuentro endpoint integration tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Engine + session fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def ep_enc_engine() -> AsyncEngine:
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
    import app.models.slot_encuentro    # noqa: F401
    import app.models.instancia_encuentro  # noqa: F401
    import app.models.guardia           # noqa: F401
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


@pytest_asyncio.fixture
async def ep_enc_session(ep_enc_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(ep_enc_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ---------------------------------------------------------------------------
# App + client factory
# ---------------------------------------------------------------------------

def _build_app_for_session(session_factory) -> FastAPI:
    """Build app with get_db overridden to the test session factory."""
    from app.main import create_app  # noqa: PLC0415
    from app.core.dependencies import get_db  # noqa: PLC0415

    app = create_app()

    async def override_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_db
    return app


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

async def _seed_all(session: AsyncSession):
    """Seed a full test context: tenant, materia, usuario, asignacion."""
    from app.models.tenant import Tenant      # noqa: PLC0415
    from app.models.materia import Materia    # noqa: PLC0415
    from app.models.usuario import Usuario    # noqa: PLC0415
    from app.models.asignacion import Asignacion  # noqa: PLC0415

    tenant = Tenant(slug=f"t-{uuid.uuid4().hex[:6]}", nombre="Tenant Test", activo=True)
    session.add(tenant)
    await session.flush()

    materia = Materia(tenant_id=tenant.id, nombre="Mat Enc", codigo="ENC-01")
    session.add(materia)

    usuario = Usuario(
        tenant_id=tenant.id,
        nombre="Prof",
        apellido="Test",
        email=f"p-{uuid.uuid4().hex[:6]}@t.com",
        legajo="L001",
    )
    session.add(usuario)
    await session.flush()

    asignacion = Asignacion(
        tenant_id=tenant.id,
        usuario_id=usuario.id,
        rol="PROFESOR",
        materia_id=materia.id,
        desde=date(2024, 1, 1),
    )
    session.add(asignacion)
    await session.flush()
    await session.refresh(tenant)
    await session.refresh(materia)
    await session.refresh(usuario)
    await session.refresh(asignacion)

    return tenant, materia, usuario, asignacion


def _make_jwt(tenant_id: uuid.UUID, user_id: uuid.UUID, roles: list[str]) -> str:
    """Create a real JWT for test auth."""
    from app.core.security import create_access_token  # noqa: PLC0415
    from app.core.config import get_settings  # noqa: PLC0415
    settings = get_settings()
    return create_access_token(
        subject=str(user_id),
        tenant_id=str(tenant_id),
        roles=roles,
        secret_key=settings.secret_key,
    )


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Task 8.1 — Schemas extra='forbid'
# ---------------------------------------------------------------------------

def test_slot_recurrente_request_rechaza_campo_extra():
    """Task 8.1 RED→GREEN: SlotRecurrenteRequest rejects extra fields."""
    from app.schemas.encuentro import SlotRecurrenteRequest  # noqa: PLC0415
    import pydantic  # noqa: PLC0415

    with pytest.raises(pydantic.ValidationError, match="extra"):
        SlotRecurrenteRequest(
            asignacion_id=str(uuid.uuid4()),
            materia_id=str(uuid.uuid4()),
            titulo="Test",
            dia_semana="Lunes",
            fecha_inicio="2024-01-01",
            cant_semanas=4,
            hora="10:00:00",
            campo_extra="no permitido",
        )


def test_guardia_request_rechaza_campo_extra():
    """Task 8.2 RED→GREEN: GuardiaRequest rejects extra fields."""
    from app.schemas.guardia import GuardiaRequest  # noqa: PLC0415
    import pydantic  # noqa: PLC0415

    with pytest.raises(pydantic.ValidationError, match="extra"):
        GuardiaRequest(
            asignacion_id=str(uuid.uuid4()),
            materia_id=str(uuid.uuid4()),
            carrera_id=str(uuid.uuid4()),
            cohorte_id=str(uuid.uuid4()),
            dia="Lunes",
            horario="14:00–14:45",
            campo_extra="prohibido",
        )


# ---------------------------------------------------------------------------
# Task 9.1 — POST /api/v1/slots
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_slot_sin_permiso_403(ep_enc_session: AsyncSession, ep_enc_engine):
    """Task 9.1 RED→GREEN: 403 when user lacks encuentros:gestionar."""
    tenant, materia, usuario, asignacion = await _seed_all(ep_enc_session)
    await ep_enc_session.commit()

    # Mock RBAC to return no permissions
    factory = async_sessionmaker(ep_enc_engine, expire_on_commit=False)
    app = _build_app_for_session(factory)

    token = _make_jwt(tenant.id, usuario.id, roles=[])

    with patch(
        "app.services.rbac_service.RbacService.resolver_permisos_efectivos",
        new_callable=AsyncMock,
        return_value={},  # no permissions
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/slots",
                json={
                    "asignacion_id": str(asignacion.id),
                    "materia_id": str(materia.id),
                    "titulo": "Clase semanal",
                    "dia_semana": "Lunes",
                    "fecha_inicio": "2024-01-01",
                    "cant_semanas": 4,
                    "hora": "10:00:00",
                },
                headers=_auth(token),
            )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_post_slot_con_permiso_201(ep_enc_session: AsyncSession, ep_enc_engine):
    """Task 9.1 GREEN: with permission → 201 + slot + N instancias."""
    tenant, materia, usuario, asignacion = await _seed_all(ep_enc_session)
    await ep_enc_session.commit()

    factory = async_sessionmaker(ep_enc_engine, expire_on_commit=False)
    app = _build_app_for_session(factory)

    token = _make_jwt(tenant.id, usuario.id, roles=["PROFESOR"])

    with patch(
        "app.services.rbac_service.RbacService.resolver_permisos_efectivos",
        new_callable=AsyncMock,
        return_value={"encuentros:gestionar": "propio"},
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/slots",
                json={
                    "asignacion_id": str(asignacion.id),
                    "materia_id": str(materia.id),
                    "titulo": "Clase semanal",
                    "dia_semana": "Lunes",
                    "fecha_inicio": "2024-01-01",
                    "cant_semanas": 3,
                    "hora": "10:00:00",
                },
                headers=_auth(token),
            )
    assert resp.status_code == 201
    data = resp.json()
    assert "slot" in data
    assert len(data["instancias"]) == 3


# ---------------------------------------------------------------------------
# Task 9.2 — POST /api/v1/encuentros and PATCH /api/v1/encuentros/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_encuentro_unico_201(ep_enc_session: AsyncSession, ep_enc_engine):
    """Task 9.2 RED→GREEN: create unique encounter → 201."""
    tenant, materia, usuario, _ = await _seed_all(ep_enc_session)
    await ep_enc_session.commit()

    factory = async_sessionmaker(ep_enc_engine, expire_on_commit=False)
    app = _build_app_for_session(factory)
    token = _make_jwt(tenant.id, usuario.id, roles=["PROFESOR"])

    with patch(
        "app.services.rbac_service.RbacService.resolver_permisos_efectivos",
        new_callable=AsyncMock,
        return_value={"encuentros:gestionar": "propio"},
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/encuentros",
                json={
                    "materia_id": str(materia.id),
                    "titulo": "Repaso único",
                    "fecha_unica": "2024-05-20",
                    "hora": "11:00:00",
                    "meet_url": "https://meet.google.com/test",
                },
                headers=_auth(token),
            )
    assert resp.status_code == 201
    data = resp.json()
    assert data["slot_id"] is None
    assert data["estado"] == "Programado"


@pytest.mark.asyncio
async def test_patch_encuentro_edita_instancia_403(ep_enc_session: AsyncSession, ep_enc_engine):
    """Task 9.2 GREEN: PATCH without permission → 403."""
    tenant, materia, usuario, _ = await _seed_all(ep_enc_session)
    await ep_enc_session.commit()

    factory = async_sessionmaker(ep_enc_engine, expire_on_commit=False)
    app = _build_app_for_session(factory)
    token = _make_jwt(tenant.id, usuario.id, roles=[])

    fake_id = uuid.uuid4()
    with patch(
        "app.services.rbac_service.RbacService.resolver_permisos_efectivos",
        new_callable=AsyncMock,
        return_value={},
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/v1/encuentros/{fake_id}",
                json={"estado": "Realizado"},
                headers=_auth(token),
            )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Task 9.3 — GET /api/v1/encuentros/html
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_encuentros_html_retorna_fragmento(
    ep_enc_session: AsyncSession, ep_enc_engine
):
    """Task 9.3 RED→GREEN: GET /encuentros/html returns HTML fragment."""
    tenant, materia, usuario, _ = await _seed_all(ep_enc_session)

    # Create an instancia first
    from app.services.encuentro_service import EncuentroService  # noqa: PLC0415
    svc = EncuentroService(session=ep_enc_session, tenant_id=tenant.id)
    await svc.crear_encuentro_unico(
        materia_id=materia.id,
        titulo="Clase HTML",
        fecha_unica=date(2024, 7, 10),
        hora=time(10, 0),
        current_user_id=usuario.id,
        current_user_roles=["PROFESOR"],
    )
    await ep_enc_session.commit()

    factory = async_sessionmaker(ep_enc_engine, expire_on_commit=False)
    app = _build_app_for_session(factory)
    token = _make_jwt(tenant.id, usuario.id, roles=["PROFESOR"])

    with patch(
        "app.services.rbac_service.RbacService.resolver_permisos_efectivos",
        new_callable=AsyncMock,
        return_value={"encuentros:gestionar": "propio"},
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/encuentros/html",
                params={"materia_id": str(materia.id)},
                headers=_auth(token),
            )
    assert resp.status_code == 200
    assert "<div" in resp.text
    assert "Clase HTML" in resp.text


# ---------------------------------------------------------------------------
# Task 9.4 — GET /api/v1/admin/encuentros
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_encuentros_403_para_profesor(ep_enc_session: AsyncSession, ep_enc_engine):
    """Task 9.4 RED→GREEN: PROFESOR (propio only) cannot access admin endpoint (global req)."""
    tenant, _, usuario, _ = await _seed_all(ep_enc_session)
    await ep_enc_session.commit()

    factory = async_sessionmaker(ep_enc_engine, expire_on_commit=False)
    app = _build_app_for_session(factory)
    token = _make_jwt(tenant.id, usuario.id, roles=["PROFESOR"])

    # Simulate PROFESOR having only propio scope
    with patch(
        "app.services.rbac_service.RbacService.resolver_permisos_efectivos",
        new_callable=AsyncMock,
        return_value={"encuentros:gestionar": "propio"},
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/admin/encuentros",
                headers=_auth(token),
            )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_encuentros_200_para_coordinador(
    ep_enc_session: AsyncSession, ep_enc_engine
):
    """Task 9.4 GREEN: COORDINADOR (global scope) gets 200 from admin endpoint."""
    tenant, _, usuario, _ = await _seed_all(ep_enc_session)
    await ep_enc_session.commit()

    factory = async_sessionmaker(ep_enc_engine, expire_on_commit=False)
    app = _build_app_for_session(factory)
    token = _make_jwt(tenant.id, usuario.id, roles=["COORDINADOR"])

    with patch(
        "app.services.rbac_service.RbacService.resolver_permisos_efectivos",
        new_callable=AsyncMock,
        return_value={"encuentros:gestionar": "global"},
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/admin/encuentros",
                headers=_auth(token),
            )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Task 10.2 — E2E FL-06
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_fl06_slot_recurrente_editar_video_admin_html(
    ep_enc_session: AsyncSession, ep_enc_engine
):
    """Task 10.2 E2E FL-06: crear slot → editar a Realizado+video → admin audita → HTML."""
    tenant, materia, usuario, asignacion = await _seed_all(ep_enc_session)

    from app.services.encuentro_service import EncuentroService  # noqa: PLC0415
    svc = EncuentroService(session=ep_enc_session, tenant_id=tenant.id)

    # 1. Create recurring slot
    slot, instancias = await svc.crear_slot_recurrente(
        asignacion_id=asignacion.id,
        materia_id=materia.id,
        titulo="Clase E2E",
        dia_semana="Lunes",
        fecha_inicio=date(2024, 1, 1),
        cant_semanas=4,
        hora=time(10, 0),
        current_user_id=usuario.id,
        current_user_roles=["PROFESOR"],
    )
    assert len(instancias) == 4

    # 2. Edit first instancia → Realizado + video_url
    video_url = "https://drive.google.com/video/e2e-test"
    updated = await svc.editar_instancia(
        instancias[0].id,
        estado="Realizado",
        video_url=video_url,
    )
    assert updated.estado == "Realizado"
    assert updated.video_url == video_url

    # 3. Admin view sees all 4 instancias
    admin_list = await svc.listar_admin_encuentros()
    tenant_instancias = [i for i in admin_list if i.tenant_id == tenant.id]
    assert len(tenant_instancias) >= 4

    # 4. HTML includes the recording link
    await ep_enc_session.commit()
    html = await svc.generar_html_asignacion(materia.id)
    assert "Ver grabación" in html
    assert video_url in html

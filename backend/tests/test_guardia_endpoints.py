"""
tests/test_guardia_endpoints.py — HTTP integration tests for guardias endpoints.

Tasks covered:
  9.5 POST /api/v1/guardias: 201 for TUTOR with permission; 403 without
  9.5 GET /api/v1/guardias: 200 for COORDINADOR (global); 403 for TUTOR (propio only)
  8.2 schema extra='forbid' already tested in test_encuentro_endpoints

Requires TEST_DATABASE_URL (real DB).

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import os
import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping guardia endpoint integration tests",
)


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


@pytest_asyncio.fixture(scope="module")
async def grd_engine() -> AsyncEngine:
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
async def grd_session(grd_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(grd_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


def _build_app_for_engine(engine):
    from app.main import create_app  # noqa: PLC0415
    from app.core.dependencies import get_db  # noqa: PLC0415

    factory = async_sessionmaker(engine, expire_on_commit=False)
    app = create_app()

    async def override_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_db
    return app


async def _seed_all(session: AsyncSession):
    from app.models.tenant import Tenant      # noqa: PLC0415
    from app.models.materia import Materia    # noqa: PLC0415
    from app.models.carrera import Carrera    # noqa: PLC0415
    from app.models.cohorte import Cohorte    # noqa: PLC0415
    from app.models.usuario import Usuario    # noqa: PLC0415
    from app.models.asignacion import Asignacion  # noqa: PLC0415

    tenant = Tenant(slug=f"grd-{uuid.uuid4().hex[:6]}", nombre="Guardia Tenant", activo=True)
    session.add(tenant)
    await session.flush()

    materia = Materia(tenant_id=tenant.id, nombre="Mat Grd", codigo="GRD-01")
    carrera = Carrera(tenant_id=tenant.id, nombre="Carrera Test", codigo="CT")
    session.add(materia)
    session.add(carrera)
    await session.flush()

    cohorte = Cohorte(
        tenant_id=tenant.id, nombre="Coh 2024", anio=2024, carrera_id=carrera.id
    )
    usuario = Usuario(
        tenant_id=tenant.id,
        nombre="Tutor",
        apellido="EP",
        email=f"t-{uuid.uuid4().hex[:6]}@t.com",
        legajo="T001",
    )
    session.add(cohorte)
    session.add(usuario)
    await session.flush()

    asignacion = Asignacion(
        tenant_id=tenant.id,
        usuario_id=usuario.id,
        rol="TUTOR",
        materia_id=materia.id,
        desde=date(2024, 1, 1),
    )
    session.add(asignacion)
    await session.flush()
    for obj in [tenant, materia, carrera, cohorte, usuario, asignacion]:
        await session.refresh(obj)
    return tenant, materia, carrera, cohorte, usuario, asignacion


def _make_jwt(tenant_id: uuid.UUID, user_id: uuid.UUID, roles: list[str]) -> str:
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
# Task 9.5 — POST /api/v1/guardias
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_guardia_sin_permiso_403(grd_session: AsyncSession, grd_engine):
    """Task 9.5 RED→GREEN: 403 when user has no permission."""
    tenant, materia, carrera, cohorte, usuario, asignacion = await _seed_all(grd_session)
    await grd_session.commit()

    app = _build_app_for_engine(grd_engine)
    token = _make_jwt(tenant.id, usuario.id, roles=[])

    with patch(
        "app.services.rbac_service.RbacService.resolver_permisos_efectivos",
        new_callable=AsyncMock,
        return_value={},
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/guardias",
                json={
                    "asignacion_id": str(asignacion.id),
                    "materia_id": str(materia.id),
                    "carrera_id": str(carrera.id),
                    "cohorte_id": str(cohorte.id),
                    "dia": "Lunes",
                    "horario": "14:00–14:45",
                },
                headers=_auth(token),
            )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_post_guardia_con_permiso_201(grd_session: AsyncSession, grd_engine):
    """Task 9.5 GREEN: with permission → 201 + guardia created."""
    tenant, materia, carrera, cohorte, usuario, asignacion = await _seed_all(grd_session)
    await grd_session.commit()

    app = _build_app_for_engine(grd_engine)
    token = _make_jwt(tenant.id, usuario.id, roles=["TUTOR"])

    with patch(
        "app.services.rbac_service.RbacService.resolver_permisos_efectivos",
        new_callable=AsyncMock,
        return_value={"encuentros:gestionar": "propio"},
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/guardias",
                json={
                    "asignacion_id": str(asignacion.id),
                    "materia_id": str(materia.id),
                    "carrera_id": str(carrera.id),
                    "cohorte_id": str(cohorte.id),
                    "dia": "Lunes",
                    "horario": "14:00–14:45",
                    "comentarios": "Guardia EP test",
                },
                headers=_auth(token),
            )
    assert resp.status_code == 201
    data = resp.json()
    assert data["estado"] == "Pendiente"
    assert data["tenant_id"] == str(tenant.id)


# ---------------------------------------------------------------------------
# Task 9.5 — GET /api/v1/guardias
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_guardias_403_para_tutor_propio(grd_session: AsyncSession, grd_engine):
    """Task 9.5 TRIANGULATE: TUTOR with propio scope cannot list guardias (global required)."""
    tenant, _, _, _, usuario, _ = await _seed_all(grd_session)
    await grd_session.commit()

    app = _build_app_for_engine(grd_engine)
    token = _make_jwt(tenant.id, usuario.id, roles=["TUTOR"])

    with patch(
        "app.services.rbac_service.RbacService.resolver_permisos_efectivos",
        new_callable=AsyncMock,
        return_value={"encuentros:gestionar": "propio"},  # not global
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/guardias", headers=_auth(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_guardias_200_para_coordinador(grd_session: AsyncSession, grd_engine):
    """Task 9.5 GREEN: COORDINADOR (global) gets 200 list."""
    tenant, _, _, _, usuario, _ = await _seed_all(grd_session)
    await grd_session.commit()

    app = _build_app_for_engine(grd_engine)
    token = _make_jwt(tenant.id, usuario.id, roles=["COORDINADOR"])

    with patch(
        "app.services.rbac_service.RbacService.resolver_permisos_efectivos",
        new_callable=AsyncMock,
        return_value={"encuentros:gestionar": "global"},
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/guardias", headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

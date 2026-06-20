"""
tests/test_estructura_services.py — TDD tests for CarreraService, CohorteService,
MateriaService business rules.

Group 8 tests: uniqueness, carrera activa validation, date range validation.

Requires TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid
from datetime import date

import pytest
import pytest_asyncio
import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping estructura service tests",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def svc_engine() -> AsyncEngine:
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
async def svc_session(svc_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(svc_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


async def _make_tenant(session: AsyncSession, *, slug_prefix: str = "svc") -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=f"{slug_prefix}-{uuid.uuid4().hex[:8]}", nombre="Svc Test Tenant", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


# ---------------------------------------------------------------------------
# Group 8: Service + business-rule tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_8_1_carrera_service_dup_codigo_same_tenant_raises_value_error(
    svc_session: AsyncSession,
):
    """8.1 CarreraService.create with dup codigo same tenant → ValueError (router returns 409)."""
    from app.services.carrera_service import CarreraService  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    svc = CarreraService(session=svc_session, tenant_id=tid)

    await svc.create(codigo="ISI", nombre="Ingeniería en Sistemas")

    with pytest.raises(ValueError, match="ya existe"):
        await svc.create(codigo="ISI", nombre="Otra Ingeniería")


@pytest.mark.asyncio
async def test_8_2_carrera_service_dup_codigo_different_tenant_succeeds(
    svc_session: AsyncSession,
):
    """8.2 CarreraService.create with dup codigo different tenant → success (201)."""
    from app.services.carrera_service import CarreraService  # noqa: PLC0415

    tid_a = await _make_tenant(svc_session, slug_prefix="svc-a")
    tid_b = await _make_tenant(svc_session, slug_prefix="svc-b")

    svc_a = CarreraService(session=svc_session, tenant_id=tid_a)
    svc_b = CarreraService(session=svc_session, tenant_id=tid_b)

    await svc_a.create(codigo="ISI", nombre="ISI Tenant A")
    # Should not raise — different tenant
    carrera_b = await svc_b.create(codigo="ISI", nombre="ISI Tenant B")
    assert carrera_b.id is not None
    assert carrera_b.tenant_id == tid_b


@pytest.mark.asyncio
async def test_8_3_cohorte_service_create_with_inactive_carrera_raises_422(
    svc_session: AsyncSession,
):
    """8.3 CohorteService.create with inactive carrera → HTTPException(422)."""
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.services.cohorte_service import CohorteService  # noqa: PLC0415

    tid = await _make_tenant(svc_session)

    carrera = Carrera(tenant_id=tid, codigo="INACT", nombre="Carrera Inactiva", estado="Inactiva")
    svc_session.add(carrera)
    await svc_session.flush()
    await svc_session.refresh(carrera)

    svc = CohorteService(session=svc_session, tenant_id=tid)

    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            carrera_id=carrera.id,
            nombre="2024-1",
            anio=2024,
            vig_desde=date(2024, 3, 1),
        )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_8_4_cohorte_service_update_activate_with_inactive_carrera_raises_422(
    svc_session: AsyncSession,
):
    """8.4 CohorteService.update to activate cohorte when carrera is inactive → HTTPException(422)."""
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.models.cohorte import Cohorte  # noqa: PLC0415
    from app.services.cohorte_service import CohorteService  # noqa: PLC0415

    tid = await _make_tenant(svc_session)

    # Start with active carrera to create cohorte
    carrera = Carrera(tenant_id=tid, codigo="ACT2INACT", nombre="Carrera Activa Temp", estado="Activa")
    svc_session.add(carrera)
    await svc_session.flush()
    await svc_session.refresh(carrera)

    # Create cohorte while carrera is active
    cohorte = Cohorte(
        tenant_id=tid,
        carrera_id=carrera.id,
        nombre="2024-1",
        anio=2024,
        vig_desde=date(2024, 3, 1),
        estado="Inactiva",  # Start inactive
    )
    svc_session.add(cohorte)
    await svc_session.flush()
    await svc_session.refresh(cohorte)

    # Now deactivate the carrera
    carrera.estado = "Inactiva"
    await svc_session.flush()

    # Attempt to activate the cohorte with inactive carrera
    svc = CohorteService(session=svc_session, tenant_id=tid)
    with pytest.raises(HTTPException) as exc_info:
        await svc.update(cohorte.id, estado="Activa")

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_8_5_cohorte_service_create_with_vig_hasta_before_vig_desde_raises_422(
    svc_session: AsyncSession,
):
    """8.5 CohorteService.create with vig_hasta < vig_desde → HTTPException(422)."""
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.services.cohorte_service import CohorteService  # noqa: PLC0415

    tid = await _make_tenant(svc_session)

    carrera = Carrera(tenant_id=tid, codigo="DATES", nombre="Carrera Para Fechas", estado="Activa")
    svc_session.add(carrera)
    await svc_session.flush()
    await svc_session.refresh(carrera)

    svc = CohorteService(session=svc_session, tenant_id=tid)

    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            carrera_id=carrera.id,
            nombre="INVFECHA",
            anio=2024,
            vig_desde=date(2024, 6, 1),
            vig_hasta=date(2024, 3, 1),  # before vig_desde
        )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_8_6_cohorte_service_dup_nombre_same_carrera_raises_value_error(
    svc_session: AsyncSession,
):
    """8.6 CohorteService.create dup nombre same carrera+tenant → ValueError (router returns 409)."""
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.services.cohorte_service import CohorteService  # noqa: PLC0415

    tid = await _make_tenant(svc_session)

    carrera = Carrera(tenant_id=tid, codigo="DUPCO", nombre="Carrera Dup Cohorte", estado="Activa")
    svc_session.add(carrera)
    await svc_session.flush()
    await svc_session.refresh(carrera)

    svc = CohorteService(session=svc_session, tenant_id=tid)

    await svc.create(
        carrera_id=carrera.id,
        nombre="2024-1",
        anio=2024,
        vig_desde=date(2024, 3, 1),
    )

    with pytest.raises(ValueError, match="ya existe"):
        await svc.create(
            carrera_id=carrera.id,
            nombre="2024-1",
            anio=2024,
            vig_desde=date(2024, 4, 1),
        )


@pytest.mark.asyncio
async def test_8_7_materia_service_dup_codigo_same_tenant_raises_value_error(
    svc_session: AsyncSession,
):
    """8.7 MateriaService.create dup codigo same tenant → ValueError (router returns 409)."""
    from app.services.materia_service import MateriaService  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    svc = MateriaService(session=svc_session, tenant_id=tid)

    await svc.create(codigo="MAT101", nombre="Matemática I")

    with pytest.raises(ValueError, match="ya existe"):
        await svc.create(codigo="MAT101", nombre="Otra Matemática")

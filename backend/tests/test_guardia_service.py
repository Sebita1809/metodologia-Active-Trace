"""
tests/test_guardia_service.py — TDD integration tests for GuardiaService.

Tasks covered:
  7.1 registrar sets creada_at server-side, tenant from JWT; happy path
  7.2 TRIANGULATE: provided estado respected; invalid estado → DomainError
  7.3 listar filters by tenant_id; aislamiento multi-tenant

These tests require TEST_DATABASE_URL (real DB — no DB mocks per project rules).

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import os
import uuid
from datetime import date

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine
from app.models.guardia import EstadoGuardia
from app.services.guardia_service import DomainError, GuardiaService

_requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping guardia service integration tests",
)

pytestmark = _requires_db


# ---------------------------------------------------------------------------
# Schema fixtures
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


@pytest_asyncio.fixture(scope="module")
async def guardia_engine() -> AsyncEngine:
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
async def guardia_session(guardia_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(guardia_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

async def _seed_tenant(session: AsyncSession) -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=f"test-{uuid.uuid4().hex[:8]}", nombre="Tenant", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _seed_materia(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(tenant_id=tenant_id, nombre="Física", codigo="FIS-01")
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


async def _seed_carrera(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    from app.models.carrera import Carrera  # noqa: PLC0415
    c = Carrera(tenant_id=tenant_id, nombre="Ingeniería", codigo="ING")
    session.add(c)
    await session.flush()
    await session.refresh(c)
    return c.id


async def _seed_cohorte(
    session: AsyncSession, tenant_id: uuid.UUID, carrera_id: uuid.UUID
) -> uuid.UUID:
    from app.models.cohorte import Cohorte  # noqa: PLC0415
    co = Cohorte(
        tenant_id=tenant_id,
        nombre="Cohorte 2024",
        anio=2024,
        carrera_id=carrera_id,
    )
    session.add(co)
    await session.flush()
    await session.refresh(co)
    return co.id


async def _seed_usuario(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    from app.models.usuario import Usuario  # noqa: PLC0415
    u = Usuario(
        tenant_id=tenant_id,
        nombre="Tutor",
        apellido="Test",
        email=f"tutor-{uuid.uuid4().hex[:6]}@test.com",
        legajo="T001",
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


async def _seed_asignacion(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID,
    materia_id: uuid.UUID,
) -> uuid.UUID:
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    a = Asignacion(
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        rol="TUTOR",
        materia_id=materia_id,
        desde=date(2024, 1, 1),
    )
    session.add(a)
    await session.flush()
    await session.refresh(a)
    return a.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# Task 7.1 — RED+GREEN: registrar happy path

@pytest.mark.asyncio
async def test_registrar_guardia_happy_path(guardia_session: AsyncSession):
    """Task 7.1 RED→GREEN: guardia is created with correct tenant and creada_at server-side."""
    tenant_id = await _seed_tenant(guardia_session)
    materia_id = await _seed_materia(guardia_session, tenant_id)
    carrera_id = await _seed_carrera(guardia_session, tenant_id)
    cohorte_id = await _seed_cohorte(guardia_session, tenant_id, carrera_id)
    usuario_id = await _seed_usuario(guardia_session, tenant_id)
    asignacion_id = await _seed_asignacion(
        guardia_session, tenant_id, usuario_id, materia_id
    )

    svc = GuardiaService(session=guardia_session, tenant_id=tenant_id)

    guardia = await svc.registrar(
        asignacion_id=asignacion_id,
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        dia="Lunes",
        horario="14:00–14:45",
        comentarios="Guardia de prueba",
    )

    assert guardia.id is not None
    assert guardia.tenant_id == tenant_id
    assert guardia.estado == EstadoGuardia.Pendiente
    assert guardia.creada_at is not None  # server-side set


# Task 7.2 — TRIANGULATE: provided estado respected

@pytest.mark.asyncio
async def test_registrar_guardia_estado_provisto(guardia_session: AsyncSession):
    """Task 7.2 TRIANGULATE: explicit estado value is respected."""
    tenant_id = await _seed_tenant(guardia_session)
    materia_id = await _seed_materia(guardia_session, tenant_id)
    carrera_id = await _seed_carrera(guardia_session, tenant_id)
    cohorte_id = await _seed_cohorte(guardia_session, tenant_id, carrera_id)
    usuario_id = await _seed_usuario(guardia_session, tenant_id)
    asignacion_id = await _seed_asignacion(
        guardia_session, tenant_id, usuario_id, materia_id
    )

    svc = GuardiaService(session=guardia_session, tenant_id=tenant_id)

    guardia = await svc.registrar(
        asignacion_id=asignacion_id,
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        dia="Martes",
        horario="10:00–10:45",
        estado=EstadoGuardia.Realizada,
    )

    assert guardia.estado == EstadoGuardia.Realizada


@pytest.mark.asyncio
async def test_registrar_guardia_estado_invalido(guardia_session: AsyncSession):
    """Task 7.2 TRIANGULATE: invalid estado → DomainError."""
    tenant_id = await _seed_tenant(guardia_session)
    materia_id = await _seed_materia(guardia_session, tenant_id)
    carrera_id = await _seed_carrera(guardia_session, tenant_id)
    cohorte_id = await _seed_cohorte(guardia_session, tenant_id, carrera_id)
    usuario_id = await _seed_usuario(guardia_session, tenant_id)
    asignacion_id = await _seed_asignacion(
        guardia_session, tenant_id, usuario_id, materia_id
    )

    svc = GuardiaService(session=guardia_session, tenant_id=tenant_id)

    with pytest.raises(DomainError, match="Estado inválido"):
        await svc.registrar(
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            dia="Lunes",
            horario="08:00–09:00",
            estado="EstadoInventado",
        )


# Task 7.3 — RED+GREEN: listar tenant isolation

@pytest.mark.asyncio
async def test_listar_guardias_aislamiento_tenant(guardia_session: AsyncSession):
    """Task 7.3 RED→GREEN: listar returns only this tenant's guardias; no cross-tenant leak."""
    tenant_a = await _seed_tenant(guardia_session)
    tenant_b = await _seed_tenant(guardia_session)

    materia_a = await _seed_materia(guardia_session, tenant_a)
    materia_b = await _seed_materia(guardia_session, tenant_b)
    carrera_a = await _seed_carrera(guardia_session, tenant_a)
    carrera_b = await _seed_carrera(guardia_session, tenant_b)
    cohorte_a = await _seed_cohorte(guardia_session, tenant_a, carrera_a)
    cohorte_b = await _seed_cohorte(guardia_session, tenant_b, carrera_b)
    usuario_a = await _seed_usuario(guardia_session, tenant_a)
    usuario_b = await _seed_usuario(guardia_session, tenant_b)
    asig_a = await _seed_asignacion(guardia_session, tenant_a, usuario_a, materia_a)
    asig_b = await _seed_asignacion(guardia_session, tenant_b, usuario_b, materia_b)

    svc_a = GuardiaService(session=guardia_session, tenant_id=tenant_a)
    svc_b = GuardiaService(session=guardia_session, tenant_id=tenant_b)

    await svc_a.registrar(
        asignacion_id=asig_a,
        materia_id=materia_a,
        carrera_id=carrera_a,
        cohorte_id=cohorte_a,
        dia="Miércoles",
        horario="13:00–13:45",
    )
    await svc_b.registrar(
        asignacion_id=asig_b,
        materia_id=materia_b,
        carrera_id=carrera_b,
        cohorte_id=cohorte_b,
        dia="Jueves",
        horario="11:00–11:45",
    )

    guardias_a = await svc_a.listar()

    tenant_ids_returned = {str(g.tenant_id) for g in guardias_a}
    assert str(tenant_a) in tenant_ids_returned
    assert str(tenant_b) not in tenant_ids_returned

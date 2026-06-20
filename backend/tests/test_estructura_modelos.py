"""
tests/test_estructura_modelos.py — TDD tests for Carrera, Cohorte, Materia models and repos.

Group 7 tests: models, repositories, constraints, soft-delete, tenant isolation.

Requires TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid
from datetime import date

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping estructura model tests",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def estructura_engine() -> AsyncEngine:
    """Function-scoped engine with the full schema including estructura tables."""
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
async def estructura_session(estructura_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(estructura_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def two_tenants(estructura_session: AsyncSession):
    """Create two tenants and return (tid_a, tid_b)."""
    from app.models.tenant import Tenant  # noqa: PLC0415

    t_a = Tenant(slug=f"est-a-{uuid.uuid4().hex[:6]}", nombre="Estructura Tenant A", activo=True)
    t_b = Tenant(slug=f"est-b-{uuid.uuid4().hex[:6]}", nombre="Estructura Tenant B", activo=True)
    estructura_session.add_all([t_a, t_b])
    await estructura_session.flush()
    await estructura_session.refresh(t_a)
    await estructura_session.refresh(t_b)
    return t_a.id, t_b.id


# ---------------------------------------------------------------------------
# Group 7: Model and repository tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_1_create_carrera_persists_with_defaults(
    estructura_session: AsyncSession,
    two_tenants: tuple[uuid.UUID, uuid.UUID],
):
    """7.1 Create Carrera → persists with correct fields, estado='Activa' by default."""
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.repositories.carrera_repository import CarreraRepository  # noqa: PLC0415

    tid_a, _ = two_tenants
    repo = CarreraRepository(session=estructura_session, tenant_id=tid_a)

    carrera = Carrera(
        tenant_id=tid_a,
        codigo="ISI",
        nombre="Ingeniería en Sistemas",
    )
    created = await repo.create(carrera)

    assert created.id is not None
    assert created.tenant_id == tid_a
    assert created.codigo == "ISI"
    assert created.nombre == "Ingeniería en Sistemas"
    assert created.estado == "Activa"
    assert created.deleted_at is None


@pytest.mark.asyncio
async def test_7_2_carrera_unique_constraint_raises_integrity_error(
    estructura_session: AsyncSession,
    two_tenants: tuple[uuid.UUID, uuid.UUID],
):
    """7.2 Unique constraint (tenant_id, codigo) on Carrera → IntegrityError on duplicate."""
    from app.models.carrera import Carrera  # noqa: PLC0415

    tid_a, _ = two_tenants

    c1 = Carrera(tenant_id=tid_a, codigo="DUP", nombre="Carrera Original")
    estructura_session.add(c1)
    await estructura_session.flush()

    c2 = Carrera(tenant_id=tid_a, codigo="DUP", nombre="Carrera Duplicada")
    estructura_session.add(c2)

    with pytest.raises(IntegrityError):
        await estructura_session.flush()

    await estructura_session.rollback()


@pytest.mark.asyncio
async def test_7_3_soft_delete_carrera(
    estructura_session: AsyncSession,
    two_tenants: tuple[uuid.UUID, uuid.UUID],
):
    """7.3 Soft delete Carrera → deleted_at set, not returned by list()."""
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.repositories.carrera_repository import CarreraRepository  # noqa: PLC0415

    tid_a, _ = two_tenants
    repo = CarreraRepository(session=estructura_session, tenant_id=tid_a)

    carrera = Carrera(
        tenant_id=tid_a,
        codigo="DEL",
        nombre="Carrera a Eliminar",
    )
    created = await repo.create(carrera)
    assert created.deleted_at is None

    deleted = await repo.soft_delete(created.id)
    assert deleted is True

    # Should not appear in list
    all_carreras = await repo.list()
    ids = [c.id for c in all_carreras]
    assert created.id not in ids

    # deleted_at should be set
    # Re-fetch via including-deleted query
    stmt = (
        repo._base_query_including_deleted()
        .where(Carrera.id == created.id)
    )
    result = await estructura_session.execute(stmt)
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.deleted_at is not None


@pytest.mark.asyncio
async def test_7_4_create_cohorte_persists_with_fk(
    estructura_session: AsyncSession,
    two_tenants: tuple[uuid.UUID, uuid.UUID],
):
    """7.4 Create Cohorte → persists with FK to Carrera and vig_hasta=None."""
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.models.cohorte import Cohorte  # noqa: PLC0415
    from app.repositories.cohorte_repository import CohorteRepository  # noqa: PLC0415

    tid_a, _ = two_tenants

    carrera = Carrera(tenant_id=tid_a, codigo="ENFT", nombre="Enfermería")
    estructura_session.add(carrera)
    await estructura_session.flush()
    await estructura_session.refresh(carrera)

    repo = CohorteRepository(session=estructura_session, tenant_id=tid_a)
    cohorte = Cohorte(
        tenant_id=tid_a,
        carrera_id=carrera.id,
        nombre="2024-1",
        anio=2024,
        vig_desde=date(2024, 3, 1),
        vig_hasta=None,
    )
    created = await repo.create(cohorte)

    assert created.id is not None
    assert created.carrera_id == carrera.id
    assert created.nombre == "2024-1"
    assert created.anio == 2024
    assert created.vig_hasta is None
    assert created.estado == "Activa"


@pytest.mark.asyncio
async def test_7_5_cohorte_unique_constraint_raises_integrity_error(
    estructura_session: AsyncSession,
    two_tenants: tuple[uuid.UUID, uuid.UUID],
):
    """7.5 Unique constraint (tenant_id, carrera_id, nombre) on Cohorte → IntegrityError."""
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.models.cohorte import Cohorte  # noqa: PLC0415

    tid_a, _ = two_tenants

    carrera = Carrera(tenant_id=tid_a, codigo="DUP2", nombre="Carrera DUP")
    estructura_session.add(carrera)
    await estructura_session.flush()
    await estructura_session.refresh(carrera)

    c1 = Cohorte(
        tenant_id=tid_a,
        carrera_id=carrera.id,
        nombre="2024-1",
        anio=2024,
        vig_desde=date(2024, 3, 1),
    )
    estructura_session.add(c1)
    await estructura_session.flush()

    c2 = Cohorte(
        tenant_id=tid_a,
        carrera_id=carrera.id,
        nombre="2024-1",
        anio=2024,
        vig_desde=date(2024, 4, 1),
    )
    estructura_session.add(c2)

    with pytest.raises(IntegrityError):
        await estructura_session.flush()

    await estructura_session.rollback()


@pytest.mark.asyncio
async def test_7_6_create_materia_persists_with_defaults(
    estructura_session: AsyncSession,
    two_tenants: tuple[uuid.UUID, uuid.UUID],
):
    """7.6 Create Materia → persists with estado='Activa' by default."""
    from app.models.materia import Materia  # noqa: PLC0415
    from app.repositories.materia_repository import MateriaRepository  # noqa: PLC0415

    tid_a, _ = two_tenants
    repo = MateriaRepository(session=estructura_session, tenant_id=tid_a)

    materia = Materia(
        tenant_id=tid_a,
        codigo="MAT101",
        nombre="Matemática I",
    )
    created = await repo.create(materia)

    assert created.id is not None
    assert created.codigo == "MAT101"
    assert created.nombre == "Matemática I"
    assert created.estado == "Activa"
    assert created.deleted_at is None


@pytest.mark.asyncio
async def test_7_7_materia_unique_constraint_raises_integrity_error(
    estructura_session: AsyncSession,
    two_tenants: tuple[uuid.UUID, uuid.UUID],
):
    """7.7 Unique constraint (tenant_id, codigo) on Materia → IntegrityError on duplicate."""
    from app.models.materia import Materia  # noqa: PLC0415

    tid_a, _ = two_tenants

    m1 = Materia(tenant_id=tid_a, codigo="DUPMAT", nombre="Materia Original")
    estructura_session.add(m1)
    await estructura_session.flush()

    m2 = Materia(tenant_id=tid_a, codigo="DUPMAT", nombre="Materia Duplicada")
    estructura_session.add(m2)

    with pytest.raises(IntegrityError):
        await estructura_session.flush()

    await estructura_session.rollback()


@pytest.mark.asyncio
async def test_7_8_carrera_repo_tenant_isolation(
    estructura_session: AsyncSession,
    two_tenants: tuple[uuid.UUID, uuid.UUID],
):
    """7.8 Repo tenant isolation: Carrera repo scoped to tenant A does not return tenant B's carreras."""
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.repositories.carrera_repository import CarreraRepository  # noqa: PLC0415

    tid_a, tid_b = two_tenants

    c_a = Carrera(tenant_id=tid_a, codigo="ONLY_A", nombre="Solo Tenant A")
    c_b = Carrera(tenant_id=tid_b, codigo="ONLY_B", nombre="Solo Tenant B")
    estructura_session.add_all([c_a, c_b])
    await estructura_session.flush()

    repo_a = CarreraRepository(session=estructura_session, tenant_id=tid_a)
    results = await repo_a.list()
    codigos = [c.codigo for c in results]

    assert "ONLY_A" in codigos
    assert "ONLY_B" not in codigos

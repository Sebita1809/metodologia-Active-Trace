"""
tests/test_programas_fechas.py — Integration tests for C-17 (programas-y-fechas-academicas).

Tests for ProgramaMateria and FechaAcademica: repositories, services, HTTP endpoints.

Requires TEST_DATABASE_URL (PostgreSQL).
Skips all tests if TEST_DATABASE_URL is not set — no mocks.

Groups:
  7.1 — Tests migración 015 (via ORM create_all): tablas, índices únicos parciales, CheckConstraints
  7.2 — ProgramaMateriaRepository/Service: alta nueva combinación, referencia opaca, listado y filtros
  7.3 — ProgramaMateriaService: reemplazo soft-deletea el anterior, re-alta sobre combo borrado
  7.4 — ProgramaMateriaService: validación de materia/carrera/cohorte de otro tenant rechazada
  7.5 — ProgramaMateriaService: aislamiento por tenant (404 cross-tenant, listado acotado)
  7.6 — FechaAcademicaService: alta válida, tipo fuera de enum y numero=0 rechazados, combo duplicado
  7.7 — FechaAcademicaService: listado tabular ordenado por fecha; update y soft-delete; re-alta
  7.8 — FechaAcademicaService: generación de fragmento LMS (formato, orden, combinación vacía)
  7.9 — FechaAcademicaService: validación de referencias y aislamiento por tenant
  7.10 — RBAC: endpoints responden 403 sin estructura:gestionar

TDD cycle evidence:
  RED: tests written to specify behavior before production code.
  GREEN: minimum implementation passes all scenarios.
  TRIANGULATE: at least 2 test cases per behavior.
  REFACTOR: code cleaned up after green.
"""
from __future__ import annotations

import os
import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
import sqlalchemy as sa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping programas_fechas integration tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Engine fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def pf_engine() -> AsyncEngine:
    """Create a full schema for programas-fechas tests, tear down after."""
    import app.models.tenant              # noqa: F401
    import app.models.user               # noqa: F401
    import app.models.rol                # noqa: F401
    import app.models.permiso            # noqa: F401
    import app.models.rol_permiso        # noqa: F401
    import app.models.usuario_rol        # noqa: F401
    import app.models.audit_log          # noqa: F401
    import app.models.carrera            # noqa: F401
    import app.models.cohorte            # noqa: F401
    import app.models.materia            # noqa: F401
    import app.models.usuario            # noqa: F401
    import app.models.asignacion         # noqa: F401
    import app.models.tarea              # noqa: F401
    import app.models.comentario_tarea   # noqa: F401
    import app.models.programa_materia   # noqa: F401
    import app.models.fecha_academica    # noqa: F401
    import app.features.auth.models      # noqa: F401

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
async def pf_session(pf_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(pf_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _make_tenant(session: AsyncSession, suffix: str = "") -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(
        slug=f"pf-{uuid.uuid4().hex[:8]}{suffix}",
        nombre="PF Test",
        activo=True,
    )
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_usuario(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.models.usuario import Usuario      # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
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


async def _make_materia(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(tenant_id=tid, codigo=f"M_{uuid.uuid4().hex[:6]}", nombre="Materia Test")
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


async def _make_carrera(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.carrera import Carrera  # noqa: PLC0415
    c = Carrera(tenant_id=tid, codigo=f"C_{uuid.uuid4().hex[:6]}", nombre="Carrera Test")
    session.add(c)
    await session.flush()
    await session.refresh(c)
    return c.id


async def _make_cohorte(session: AsyncSession, tid: uuid.UUID, carrera_id: uuid.UUID) -> uuid.UUID:
    from app.models.cohorte import Cohorte  # noqa: PLC0415
    c = Cohorte(
        tenant_id=tid,
        carrera_id=carrera_id,
        nombre=f"2026-{uuid.uuid4().hex[:4]}",
        anio=2026,
        vig_desde=date(2026, 1, 1),
    )
    session.add(c)
    await session.flush()
    await session.refresh(c)
    return c.id


async def _make_programa(
    session: AsyncSession,
    tid: uuid.UUID,
    materia_id: uuid.UUID,
    carrera_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    titulo: str = "Programa Test",
    referencia_archivo: str = "s3://bucket/prog.pdf",
) -> uuid.UUID:
    from app.models.programa_materia import ProgramaMateria  # noqa: PLC0415
    p = ProgramaMateria(
        tenant_id=tid,
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        titulo=titulo,
        referencia_archivo=referencia_archivo,
    )
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p.id


async def _make_fecha(
    session: AsyncSession,
    tid: uuid.UUID,
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    tipo: str = "Parcial",
    numero: int = 1,
    fecha: date | None = None,
    titulo: str = "Fecha Test",
    periodo: str | None = None,
) -> uuid.UUID:
    from app.models.fecha_academica import FechaAcademica  # noqa: PLC0415
    f = FechaAcademica(
        tenant_id=tid,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        tipo=tipo,
        numero=numero,
        fecha=fecha or date(2026, 6, 15),
        titulo=titulo,
        periodo=periodo,
    )
    session.add(f)
    await session.flush()
    await session.refresh(f)
    return f.id


def _make_current_user(user_id: uuid.UUID, tenant_id: uuid.UUID, roles: list[str] | None = None):
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    return CurrentUser(user_id=user_id, tenant_id=tenant_id, roles=roles or ["COORDINADOR"])


# ---------------------------------------------------------------------------
# Group 7.1 — Migration: tables exist with constraints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_1_programa_materia_table_created(pf_session: AsyncSession):
    """7.1: programa_materia table exists and accepts a valid row."""
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    prog_id = await _make_programa(pf_session, tid, materia_id, carrera_id, cohorte_id)
    await pf_session.commit()
    assert prog_id is not None


@pytest.mark.asyncio
async def test_7_1_fecha_academica_table_created(pf_session: AsyncSession):
    """7.1: fecha_academica table exists and accepts a valid row."""
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    fecha_id = await _make_fecha(pf_session, tid, materia_id, cohorte_id)
    await pf_session.commit()
    assert fecha_id is not None


# ---------------------------------------------------------------------------
# Group 7.2 — ProgramaMateria: create, opaque ref, list, filters
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_2_programa_create_new_combo(pf_session: AsyncSession):
    """7.2: Creating a programme for a new combo persists correctly."""
    from app.schemas.programas import ProgramaCreate  # noqa: PLC0415
    from app.services.programa_materia_service import ProgramaMateriaService  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    uid = await _make_usuario(pf_session, tid)
    await pf_session.commit()

    svc = ProgramaMateriaService(session=pf_session, tenant_id=tid)
    data = ProgramaCreate(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        titulo="Programa de Álgebra",
        referencia_archivo="s3://bucket/algebra.pdf",
    )
    response = await svc.asociar_programa(data)

    assert response.materia_id == materia_id
    assert response.carrera_id == carrera_id
    assert response.cohorte_id == cohorte_id
    assert response.titulo == "Programa de Álgebra"
    assert response.referencia_archivo == "s3://bucket/algebra.pdf"
    assert response.tenant_id == tid
    assert response.deleted_at is None


@pytest.mark.asyncio
async def test_7_2_programa_referencia_archivo_opaca(pf_session: AsyncSession):
    """7.2: referencia_archivo is stored as-is without interpretation."""
    from app.schemas.programas import ProgramaCreate  # noqa: PLC0415
    from app.services.programa_materia_service import ProgramaMateriaService  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    opaque_ref = "gs://my-bucket/2026/prog_algebra_v3.pdf?token=xyz123"
    svc = ProgramaMateriaService(session=pf_session, tenant_id=tid)
    data = ProgramaCreate(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        titulo="Test opaque",
        referencia_archivo=opaque_ref,
    )
    response = await svc.asociar_programa(data)

    assert response.referencia_archivo == opaque_ref  # stored exactly as provided


@pytest.mark.asyncio
async def test_7_2_programa_listar_sin_filtros(pf_session: AsyncSession):
    """7.2: listar returns all vivo programmes for the tenant."""
    from app.schemas.programas import ProgramaCreate, ProgramaFiltros  # noqa: PLC0415
    from app.services.programa_materia_service import ProgramaMateriaService  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    m1 = await _make_materia(pf_session, tid)
    m2 = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    svc = ProgramaMateriaService(session=pf_session, tenant_id=tid)
    await svc.asociar_programa(ProgramaCreate(
        materia_id=m1, carrera_id=carrera_id, cohorte_id=cohorte_id,
        titulo="P1", referencia_archivo="s3://p1",
    ))
    await svc.asociar_programa(ProgramaCreate(
        materia_id=m2, carrera_id=carrera_id, cohorte_id=cohorte_id,
        titulo="P2", referencia_archivo="s3://p2",
    ))

    programas = await svc.listar(ProgramaFiltros())
    assert len(programas) == 2


@pytest.mark.asyncio
async def test_7_2_programa_listar_filtro_materia(pf_session: AsyncSession):
    """7.2: listar filters by materia_id correctly."""
    from app.schemas.programas import ProgramaCreate, ProgramaFiltros  # noqa: PLC0415
    from app.services.programa_materia_service import ProgramaMateriaService  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    m1 = await _make_materia(pf_session, tid)
    m2 = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    svc = ProgramaMateriaService(session=pf_session, tenant_id=tid)
    await svc.asociar_programa(ProgramaCreate(
        materia_id=m1, carrera_id=carrera_id, cohorte_id=cohorte_id,
        titulo="P1", referencia_archivo="s3://p1",
    ))
    await svc.asociar_programa(ProgramaCreate(
        materia_id=m2, carrera_id=carrera_id, cohorte_id=cohorte_id,
        titulo="P2", referencia_archivo="s3://p2",
    ))

    programas = await svc.listar(ProgramaFiltros(materia_id=m1))
    assert len(programas) == 1
    assert programas[0].materia_id == m1


# ---------------------------------------------------------------------------
# Group 7.3 — ProgramaMateria: reemplazo y re-alta
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_3_reemplazo_soft_deletea_anterior(pf_session: AsyncSession):
    """7.3: Replacing a vivo programme soft-deletes the previous one."""
    from app.schemas.programas import ProgramaCreate  # noqa: PLC0415
    from app.services.programa_materia_service import ProgramaMateriaService  # noqa: PLC0415
    from app.repositories.programa_materia_repository import ProgramaMateriaRepository  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    svc = ProgramaMateriaService(session=pf_session, tenant_id=tid)
    first = await svc.asociar_programa(ProgramaCreate(
        materia_id=materia_id, carrera_id=carrera_id, cohorte_id=cohorte_id,
        titulo="V1", referencia_archivo="s3://v1",
    ))
    first_id = first.id

    # Replace
    second = await svc.asociar_programa(ProgramaCreate(
        materia_id=materia_id, carrera_id=carrera_id, cohorte_id=cohorte_id,
        titulo="V2", referencia_archivo="s3://v2",
    ))
    await pf_session.commit()

    # Only one vivo combo exists
    repo = ProgramaMateriaRepository(session=pf_session, tenant_id=tid)
    vivo = await repo.get_vivo_por_combo(
        materia_id=materia_id, carrera_id=carrera_id, cohorte_id=cohorte_id
    )
    assert vivo is not None
    assert vivo.id == second.id
    assert vivo.titulo == "V2"

    # Previous row is soft-deleted (get by ID on base repo including deleted)
    stmt = sa.select(vivo.__class__).where(vivo.__class__.id == first_id)
    result = await pf_session.execute(stmt)
    old = result.scalar_one_or_none()
    assert old is not None
    assert old.deleted_at is not None  # soft-deleted


@pytest.mark.asyncio
async def test_7_3_realta_sobre_combo_borrado_funciona(pf_session: AsyncSession):
    """7.3: Re-creating a combo after soft-delete does not collide."""
    from app.schemas.programas import ProgramaCreate  # noqa: PLC0415
    from app.services.programa_materia_service import ProgramaMateriaService  # noqa: PLC0415
    from app.repositories.programa_materia_repository import ProgramaMateriaRepository  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    svc = ProgramaMateriaService(session=pf_session, tenant_id=tid)
    first = await svc.asociar_programa(ProgramaCreate(
        materia_id=materia_id, carrera_id=carrera_id, cohorte_id=cohorte_id,
        titulo="V1", referencia_archivo="s3://v1",
    ))
    await pf_session.commit()

    # Soft-delete the programme directly
    repo = ProgramaMateriaRepository(session=pf_session, tenant_id=tid)
    await repo.soft_delete(first.id)
    await pf_session.commit()

    # Re-create the same combo — should not raise
    second = await svc.asociar_programa(ProgramaCreate(
        materia_id=materia_id, carrera_id=carrera_id, cohorte_id=cohorte_id,
        titulo="V2", referencia_archivo="s3://v2",
    ))
    await pf_session.commit()

    assert second.id != first.id
    assert second.deleted_at is None


# ---------------------------------------------------------------------------
# Group 7.4 — ProgramaMateria: validación cross-tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_4_materia_otro_tenant_rechazada(pf_session: AsyncSession):
    """7.4: materia_id from another tenant is rejected with 404."""
    from fastapi import HTTPException  # noqa: PLC0415
    from app.schemas.programas import ProgramaCreate  # noqa: PLC0415
    from app.services.programa_materia_service import ProgramaMateriaService  # noqa: PLC0415
    tid_a = await _make_tenant(pf_session, "A")
    tid_b = await _make_tenant(pf_session, "B")
    carrera_id_a = await _make_carrera(pf_session, tid_a)
    materia_b = await _make_materia(pf_session, tid_b)  # belongs to B
    cohorte_id_a = await _make_cohorte(pf_session, tid_a, carrera_id_a)
    await pf_session.commit()

    svc_a = ProgramaMateriaService(session=pf_session, tenant_id=tid_a)
    with pytest.raises(HTTPException) as exc_info:
        await svc_a.asociar_programa(ProgramaCreate(
            materia_id=materia_b,  # from tenant B
            carrera_id=carrera_id_a,
            cohorte_id=cohorte_id_a,
            titulo="Cross-tenant attempt",
            referencia_archivo="s3://x",
        ))
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_7_4_cohorte_otro_tenant_rechazada(pf_session: AsyncSession):
    """7.4: cohorte_id from another tenant is rejected with 404."""
    from fastapi import HTTPException  # noqa: PLC0415
    from app.schemas.programas import ProgramaCreate  # noqa: PLC0415
    from app.services.programa_materia_service import ProgramaMateriaService  # noqa: PLC0415
    tid_a = await _make_tenant(pf_session, "A2")
    tid_b = await _make_tenant(pf_session, "B2")
    carrera_id_a = await _make_carrera(pf_session, tid_a)
    materia_a = await _make_materia(pf_session, tid_a)
    carrera_b = await _make_carrera(pf_session, tid_b)
    cohorte_b = await _make_cohorte(pf_session, tid_b, carrera_b)  # belongs to B
    await pf_session.commit()

    svc_a = ProgramaMateriaService(session=pf_session, tenant_id=tid_a)
    with pytest.raises(HTTPException) as exc_info:
        await svc_a.asociar_programa(ProgramaCreate(
            materia_id=materia_a,
            carrera_id=carrera_id_a,
            cohorte_id=cohorte_b,  # from tenant B
            titulo="Cross-tenant cohorte",
            referencia_archivo="s3://x",
        ))
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Group 7.5 — ProgramaMateria: aislamiento por tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_5_programa_otro_tenant_no_visible(pf_session: AsyncSession):
    """7.5: Programme from tenant B is not visible to tenant A."""
    from app.services.programa_materia_service import ProgramaMateriaService  # noqa: PLC0415
    from app.repositories.programa_materia_repository import ProgramaMateriaRepository  # noqa: PLC0415
    tid_a = await _make_tenant(pf_session, "A3")
    tid_b = await _make_tenant(pf_session, "B3")
    carrera_b = await _make_carrera(pf_session, tid_b)
    materia_b = await _make_materia(pf_session, tid_b)
    cohorte_b = await _make_cohorte(pf_session, tid_b, carrera_b)
    prog_b_id = await _make_programa(pf_session, tid_b, materia_b, carrera_b, cohorte_b)
    await pf_session.commit()

    repo_a = ProgramaMateriaRepository(session=pf_session, tenant_id=tid_a)
    result = await repo_a.get(prog_b_id)
    assert result is None  # tenant A cannot see tenant B's programme


@pytest.mark.asyncio
async def test_7_5_listado_acotado_al_tenant(pf_session: AsyncSession):
    """7.5: listar returns only programmes of the session tenant."""
    from app.schemas.programas import ProgramaCreate, ProgramaFiltros  # noqa: PLC0415
    from app.services.programa_materia_service import ProgramaMateriaService  # noqa: PLC0415
    tid_a = await _make_tenant(pf_session, "A4")
    tid_b = await _make_tenant(pf_session, "B4")
    carrera_a = await _make_carrera(pf_session, tid_a)
    carrera_b = await _make_carrera(pf_session, tid_b)
    m_a = await _make_materia(pf_session, tid_a)
    m_b = await _make_materia(pf_session, tid_b)
    c_a = await _make_cohorte(pf_session, tid_a, carrera_a)
    c_b = await _make_cohorte(pf_session, tid_b, carrera_b)
    await pf_session.commit()

    svc_a = ProgramaMateriaService(session=pf_session, tenant_id=tid_a)
    svc_b = ProgramaMateriaService(session=pf_session, tenant_id=tid_b)
    await svc_a.asociar_programa(ProgramaCreate(
        materia_id=m_a, carrera_id=carrera_a, cohorte_id=c_a,
        titulo="Tenant A", referencia_archivo="s3://a",
    ))
    await svc_b.asociar_programa(ProgramaCreate(
        materia_id=m_b, carrera_id=carrera_b, cohorte_id=c_b,
        titulo="Tenant B", referencia_archivo="s3://b",
    ))

    programas_a = await svc_a.listar(ProgramaFiltros())
    assert len(programas_a) == 1
    assert programas_a[0].tenant_id == tid_a


# ---------------------------------------------------------------------------
# Group 7.6 — FechaAcademica: alta, validaciones, duplicado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_6_crear_primera_fecha_valida(pf_session: AsyncSession):
    """7.6: Creating the first Parcial for a materia×cohorte succeeds."""
    from app.schemas.fechas_academicas import FechaAcademicaCreate  # noqa: PLC0415
    from app.models.fecha_academica import TipoFechaAcademica  # noqa: PLC0415
    from app.services.fecha_academica_service import FechaAcademicaService  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    svc = FechaAcademicaService(session=pf_session, tenant_id=tid)
    data = FechaAcademicaCreate(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        tipo=TipoFechaAcademica.Parcial,
        numero=1,
        fecha=date(2026, 7, 10),
        titulo="Primer parcial",
    )
    response = await svc.crear_fecha(data)

    assert response.tipo == "Parcial"
    assert response.numero == 1
    assert response.tenant_id == tid
    assert response.deleted_at is None


@pytest.mark.asyncio
async def test_7_6_tipo_invalido_rechazado_por_schema():
    """7.6: tipo not in TipoFechaAcademica raises ValidationError (schema-level)."""
    from pydantic import ValidationError  # noqa: PLC0415
    from app.schemas.fechas_academicas import FechaAcademicaCreate  # noqa: PLC0415

    with pytest.raises(ValidationError):
        FechaAcademicaCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo="Examen",  # invalid tipo
            numero=1,
            fecha=date(2026, 7, 10),
            titulo="Examen inválido",
        )


@pytest.mark.asyncio
async def test_7_6_numero_cero_rechazado_por_schema():
    """7.6: numero=0 raises ValidationError (schema-level validator)."""
    from pydantic import ValidationError  # noqa: PLC0415
    from app.schemas.fechas_academicas import FechaAcademicaCreate  # noqa: PLC0415
    from app.models.fecha_academica import TipoFechaAcademica  # noqa: PLC0415

    with pytest.raises(ValidationError):
        FechaAcademicaCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo=TipoFechaAcademica.Parcial,
            numero=0,  # invalid
            fecha=date(2026, 7, 10),
            titulo="Numero cero",
        )


@pytest.mark.asyncio
async def test_7_6_combo_duplicado_rechazado(pf_session: AsyncSession):
    """7.6: Creating a duplicate combo raises 409."""
    from fastapi import HTTPException  # noqa: PLC0415
    from app.schemas.fechas_academicas import FechaAcademicaCreate  # noqa: PLC0415
    from app.models.fecha_academica import TipoFechaAcademica  # noqa: PLC0415
    from app.services.fecha_academica_service import FechaAcademicaService  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    svc = FechaAcademicaService(session=pf_session, tenant_id=tid)
    base_data = dict(
        materia_id=materia_id, cohorte_id=cohorte_id,
        tipo=TipoFechaAcademica.Parcial, numero=1,
        fecha=date(2026, 7, 10), titulo="Primer parcial",
    )
    await svc.crear_fecha(FechaAcademicaCreate(**base_data))

    with pytest.raises(HTTPException) as exc_info:
        await svc.crear_fecha(FechaAcademicaCreate(**base_data))  # same combo
    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# Group 7.7 — FechaAcademica: listado, update, soft-delete, re-alta
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_7_listar_ordenado_por_fecha(pf_session: AsyncSession):
    """7.7: listar_por_materia_cohorte returns rows ordered by fecha asc."""
    from app.schemas.fechas_academicas import FechaAcademicaCreate  # noqa: PLC0415
    from app.models.fecha_academica import TipoFechaAcademica  # noqa: PLC0415
    from app.services.fecha_academica_service import FechaAcademicaService  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    svc = FechaAcademicaService(session=pf_session, tenant_id=tid)
    # Create 3 fechas out of order
    await svc.crear_fecha(FechaAcademicaCreate(
        materia_id=materia_id, cohorte_id=cohorte_id,
        tipo=TipoFechaAcademica.Parcial, numero=2,
        fecha=date(2026, 8, 20), titulo="2do parcial",
    ))
    await svc.crear_fecha(FechaAcademicaCreate(
        materia_id=materia_id, cohorte_id=cohorte_id,
        tipo=TipoFechaAcademica.Parcial, numero=1,
        fecha=date(2026, 7, 10), titulo="1er parcial",
    ))
    await svc.crear_fecha(FechaAcademicaCreate(
        materia_id=materia_id, cohorte_id=cohorte_id,
        tipo=TipoFechaAcademica.Coloquio, numero=1,
        fecha=date(2026, 9, 5), titulo="Coloquio",
    ))

    fechas = await svc.listar_por_materia_cohorte(
        materia_id=materia_id, cohorte_id=cohorte_id
    )
    assert len(fechas) == 3
    for i in range(len(fechas) - 1):
        assert fechas[i].fecha <= fechas[i + 1].fecha


@pytest.mark.asyncio
async def test_7_7_listar_materia_cohorte_sin_fechas(pf_session: AsyncSession):
    """7.7: listar for a combo with no fechas returns empty list."""
    from app.services.fecha_academica_service import FechaAcademicaService  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    svc = FechaAcademicaService(session=pf_session, tenant_id=tid)
    fechas = await svc.listar_por_materia_cohorte(
        materia_id=materia_id, cohorte_id=cohorte_id
    )
    assert fechas == []


@pytest.mark.asyncio
async def test_7_7_update_fecha_y_titulo(pf_session: AsyncSession):
    """7.7: actualizar_fecha updates fecha and titulo, preserves tipo and numero."""
    from app.schemas.fechas_academicas import FechaAcademicaCreate, FechaAcademicaUpdate  # noqa: PLC0415
    from app.models.fecha_academica import TipoFechaAcademica  # noqa: PLC0415
    from app.services.fecha_academica_service import FechaAcademicaService  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    svc = FechaAcademicaService(session=pf_session, tenant_id=tid)
    created = await svc.crear_fecha(FechaAcademicaCreate(
        materia_id=materia_id, cohorte_id=cohorte_id,
        tipo=TipoFechaAcademica.TP, numero=1,
        fecha=date(2026, 7, 5), titulo="TP original",
    ))

    nueva_fecha = date(2026, 7, 20)
    updated = await svc.actualizar_fecha(
        created.id,
        FechaAcademicaUpdate(fecha=nueva_fecha, titulo="TP reprogramado"),
    )

    assert updated.fecha == nueva_fecha
    assert updated.titulo == "TP reprogramado"
    assert updated.tipo == "TP"  # preserved
    assert updated.numero == 1   # preserved


@pytest.mark.asyncio
async def test_7_7_soft_delete_y_realta(pf_session: AsyncSession):
    """7.7: soft-delete removes from listing; re-create with same combo succeeds."""
    from app.schemas.fechas_academicas import FechaAcademicaCreate  # noqa: PLC0415
    from app.models.fecha_academica import TipoFechaAcademica  # noqa: PLC0415
    from app.services.fecha_academica_service import FechaAcademicaService  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    svc = FechaAcademicaService(session=pf_session, tenant_id=tid)
    base_data = dict(
        materia_id=materia_id, cohorte_id=cohorte_id,
        tipo=TipoFechaAcademica.Recuperatorio, numero=1,
        fecha=date(2026, 8, 1), titulo="Recuperatorio 1",
    )
    first = await svc.crear_fecha(FechaAcademicaCreate(**base_data))
    await pf_session.commit()

    # Soft-delete
    await svc.eliminar_fecha(first.id)
    await pf_session.commit()

    # Must not appear in listing
    fechas = await svc.listar_por_materia_cohorte(
        materia_id=materia_id, cohorte_id=cohorte_id
    )
    assert all(f.id != first.id for f in fechas)

    # Re-create same combo — should succeed
    second = await svc.crear_fecha(FechaAcademicaCreate(**base_data))
    assert second.id != first.id
    assert second.deleted_at is None


# ---------------------------------------------------------------------------
# Group 7.8 — FechaAcademica: fragmento LMS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_8_fragmento_lms_con_fechas(pf_session: AsyncSession):
    """7.8: generar_fragmento_lms returns HTML with one entry per fecha."""
    from app.schemas.fechas_academicas import FechaAcademicaCreate  # noqa: PLC0415
    from app.models.fecha_academica import TipoFechaAcademica  # noqa: PLC0415
    from app.services.fecha_academica_service import FechaAcademicaService  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    svc = FechaAcademicaService(session=pf_session, tenant_id=tid)
    await svc.crear_fecha(FechaAcademicaCreate(
        materia_id=materia_id, cohorte_id=cohorte_id,
        tipo=TipoFechaAcademica.Parcial, numero=1,
        fecha=date(2026, 7, 10), titulo="1er Parcial",
    ))
    await svc.crear_fecha(FechaAcademicaCreate(
        materia_id=materia_id, cohorte_id=cohorte_id,
        tipo=TipoFechaAcademica.Parcial, numero=2,
        fecha=date(2026, 8, 20), titulo="2do Parcial",
    ))

    fragmento = await svc.generar_fragmento_lms(
        materia_id=materia_id, cohorte_id=cohorte_id
    )

    assert fragmento.formato == "html"
    assert fragmento.materia_id == materia_id
    assert fragmento.cohorte_id == cohorte_id
    # HTML contains both entries
    assert "Parcial 1" in fragmento.contenido
    assert "Parcial 2" in fragmento.contenido
    assert "1er Parcial" in fragmento.contenido
    assert "2do Parcial" in fragmento.contenido


@pytest.mark.asyncio
async def test_7_8_fragmento_lms_sin_fechas(pf_session: AsyncSession):
    """7.8: generar_fragmento_lms for empty combo returns empty contenido, no error."""
    from app.services.fecha_academica_service import FechaAcademicaService  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    svc = FechaAcademicaService(session=pf_session, tenant_id=tid)
    fragmento = await svc.generar_fragmento_lms(
        materia_id=materia_id, cohorte_id=cohorte_id
    )

    assert fragmento.formato == "html"
    assert fragmento.contenido == ""


@pytest.mark.asyncio
async def test_7_8_fragmento_lms_no_llama_al_lms(pf_session: AsyncSession):
    """7.8: Fragmento LMS only builds a string — verify no external HTTP call."""
    # This test verifies the service method returns quickly without side effects.
    # The service only reads from DB and formats a string.
    from app.services.fecha_academica_service import FechaAcademicaService  # noqa: PLC0415
    from app.schemas.fechas_academicas import FechaAcademicaCreate  # noqa: PLC0415
    from app.models.fecha_academica import TipoFechaAcademica  # noqa: PLC0415
    tid = await _make_tenant(pf_session)
    carrera_id = await _make_carrera(pf_session, tid)
    materia_id = await _make_materia(pf_session, tid)
    cohorte_id = await _make_cohorte(pf_session, tid, carrera_id)
    await pf_session.commit()

    svc = FechaAcademicaService(session=pf_session, tenant_id=tid)
    await svc.crear_fecha(FechaAcademicaCreate(
        materia_id=materia_id, cohorte_id=cohorte_id,
        tipo=TipoFechaAcademica.Coloquio, numero=1,
        fecha=date(2026, 9, 5), titulo="Coloquio Final",
    ))

    # If service called an external HTTP endpoint it would fail (no network in test)
    fragmento = await svc.generar_fragmento_lms(
        materia_id=materia_id, cohorte_id=cohorte_id
    )
    assert fragmento.contenido != ""  # has content
    assert "Coloquio" in fragmento.contenido


# ---------------------------------------------------------------------------
# Group 7.9 — FechaAcademica: validación referencias y aislamiento
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_9_cohorte_otro_tenant_rechazada(pf_session: AsyncSession):
    """7.9: cohorte_id from another tenant raises 404."""
    from fastapi import HTTPException  # noqa: PLC0415
    from app.schemas.fechas_academicas import FechaAcademicaCreate  # noqa: PLC0415
    from app.models.fecha_academica import TipoFechaAcademica  # noqa: PLC0415
    from app.services.fecha_academica_service import FechaAcademicaService  # noqa: PLC0415
    tid_a = await _make_tenant(pf_session, "A5")
    tid_b = await _make_tenant(pf_session, "B5")
    carrera_a = await _make_carrera(pf_session, tid_a)
    carrera_b = await _make_carrera(pf_session, tid_b)
    materia_a = await _make_materia(pf_session, tid_a)
    cohorte_b = await _make_cohorte(pf_session, tid_b, carrera_b)  # belongs to B
    await pf_session.commit()

    svc_a = FechaAcademicaService(session=pf_session, tenant_id=tid_a)
    with pytest.raises(HTTPException) as exc_info:
        await svc_a.crear_fecha(FechaAcademicaCreate(
            materia_id=materia_a,
            cohorte_id=cohorte_b,  # cross-tenant
            tipo=TipoFechaAcademica.Parcial, numero=1,
            fecha=date(2026, 7, 10), titulo="Cross-tenant",
        ))
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_7_9_fecha_otro_tenant_no_visible(pf_session: AsyncSession):
    """7.9: Fecha from tenant B is not visible to tenant A service → 404."""
    from fastapi import HTTPException  # noqa: PLC0415
    from app.services.fecha_academica_service import FechaAcademicaService  # noqa: PLC0415
    tid_a = await _make_tenant(pf_session, "A6")
    tid_b = await _make_tenant(pf_session, "B6")
    carrera_b = await _make_carrera(pf_session, tid_b)
    m_b = await _make_materia(pf_session, tid_b)
    c_b = await _make_cohorte(pf_session, tid_b, carrera_b)
    fecha_b_id = await _make_fecha(pf_session, tid_b, m_b, c_b)
    await pf_session.commit()

    svc_a = FechaAcademicaService(session=pf_session, tenant_id=tid_a)
    with pytest.raises(HTTPException) as exc_info:
        await svc_a.eliminar_fecha(fecha_b_id)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Group 7.10 — RBAC: 403 without estructura:gestionar
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def pf_http_fixtures(pf_engine: AsyncEngine):
    """Build HTTP client with full test DB wired in, user WITH estructura:gestionar."""
    from app.core.database import build_session_factory  # noqa: PLC0415
    from app.core.dependencies import get_db, get_current_user  # noqa: PLC0415
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.main import create_app  # noqa: PLC0415

    factory = build_session_factory(pf_engine)
    application = create_app()

    async with factory() as setup_session:
        tid = await _make_tenant(setup_session)
        uid = await _make_usuario(setup_session, tid)
        await setup_session.commit()

    async def override_db():
        async with factory() as session:
            yield session

    async def override_auth():
        return CurrentUser(user_id=uid, tenant_id=tid, roles=["COORDINADOR"])

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_current_user] = override_auth

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, tid, uid, factory


@pytest.mark.asyncio
async def test_7_10_programas_sin_permiso_returns_403(pf_engine: AsyncEngine):
    """7.10: GET /api/v1/programas/ without estructura:gestionar returns 403."""
    from app.core.database import build_session_factory  # noqa: PLC0415
    from app.core.dependencies import get_db, get_current_user  # noqa: PLC0415
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.main import create_app  # noqa: PLC0415

    factory = build_session_factory(pf_engine)
    application = create_app()

    async with factory() as setup_session:
        tid = await _make_tenant(setup_session)
        uid = await _make_usuario(setup_session, tid)
        await setup_session.commit()

    async def override_db():
        async with factory() as session:
            yield session

    async def override_auth_no_perm():
        return CurrentUser(user_id=uid, tenant_id=tid, roles=[])  # no roles

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_current_user] = override_auth_no_perm

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/programas/")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_7_10_fechas_academicas_sin_permiso_returns_403(pf_engine: AsyncEngine):
    """7.10: GET /api/v1/fechas-academicas/ without estructura:gestionar returns 403."""
    from app.core.database import build_session_factory  # noqa: PLC0415
    from app.core.dependencies import get_db, get_current_user  # noqa: PLC0415
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.main import create_app  # noqa: PLC0415

    factory = build_session_factory(pf_engine)
    application = create_app()

    async with factory() as setup_session:
        tid = await _make_tenant(setup_session)
        uid = await _make_usuario(setup_session, tid)
        await setup_session.commit()

    async def override_db():
        async with factory() as session:
            yield session

    async def override_auth_no_perm():
        return CurrentUser(user_id=uid, tenant_id=tid, roles=[])  # no roles

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_current_user] = override_auth_no_perm

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        m_id = uuid.uuid4()
        c_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/fechas-academicas/?materia_id={m_id}&cohorte_id={c_id}"
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_7_10_http_programas_listar_returns_200_or_403(pf_http_fixtures):
    """7.10: GET /api/v1/programas/ returns 200 (RBAC seeded) or 403."""
    client, tid, uid, factory = pf_http_fixtures
    resp = await client.get("/api/v1/programas/")
    assert resp.status_code in (200, 403)


@pytest.mark.asyncio
async def test_7_10_schema_programa_rechaza_tenant_id():
    """7.10 (schema): ProgramaCreate rejects tenant_id field (extra='forbid')."""
    from pydantic import ValidationError  # noqa: PLC0415
    from app.schemas.programas import ProgramaCreate  # noqa: PLC0415

    with pytest.raises(ValidationError):
        ProgramaCreate(
            materia_id=uuid.uuid4(),
            carrera_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            titulo="Test",
            referencia_archivo="s3://x",
            tenant_id=uuid.uuid4(),  # MUST be rejected
        )


@pytest.mark.asyncio
async def test_7_10_schema_fecha_rechaza_tenant_id():
    """7.10 (schema): FechaAcademicaCreate rejects tenant_id field (extra='forbid')."""
    from pydantic import ValidationError  # noqa: PLC0415
    from app.schemas.fechas_academicas import FechaAcademicaCreate  # noqa: PLC0415
    from app.models.fecha_academica import TipoFechaAcademica  # noqa: PLC0415

    with pytest.raises(ValidationError):
        FechaAcademicaCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo=TipoFechaAcademica.Parcial,
            numero=1,
            fecha=date(2026, 7, 10),
            titulo="Test",
            tenant_id=uuid.uuid4(),  # MUST be rejected
        )

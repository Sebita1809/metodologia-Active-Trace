"""
tests/test_analisis.py — TDD tests for AnalisisService.

Tests:
  Unit tests (no DB — always run):
    - test_atrasados_alumno_sin_calificaciones_es_atrasado (5.1)
    - test_atrasados_alumno_reprobado_es_atrasado (5.2)
    - test_atrasados_alumno_aprobado_no_aparece (5.3)
    - test_atrasados_sin_padron_retorna_lista_vacia (5.4)
    - test_ranking_excluye_alumnos_sin_aprobadas (5.5)
    - test_ranking_vacio_sin_calificaciones (5.6)
    - test_notas_finales_alumno_sin_calificaciones (5.7)
    - test_notas_finales_porcentaje_correcto (5.8)
    - test_reporte_tiene_datos_false_sin_datos (5.9)

  Integration tests (require TEST_DATABASE_URL):
    - test_analisis_rbac_403_sin_permiso (5.10)
    - test_analisis_multitenant_isolation (5.11)
"""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine
from app.schemas.analisis import AtrasadosResponse
from app.services.analisis_service import (
    _compute_atrasados,
    _compute_notas_finales,
    _compute_ranking,
    _compute_reporte,
    get_atrasados,
)

_requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping analisis integration tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Lightweight helpers for unit tests (no DB required)
# ---------------------------------------------------------------------------

def _entrada(nombre: str = "Juan", apellidos: str = "Pérez") -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), nombre=nombre, apellidos=apellidos)


def _cal(
    entrada_padron_id: uuid.UUID,
    actividad: str = "Act1",
    aprobado: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        entrada_padron_id=entrada_padron_id,
        actividad=actividad,
        aprobado=aprobado,
    )


# ---------------------------------------------------------------------------
# Unit tests — no DB required (always run)
# ---------------------------------------------------------------------------

def test_atrasados_alumno_sin_calificaciones_es_atrasado():
    """5.1: Alumno en padrón sin ninguna calificación → atrasado, listas vacías (condición a)."""
    e = _entrada()
    result = _compute_atrasados([e], [])

    assert len(result) == 1
    assert result[0].alumno_id == e.id
    assert result[0].actividades_faltantes == []
    assert result[0].actividades_reprobadas == []


def test_atrasados_alumno_reprobado_es_atrasado():
    """5.2: Alumno con calificación aprobado=False → atrasado con la actividad reprobada (condición b)."""
    e = _entrada()
    c = _cal(e.id, actividad="Tarea1", aprobado=False)
    result = _compute_atrasados([e], [c])

    assert len(result) == 1
    assert result[0].actividades_reprobadas == ["Tarea1"]
    assert result[0].actividades_faltantes == []


def test_atrasados_alumno_aprobado_no_aparece():
    """5.3: Alumno con todas las actividades aprobadas no aparece en atrasados."""
    e = _entrada()
    c = _cal(e.id, actividad="Tarea1", aprobado=True)
    result = _compute_atrasados([e], [c])

    assert result == []


@pytest.mark.asyncio
async def test_atrasados_sin_padron_retorna_lista_vacia():
    """5.4: Sin padrón activo → AtrasadosResponse(atrasados=[], sin_padron=True)."""
    with patch(
        "app.services.analisis_service._get_entradas_activas",
        new=AsyncMock(return_value=[]),
    ):
        result = await get_atrasados(uuid.uuid4(), AsyncMock(), uuid.uuid4())

    assert isinstance(result, AtrasadosResponse)
    assert result.atrasados == []
    assert result.sin_padron is True


def test_ranking_excluye_alumnos_sin_aprobadas():
    """5.5: Ranking excluye alumnos con 0 aprobadas (RN-09); ordena de mayor a menor."""
    e_a = _entrada("Ana", "Lopez")
    e_b = _entrada("Bob", "Smith")

    cals = [
        _cal(e_a.id, "Act1", aprobado=True),
        _cal(e_a.id, "Act2", aprobado=True),
        _cal(e_b.id, "Act3", aprobado=False),
    ]
    result = _compute_ranking([e_a, e_b], cals)

    assert len(result) == 1
    assert result[0].alumno_id == e_a.id
    assert result[0].aprobadas == 2


def test_ranking_vacio_sin_calificaciones():
    """5.6: Sin calificaciones importadas → ranking vacío."""
    e = _entrada()
    result = _compute_ranking([e], [])

    assert result == []


def test_notas_finales_alumno_sin_calificaciones():
    """5.7: Alumno en padrón sin calificaciones → aprobadas=0, total=0, pct=0.0."""
    e = _entrada()
    result = _compute_notas_finales([e], [])

    assert len(result) == 1
    assert result[0].aprobadas == 0
    assert result[0].total_actividades == 0
    assert result[0].porcentaje_aprobacion == 0.0


def test_notas_finales_porcentaje_correcto():
    """5.8: 2 aprobadas de 3 calificaciones → porcentaje ≈ 66.67."""
    e = _entrada()
    cals = [
        _cal(e.id, "Act1", aprobado=True),
        _cal(e.id, "Act2", aprobado=True),
        _cal(e.id, "Act3", aprobado=False),
    ]
    result = _compute_notas_finales([e], cals)

    assert len(result) == 1
    assert result[0].aprobadas == 2
    assert result[0].total_actividades == 3
    assert abs(result[0].porcentaje_aprobacion - 66.666) < 0.01


def test_reporte_tiene_datos_false_sin_datos():
    """5.9: Sin calificaciones ni padrón → tiene_datos=False, todos los contadores en cero."""
    result = _compute_reporte([], [])

    assert result.tiene_datos is False
    assert result.total_alumnos == 0
    assert result.total_atrasados == 0
    assert result.pct_aprobacion_general == 0.0
    assert result.total_actividades == 0


# ---------------------------------------------------------------------------
# Integration test fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def analisis_engine() -> AsyncEngine:
    """Create a full schema engine for analisis tests."""
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
    import app.models.umbral_materia  # noqa: F401
    import app.models.calificacion    # noqa: F401
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
async def analisis_session(analisis_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(analisis_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# DB helpers (reusing pattern from test_calificaciones.py)
# ---------------------------------------------------------------------------

async def _make_tenant(session: AsyncSession, suffix: str = "") -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=f"ana-{uuid.uuid4().hex[:8]}{suffix}", nombre="Analisis Test", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_materia(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(tenant_id=tid, codigo=f"MAT_{uuid.uuid4().hex[:6]}", nombre="Mat Test")
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


async def _make_cohorte(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.models.cohorte import Cohorte  # noqa: PLC0415
    c = Carrera(tenant_id=tid, codigo=f"CAR_{uuid.uuid4().hex[:6]}", nombre="Car")
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


async def _make_usuario(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.models.usuario import Usuario  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    email = f"usr_{uuid.uuid4().hex[:8]}@test.com"
    u = Usuario(
        tenant_id=tid, nombre="Test", apellidos="User",
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


async def _make_asignacion(
    session: AsyncSession,
    tid: uuid.UUID,
    usuario_id: uuid.UUID,
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
) -> uuid.UUID:
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    a = Asignacion(
        tenant_id=tid, usuario_id=usuario_id, rol="PROFESOR",
        materia_id=materia_id, cohorte_id=cohorte_id, desde=date.today(),
    )
    session.add(a)
    await session.flush()
    await session.refresh(a)
    return a.id


async def _make_version_padron(
    session: AsyncSession,
    tid: uuid.UUID,
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> uuid.UUID:
    from app.models.version_padron import VersionPadron  # noqa: PLC0415
    v = VersionPadron(
        tenant_id=tid, materia_id=materia_id, cohorte_id=cohorte_id,
        cargado_por=usuario_id, cargado_at=datetime.now(tz=timezone.utc),
        activa=True, origen="archivo",
    )
    session.add(v)
    await session.flush()
    await session.refresh(v)
    return v.id


async def _make_entrada(
    session: AsyncSession,
    tid: uuid.UUID,
    version_id: uuid.UUID,
    nombre: str = "Alumno",
    apellidos: str = "Test",
) -> uuid.UUID:
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.models.entrada_padron import EntradaPadron  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    email = f"{uuid.uuid4().hex[:8]}@test.com"
    e = EntradaPadron(
        tenant_id=tid, version_id=version_id,
        nombre=nombre, apellidos=apellidos,
        email=crypto.encrypt(email),
    )
    session.add(e)
    await session.flush()
    await session.refresh(e)
    return e.id


async def _make_calificacion(
    session: AsyncSession,
    tid: uuid.UUID,
    entrada_id: uuid.UUID,
    materia_id: uuid.UUID,
    actividad: str = "Act1",
    aprobado: bool = True,
) -> None:
    from app.models.calificacion import Calificacion  # noqa: PLC0415
    c = Calificacion(
        tenant_id=tid, entrada_padron_id=entrada_id, materia_id=materia_id,
        actividad=actividad, nota_numerica=80 if aprobado else 40,
        aprobado=aprobado, origen="Importado",
        importado_at=datetime.now(tz=timezone.utc),
    )
    session.add(c)
    await session.flush()


# ---------------------------------------------------------------------------
# Integration test: RBAC — 403 en los 4 endpoints sin permiso (5.10)
# ---------------------------------------------------------------------------

@_requires_db
def test_analisis_rbac_403_sin_permiso(app_instance):
    """5.10: Los 4 endpoints de analisis retornan 401/403 sin token de autenticación."""
    import asyncio  # noqa: PLC0415
    from httpx import ASGITransport, AsyncClient  # noqa: PLC0415

    asignacion_id = str(uuid.uuid4())
    endpoints = [
        f"/api/v1/analisis/atrasados?asignacion_id={asignacion_id}",
        f"/api/v1/analisis/ranking?asignacion_id={asignacion_id}",
        f"/api/v1/analisis/notas-finales?asignacion_id={asignacion_id}",
        f"/api/v1/analisis/reporte?asignacion_id={asignacion_id}",
    ]

    async def _run():
        transport = ASGITransport(app=app_instance)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for path in endpoints:
                resp = await client.get(path)
                assert resp.status_code in (401, 403), (
                    f"Expected 401/403 for {path}, got {resp.status_code}"
                )

    asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# Integration test: multi-tenant isolation (5.11)
# ---------------------------------------------------------------------------

@_requires_db
async def test_analisis_multitenant_isolation(analisis_session: AsyncSession):
    """5.11: Datos de tenant A no aparecen en ningún endpoint cuando se consulta con tenant B."""
    # -- Setup tenant A with full data --
    tid_a = await _make_tenant(analisis_session, "_A")
    tid_b = await _make_tenant(analisis_session, "_B")
    uid_a = await _make_usuario(analisis_session, tid_a)
    mat_a = await _make_materia(analisis_session, tid_a)
    coh_a = await _make_cohorte(analisis_session, tid_a)
    asig_a = await _make_asignacion(analisis_session, tid_a, uid_a, mat_a, coh_a)
    ver_a = await _make_version_padron(analisis_session, tid_a, mat_a, coh_a, uid_a)
    entrada_a = await _make_entrada(analisis_session, tid_a, ver_a)
    await _make_calificacion(analisis_session, tid_a, entrada_a, mat_a, "Act1", aprobado=False)
    await analisis_session.commit()

    # -- Query analisis with tenant B's scope for tenant A's asignacion --
    atrasados = await get_atrasados(asig_a, analisis_session, tid_b)
    assert atrasados.atrasados == [], "Tenant B should not see Tenant A's atrasados"
    assert atrasados.sin_padron is True, "asignacion_id from A is invisible to tenant B"

    from app.services.analisis_service import get_ranking, get_notas_finales, get_reporte  # noqa: PLC0415
    ranking = await get_ranking(asig_a, analisis_session, tid_b)
    assert ranking.items == [], "Tenant B should not see Tenant A's ranking"

    notas = await get_notas_finales(asig_a, analisis_session, tid_b)
    assert notas.items == [], "Tenant B should not see Tenant A's notas finales"

    reporte = await get_reporte(asig_a, analisis_session, tid_b)
    assert reporte.total_alumnos == 0, "Tenant B should not see Tenant A's reporte"
    assert reporte.tiene_datos is False

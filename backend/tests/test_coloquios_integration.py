"""
tests/test_coloquios_integration.py — Integration tests for C-14 evaluaciones/coloquios.

All tests require TEST_DATABASE_URL and are skipped when not set.

Tests:
  T7.1  — crear evaluacion persiste con estado='Activa'
  T7.2  — listar evaluaciones retorna cupos_libres_hoy correcto
  T7.3  — metricas_panel retorna 4 contadores correctos
  T7.4  — reservar crea reserva con alumno_id del JWT
  T7.5  — reservar rechaza cupo excedido
  T7.6  — reservar rechaza duplicado activo mismo alumno
  T7.7  — cancelar Activa → Cancelada, solo owner
  T7.8  — cancelar rechaza si no es owner
  T7.9  — registrar resultado persiste correctamente
  T7.10 — registrar resultado duplicado retorna LookupError
  T7.11 — multitenant: evaluacion de tenant A invisible para tenant B
  T7.12 — RBAC: endpoints retornan 401/403 sin token
  T7.13 — migration test: tables exist with correct columns
"""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine

_requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping coloquios integration tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Schema fixture — creates all tables including new C-14 ones
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


@pytest_asyncio.fixture
async def coloquios_engine() -> AsyncEngine:
    """Engine with full C-14 schema."""
    # Register all models
    import app.models.tenant              # noqa: F401
    import app.models.user                # noqa: F401
    import app.models.rol                 # noqa: F401
    import app.models.permiso             # noqa: F401
    import app.models.rol_permiso         # noqa: F401
    import app.models.usuario_rol         # noqa: F401
    import app.models.audit_log           # noqa: F401
    import app.models.carrera             # noqa: F401
    import app.models.cohorte             # noqa: F401
    import app.models.materia             # noqa: F401
    import app.models.usuario             # noqa: F401
    import app.models.asignacion          # noqa: F401
    import app.models.version_padron      # noqa: F401
    import app.models.entrada_padron      # noqa: F401
    import app.models.umbral_materia      # noqa: F401
    import app.models.calificacion        # noqa: F401
    import app.models.evaluacion          # noqa: F401
    import app.models.reserva_evaluacion  # noqa: F401
    import app.models.resultado_evaluacion  # noqa: F401
    import app.features.auth.models       # noqa: F401

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
async def col_session(coloquios_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(coloquios_engine, expire_on_commit=False)
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

    t = Tenant(slug=f"col-{uuid.uuid4().hex[:8]}", nombre="Coloquios Test", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_materia(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415

    m = Materia(tenant_id=tid, codigo=f"MAT_{uuid.uuid4().hex[:6]}", nombre="Materia Test")
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


async def _make_cohorte(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.models.cohorte import Cohorte  # noqa: PLC0415

    c = Carrera(tenant_id=tid, codigo=f"CAR_{uuid.uuid4().hex[:6]}", nombre="Carrera")
    session.add(c)
    await session.flush()
    await session.refresh(c)
    cohorte = Cohorte(
        tenant_id=tid,
        carrera_id=c.id,
        nombre=f"COH_{uuid.uuid4().hex[:6]}",
        anio=2026,
        vig_desde=date.today(),
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
        tenant_id=tid,
        nombre="Test",
        apellidos="Alumno",
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


async def _make_evaluacion(
    session: AsyncSession,
    tid: uuid.UUID,
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    cupo_por_dia: int = 5,
    tipo: str = "Coloquio",
) -> uuid.UUID:
    from app.models.evaluacion import Evaluacion  # noqa: PLC0415

    ev = Evaluacion(
        tenant_id=tid,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        tipo=tipo,
        estado="Activa",
        instancia="Coloquio Feb 2026",
        dias_disponibles=5,
        cupo_por_dia=cupo_por_dia,
    )
    session.add(ev)
    await session.flush()
    await session.refresh(ev)
    return ev.id


async def _make_reserva(
    session: AsyncSession,
    tid: uuid.UUID,
    evaluacion_id: uuid.UUID,
    alumno_id: uuid.UUID,
    fecha_hora: datetime | None = None,
    estado: str = "Activa",
) -> uuid.UUID:
    from app.models.reserva_evaluacion import ReservaEvaluacion  # noqa: PLC0415

    if fecha_hora is None:
        fecha_hora = datetime.now(tz=timezone.utc)
    r = ReservaEvaluacion(
        tenant_id=tid,
        evaluacion_id=evaluacion_id,
        alumno_id=alumno_id,
        fecha_hora=fecha_hora,
        estado=estado,
    )
    session.add(r)
    await session.flush()
    await session.refresh(r)
    return r.id


# ---------------------------------------------------------------------------
# T7.1: crear evaluacion persiste con estado='Activa'
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_crear_evaluacion_estado_activa(col_session: AsyncSession):
    """T7.1: EvaluacionService.crear() returns EvaluacionRead with estado='Activa'."""
    from app.schemas.coloquios import EvaluacionCreate  # noqa: PLC0415
    from app.services.evaluacion_service import EvaluacionService  # noqa: PLC0415

    tid = await _make_tenant(col_session)
    materia_id = await _make_materia(col_session, tid)
    cohorte_id = await _make_cohorte(col_session, tid)
    await col_session.commit()

    svc = EvaluacionService(session=col_session, tenant_id=tid)
    body = EvaluacionCreate(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        tipo="Coloquio",
        instancia="Febrero 2026",
        dias_disponibles=5,
        cupo_por_dia=10,
    )
    result = await svc.crear(body)

    assert result.estado == "Activa"
    assert result.tipo == "Coloquio"
    assert result.tenant_id == tid
    assert result.materia_id == materia_id
    assert result.cupo_por_dia == 10


# ---------------------------------------------------------------------------
# T7.2: listar evaluaciones retorna cupos_libres_hoy correcto
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_listar_con_metricas_cupos_libres(col_session: AsyncSession):
    """T7.2: listar_con_metricas returns cupos_libres_hoy = cupo - reservas_hoy."""
    from app.services.evaluacion_service import EvaluacionService  # noqa: PLC0415

    tid = await _make_tenant(col_session)
    mat = await _make_materia(col_session, tid)
    coh = await _make_cohorte(col_session, tid)
    uid = await _make_usuario(col_session, tid)
    ev_id = await _make_evaluacion(col_session, tid, mat, coh, cupo_por_dia=5)

    # Add one reservation for today
    today_noon = datetime.now(tz=timezone.utc).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    await _make_reserva(col_session, tid, ev_id, uid, fecha_hora=today_noon)
    await col_session.commit()

    svc = EvaluacionService(session=col_session, tenant_id=tid)
    result = await svc.listar_con_metricas()

    assert len(result) == 1
    assert result[0].cupos_libres_hoy == 4  # 5 - 1 = 4


# ---------------------------------------------------------------------------
# T7.3: metricas_panel retorna 4 contadores correctos
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_metricas_panel(col_session: AsyncSession):
    """T7.3: metricas_panel returns correct counters."""
    from app.models.evaluacion import Evaluacion  # noqa: PLC0415
    from app.services.evaluacion_service import EvaluacionService  # noqa: PLC0415

    tid = await _make_tenant(col_session)
    mat = await _make_materia(col_session, tid)
    coh = await _make_cohorte(col_session, tid)
    uid = await _make_usuario(col_session, tid)
    ev_id = await _make_evaluacion(col_session, tid, mat, coh)
    await _make_reserva(col_session, tid, ev_id, uid)

    # Soft-close one evaluacion (create another and mark it cerrada)
    ev2 = Evaluacion(
        tenant_id=tid,
        materia_id=mat,
        cohorte_id=coh,
        tipo="Parcial",
        estado="Cerrada",
        instancia="Primer Parcial",
        dias_disponibles=3,
        cupo_por_dia=5,
    )
    col_session.add(ev2)
    await col_session.flush()
    await col_session.commit()

    svc = EvaluacionService(session=col_session, tenant_id=tid)
    metrics = await svc.metricas_panel()

    assert metrics.total_evaluaciones == 2
    assert metrics.evaluaciones_cerradas == 1
    assert metrics.total_reservas_activas == 1
    assert metrics.total_resultados == 0


# ---------------------------------------------------------------------------
# T7.4: reservar crea reserva con alumno_id del JWT (no del body)
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_reservar_usa_alumno_id_del_jwt(col_session: AsyncSession):
    """T7.4: reservar() creates a reserva with alumno_id = current_user.user_id (JWT)."""
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.schemas.coloquios import ReservarRequest  # noqa: PLC0415
    from app.services.reserva_service import ReservaService  # noqa: PLC0415

    tid = await _make_tenant(col_session)
    mat = await _make_materia(col_session, tid)
    coh = await _make_cohorte(col_session, tid)
    uid = await _make_usuario(col_session, tid)
    ev_id = await _make_evaluacion(col_session, tid, mat, coh)
    await col_session.commit()

    current_user = CurrentUser(
        user_id=uid,
        tenant_id=tid,
        roles=["ALUMNO"],
    )
    fecha_hora = datetime.now(tz=timezone.utc).replace(
        hour=14, minute=0, second=0, microsecond=0
    )
    body = ReservarRequest(fecha_hora=fecha_hora)

    svc = ReservaService(session=col_session, tenant_id=tid)
    result = await svc.reservar(ev_id, body, current_user)

    assert result.alumno_id == uid  # identity from JWT, not from body
    assert result.evaluacion_id == ev_id
    assert result.estado == "Activa"


# ---------------------------------------------------------------------------
# T7.5: reservar rechaza cupo excedido
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_reservar_rechaza_cupo_excedido(col_session: AsyncSession):
    """T7.5: reservar() raises ValueError when cupo_por_dia is exceeded."""
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.schemas.coloquios import ReservarRequest  # noqa: PLC0415
    from app.services.reserva_service import ReservaService  # noqa: PLC0415

    tid = await _make_tenant(col_session)
    mat = await _make_materia(col_session, tid)
    coh = await _make_cohorte(col_session, tid)
    uid = await _make_usuario(col_session, tid)
    uid2 = await _make_usuario(col_session, tid)
    uid3 = await _make_usuario(col_session, tid)

    # Evaluacion with cupo_por_dia=2
    ev_id = await _make_evaluacion(col_session, tid, mat, coh, cupo_por_dia=2)

    today_noon = datetime.now(tz=timezone.utc).replace(
        hour=10, minute=0, second=0, microsecond=0
    )

    # Fill the cupo (2 reservas for today)
    await _make_reserva(col_session, tid, ev_id, uid, fecha_hora=today_noon)
    await _make_reserva(col_session, tid, ev_id, uid2, fecha_hora=today_noon)
    await col_session.commit()

    # Third alumno tries to reserve — should fail
    cu3 = CurrentUser(user_id=uid3, tenant_id=tid, roles=["ALUMNO"])
    body = ReservarRequest(fecha_hora=today_noon)
    svc = ReservaService(session=col_session, tenant_id=tid)

    with pytest.raises(ValueError, match="Sin cupo"):
        await svc.reservar(ev_id, body, cu3)


# ---------------------------------------------------------------------------
# T7.6: reservar rechaza duplicado activo mismo alumno
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_reservar_rechaza_duplicado_activo(col_session: AsyncSession):
    """T7.6: reservar() raises ValueError when alumno already has an active reservation."""
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.schemas.coloquios import ReservarRequest  # noqa: PLC0415
    from app.services.reserva_service import ReservaService  # noqa: PLC0415

    tid = await _make_tenant(col_session)
    mat = await _make_materia(col_session, tid)
    coh = await _make_cohorte(col_session, tid)
    uid = await _make_usuario(col_session, tid)
    ev_id = await _make_evaluacion(col_session, tid, mat, coh, cupo_por_dia=10)
    await col_session.commit()

    cu = CurrentUser(user_id=uid, tenant_id=tid, roles=["ALUMNO"])
    fecha_hora = datetime.now(tz=timezone.utc).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    body = ReservarRequest(fecha_hora=fecha_hora)

    svc = ReservaService(session=col_session, tenant_id=tid)

    # First reservation succeeds
    await svc.reservar(ev_id, body, cu)
    await col_session.commit()

    # Second reservation by same alumno should fail
    with pytest.raises(ValueError, match="reserva activa"):
        await svc.reservar(ev_id, body, cu)


# ---------------------------------------------------------------------------
# T7.7: cancelar Activa → Cancelada, solo owner
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_cancelar_reserva_propia(col_session: AsyncSession):
    """T7.7: cancelar() transitions estado Activa → Cancelada for the owner."""
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.services.reserva_service import ReservaService  # noqa: PLC0415

    tid = await _make_tenant(col_session)
    mat = await _make_materia(col_session, tid)
    coh = await _make_cohorte(col_session, tid)
    uid = await _make_usuario(col_session, tid)
    ev_id = await _make_evaluacion(col_session, tid, mat, coh)
    reserva_id = await _make_reserva(col_session, tid, ev_id, uid)
    await col_session.commit()

    cu = CurrentUser(user_id=uid, tenant_id=tid, roles=["ALUMNO"])
    svc = ReservaService(session=col_session, tenant_id=tid)

    result = await svc.cancelar(ev_id, reserva_id, cu)
    assert result is True

    # Verify estado was changed
    from app.repositories.reserva_evaluacion_repository import ReservaEvaluacionRepository  # noqa: PLC0415
    repo = ReservaEvaluacionRepository(session=col_session, tenant_id=tid)
    # The base get() filters deleted_at IS NULL but not by estado — use raw check
    stmt = sa.select(sa.text("estado")).select_from(sa.text("reserva_evaluacion")).where(
        sa.text(f"id = '{reserva_id}'")
    )
    estado_result = await col_session.execute(stmt)
    estado = estado_result.scalar_one()
    assert estado == "Cancelada"


# ---------------------------------------------------------------------------
# T7.8: cancelar rechaza si no es owner
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_cancelar_rechaza_no_owner(col_session: AsyncSession):
    """T7.8: cancelar() raises ValueError when a different alumno tries to cancel."""
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.services.reserva_service import ReservaService  # noqa: PLC0415

    tid = await _make_tenant(col_session)
    mat = await _make_materia(col_session, tid)
    coh = await _make_cohorte(col_session, tid)
    uid_owner = await _make_usuario(col_session, tid)
    uid_other = await _make_usuario(col_session, tid)
    ev_id = await _make_evaluacion(col_session, tid, mat, coh)
    reserva_id = await _make_reserva(col_session, tid, ev_id, uid_owner)
    await col_session.commit()

    # Different user tries to cancel
    cu_other = CurrentUser(user_id=uid_other, tenant_id=tid, roles=["ALUMNO"])
    svc = ReservaService(session=col_session, tenant_id=tid)

    with pytest.raises(ValueError, match="propias"):
        await svc.cancelar(ev_id, reserva_id, cu_other)


# ---------------------------------------------------------------------------
# T7.9: registrar resultado persiste correctamente
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_registrar_resultado(col_session: AsyncSession):
    """T7.9: ResultadoService.registrar() persists the resultado correctly."""
    from app.schemas.coloquios import RegistrarResultadoRequest  # noqa: PLC0415
    from app.services.resultado_service import ResultadoService  # noqa: PLC0415

    tid = await _make_tenant(col_session)
    mat = await _make_materia(col_session, tid)
    coh = await _make_cohorte(col_session, tid)
    uid = await _make_usuario(col_session, tid)
    ev_id = await _make_evaluacion(col_session, tid, mat, coh)
    await col_session.commit()

    svc = ResultadoService(session=col_session, tenant_id=tid)
    body = RegistrarResultadoRequest(alumno_id=uid, nota_final="8")
    result = await svc.registrar(ev_id, body)

    assert result.alumno_id == uid
    assert result.evaluacion_id == ev_id
    assert result.nota_final == "8"
    assert result.tenant_id == tid


# ---------------------------------------------------------------------------
# T7.10: registrar resultado duplicado → LookupError
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_registrar_resultado_duplicado_retorna_lookup_error(col_session: AsyncSession):
    """T7.10: registrar() raises LookupError on duplicate (evaluacion, alumno)."""
    from app.schemas.coloquios import RegistrarResultadoRequest  # noqa: PLC0415
    from app.services.resultado_service import ResultadoService  # noqa: PLC0415

    tid = await _make_tenant(col_session)
    mat = await _make_materia(col_session, tid)
    coh = await _make_cohorte(col_session, tid)
    uid = await _make_usuario(col_session, tid)
    ev_id = await _make_evaluacion(col_session, tid, mat, coh)
    await col_session.commit()

    svc = ResultadoService(session=col_session, tenant_id=tid)
    body = RegistrarResultadoRequest(alumno_id=uid, nota_final="8")

    # First registration succeeds
    await svc.registrar(ev_id, body)
    await col_session.commit()

    # Second registration should fail
    with pytest.raises(LookupError, match="Ya existe"):
        await svc.registrar(ev_id, body)


# ---------------------------------------------------------------------------
# T7.11: multitenant isolation
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_multitenant_isolation(col_session: AsyncSession):
    """T7.11: Evaluaciones from tenant A are invisible to tenant B."""
    from app.services.evaluacion_service import EvaluacionService  # noqa: PLC0415

    tid_a = await _make_tenant(col_session)
    tid_b = await _make_tenant(col_session)

    mat_a = await _make_materia(col_session, tid_a)
    coh_a = await _make_cohorte(col_session, tid_a)
    await _make_evaluacion(col_session, tid_a, mat_a, coh_a)
    await col_session.commit()

    # Tenant B sees nothing
    svc_b = EvaluacionService(session=col_session, tenant_id=tid_b)
    result = await svc_b.listar_con_metricas()
    assert result == [], "Tenant B should not see Tenant A's evaluaciones"

    metrics_b = await svc_b.metricas_panel()
    assert metrics_b.total_evaluaciones == 0


# ---------------------------------------------------------------------------
# T7.12: RBAC — endpoints return 401/403 without auth token
# ---------------------------------------------------------------------------

@_requires_db
def test_coloquios_rbac_requires_auth(app_instance):
    """T7.12: All coloquios endpoints return 401 without auth token."""
    import asyncio  # noqa: PLC0415
    from httpx import ASGITransport, AsyncClient  # noqa: PLC0415

    ev_id = str(uuid.uuid4())
    res_id = str(uuid.uuid4())
    endpoints_and_methods = [
        ("POST", "/api/v1/coloquios/"),
        ("GET", "/api/v1/coloquios/"),
        ("GET", "/api/v1/coloquios/metricas"),
        ("POST", f"/api/v1/coloquios/{ev_id}/alumnos"),
        ("POST", f"/api/v1/coloquios/{ev_id}/reservas"),
        ("DELETE", f"/api/v1/coloquios/{ev_id}/reservas/{res_id}"),
        ("GET", f"/api/v1/coloquios/{ev_id}/reservas"),
        ("POST", f"/api/v1/coloquios/{ev_id}/resultados"),
        ("GET", f"/api/v1/coloquios/{ev_id}/resultados"),
    ]

    async def _run():
        transport = ASGITransport(app=app_instance)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for method, path in endpoints_and_methods:
                resp = await client.request(method, path, json={})
                assert resp.status_code in (401, 403, 422), (
                    f"Expected 401/403/422 for {method} {path}, got {resp.status_code}"
                )

    asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# T7.13: Migration structure — tables exist with correct columns
# ---------------------------------------------------------------------------

@_requires_db
@pytest.mark.asyncio
async def test_coloquios_tables_exist(col_session: AsyncSession):
    """T7.13: evaluacion, reserva_evaluacion, resultado_evaluacion tables exist."""
    from sqlalchemy import inspect  # noqa: PLC0415

    # Use raw inspect to verify table structure
    tables_expected = {
        "evaluacion": {
            "materia_id", "cohorte_id", "tipo", "estado",
            "instancia", "dias_disponibles", "cupo_por_dia"
        },
        "reserva_evaluacion": {
            "evaluacion_id", "alumno_id", "fecha_hora", "estado"
        },
        "resultado_evaluacion": {
            "evaluacion_id", "alumno_id", "nota_final"
        },
    }

    for table_name, expected_cols in tables_expected.items():
        result = await col_session.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :t"
            ),
            {"t": table_name},
        )
        actual_cols = {row[0] for row in result}
        missing = expected_cols - actual_cols
        assert not missing, (
            f"Table '{table_name}' missing columns: {missing}"
        )

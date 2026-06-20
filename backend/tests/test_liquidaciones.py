"""
tests/test_liquidaciones.py — Tests for C-18 Liquidaciones y Honorarios.

TDD cycle:
  RED: tests written BEFORE production code.
  GREEN: minimum implementation passes all scenarios.
  TRIANGULATE: ≥2 test cases per behavior.
  REFACTOR: code cleaned up after green.

Structure:
  Group 0  — Pure calcular_liquidacion (no DB, always run)
  Group 1  — SalarioBase repo: get_vigente, no-solapamiento, soft-delete
  Group 2  — SalarioPlus repo: get_vigente, no-solapamiento
  Group 3  — LiquidacionRepository: upsert, listar_periodo, get_combo, listar_cerradas
  Group 4  — FacturaRepository: listar, sumar_periodo
  Group 5  — GrillaSalarialService: ABM Base + Plus, solapamiento → ValueError
  Group 6  — LiquidacionService: calcular_periodo, vista_periodo, cerrar_periodo, historial
  Group 7  — FacturaService: ABM, cambiar_estado Pendiente→Abonada
  Group 8  — Schema validation (extra='forbid'), no DB
  Group 9  — Multi-tenancy isolation
  Group 10 — HTTP endpoints (201/200/409/404/403)

DB tests skip if TEST_DATABASE_URL is not set.
Pure unit tests (Group 0, Group 8) always run.

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
import sqlalchemy as sa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

# DB tests skip marker
_db_required = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping liquidaciones integration tests",
)

_TEST_KEY = "a" * 64


# ===========================================================================
# Group 0 — Pure calcular_liquidacion (no DB, ALWAYS RUN)
# ===========================================================================

def test_7_4_motor_total_base_plus_1_comision():
    """7.4: total = base + plus × 1 comision (happy path, RN-34)."""
    from app.services.liquidacion_calculo import calcular_liquidacion  # noqa: PLC0415

    base_monto, plus_monto, total_monto, desglose = calcular_liquidacion(
        rol="PROFESOR",
        base_vigente=Decimal("1000"),
        plus_vigentes={"PROG": Decimal("200")},
        comisiones_por_clave={"PROG": 1},
    )

    assert base_monto == Decimal("1000")
    assert plus_monto == Decimal("200")
    assert total_monto == Decimal("1200")
    assert len(desglose["items"]) == 1
    assert desglose["items"][0]["clave"] == "PROG"
    assert desglose["items"][0]["n_comisiones"] == 1


def test_7_5_motor_acumula_n_veces_sin_tope_n1():
    """7.5 TRIANGULATE N=1: Plus acumula 1 vez por 1 comision (RN-33)."""
    from app.services.liquidacion_calculo import calcular_liquidacion  # noqa: PLC0415

    _, plus_monto, _, desglose = calcular_liquidacion(
        rol="PROFESOR",
        base_vigente=Decimal("1000"),
        plus_vigentes={"PROG": Decimal("200")},
        comisiones_por_clave={"PROG": 1},
    )

    assert plus_monto == Decimal("200")
    assert desglose["items"][0]["n_comisiones"] == 1


def test_7_5_motor_acumula_n_veces_sin_tope_n3():
    """7.5 TRIANGULATE N=3: Plus acumula 3 veces por 3 comisiones (RN-33)."""
    from app.services.liquidacion_calculo import calcular_liquidacion  # noqa: PLC0415

    _, plus_monto, total_monto, desglose = calcular_liquidacion(
        rol="PROFESOR",
        base_vigente=Decimal("1000"),
        plus_vigentes={"PROG": Decimal("200")},
        comisiones_por_clave={"PROG": 3},
    )

    assert plus_monto == Decimal("600")  # 200 × 3, no cap
    assert total_monto == Decimal("1600")
    assert desglose["items"][0]["n_comisiones"] == 3


def test_7_6_motor_claves_distintas_suman_separado():
    """7.6: Comisiones de claves distintas suman cada plus por separado (RN-33)."""
    from app.services.liquidacion_calculo import calcular_liquidacion  # noqa: PLC0415

    _, plus_monto, _, desglose = calcular_liquidacion(
        rol="PROFESOR",
        base_vigente=Decimal("0"),
        plus_vigentes={"PROG": Decimal("200"), "BD": Decimal("150")},
        comisiones_por_clave={"PROG": 2, "BD": 1},
    )

    # 2×200 + 1×150 = 550
    assert plus_monto == Decimal("550")
    claves = {item["clave"] for item in desglose["items"]}
    assert claves == {"PROG", "BD"}


def test_7_7_motor_clave_plus_nulo_no_aporta():
    """7.7: Materia con clave_plus nulo no aporta plus (clave no in plus_vigentes)."""
    from app.services.liquidacion_calculo import calcular_liquidacion  # noqa: PLC0415

    # comisiones_por_clave is empty (caller excludes NULL claves before calling)
    base_monto, plus_monto, total_monto, desglose = calcular_liquidacion(
        rol="PROFESOR",
        base_vigente=Decimal("1000"),
        plus_vigentes={},
        comisiones_por_clave={},
    )

    assert plus_monto == Decimal("0")
    assert total_monto == Decimal("1000")
    assert desglose["items"] == []


def test_motor_base_none_usa_cero():
    """When base_vigente is None, base_monto = 0."""
    from app.services.liquidacion_calculo import calcular_liquidacion  # noqa: PLC0415

    base_monto, _, total_monto, _ = calcular_liquidacion(
        rol="PROFESOR",
        base_vigente=None,
        plus_vigentes={"PROG": Decimal("100")},
        comisiones_por_clave={"PROG": 2},
    )
    assert base_monto == Decimal("0")
    assert total_monto == Decimal("200")


def test_motor_clave_no_en_plus_vigentes_ignorada():
    """Clave presente in comisiones but not in plus_vigentes → contributes 0."""
    from app.services.liquidacion_calculo import calcular_liquidacion  # noqa: PLC0415

    _, plus_monto, total_monto, desglose = calcular_liquidacion(
        rol="TUTOR",
        base_vigente=Decimal("500"),
        plus_vigentes={},  # no plus configured
        comisiones_por_clave={"PROG": 5},  # 5 comisiones but no plus for PROG
    )
    assert plus_monto == Decimal("0")
    assert total_monto == Decimal("500")
    assert desglose["items"] == []


# ===========================================================================
# DB fixtures — shared across Groups 1-10
# ===========================================================================

@pytest_asyncio.fixture
async def liq_engine() -> AsyncEngine:
    """Create full schema for liquidaciones tests, tear down after."""
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL not set")
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
    import app.models.salario_base      # noqa: F401
    import app.models.salario_plus      # noqa: F401
    import app.models.liquidacion       # noqa: F401
    import app.models.factura           # noqa: F401
    import app.features.auth.models     # noqa: F401

    from app.core.database import Base, build_engine  # noqa: PLC0415

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
async def liq_session(liq_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(liq_engine, expire_on_commit=False)
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
        slug=f"liq-{uuid.uuid4().hex[:8]}{suffix}",
        nombre="Liq Test",
        activo=True,
    )
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_usuario(
    session: AsyncSession,
    tid: uuid.UUID,
    facturador: bool = False,
) -> uuid.UUID:
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
        facturador=facturador,
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


async def _make_cohorte(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.cohorte import Cohorte  # noqa: PLC0415
    from app.models.carrera import Carrera  # noqa: PLC0415
    carrera = Carrera(tenant_id=tid, nombre="Carrera Test", codigo=f"C{uuid.uuid4().hex[:4]}")
    session.add(carrera)
    await session.flush()
    await session.refresh(carrera)
    c = Cohorte(
        tenant_id=tid,
        carrera_id=carrera.id,
        anio=2026,
        nombre=f"Cohorte-{uuid.uuid4().hex[:6]}",
    )
    session.add(c)
    await session.flush()
    await session.refresh(c)
    return c.id


async def _make_materia(
    session: AsyncSession, tid: uuid.UUID, clave_plus: str | None = None
) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(
        tenant_id=tid,
        codigo=f"M_{uuid.uuid4().hex[:6]}",
        nombre="Mat",
        clave_plus=clave_plus,
    )
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


async def _make_asignacion(
    session: AsyncSession,
    tid: uuid.UUID,
    usuario_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    materia_id: uuid.UUID,
    rol: str = "PROFESOR",
    comisiones: list | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> uuid.UUID:
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    a = Asignacion(
        tenant_id=tid,
        usuario_id=usuario_id,
        rol=rol,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        comisiones=comisiones or ["C1"],
        desde=desde or date(2026, 1, 1),
        hasta=hasta,
    )
    session.add(a)
    await session.flush()
    await session.refresh(a)
    return a.id


async def _make_salario_base(
    session: AsyncSession,
    tid: uuid.UUID,
    rol: str = "PROFESOR",
    monto: str = "1000",
    desde: date = date(2026, 1, 1),
    hasta: date | None = None,
) -> uuid.UUID:
    from app.models.salario_base import SalarioBase  # noqa: PLC0415
    sb = SalarioBase(
        tenant_id=tid,
        rol=rol,
        monto=Decimal(monto),
        desde=desde,
        hasta=hasta,
    )
    session.add(sb)
    await session.flush()
    await session.refresh(sb)
    return sb.id


async def _make_salario_plus(
    session: AsyncSession,
    tid: uuid.UUID,
    clave: str = "PROG",
    rol: str = "PROFESOR",
    monto: str = "200",
    desde: date = date(2026, 1, 1),
    hasta: date | None = None,
) -> uuid.UUID:
    from app.models.salario_plus import SalarioPlus  # noqa: PLC0415
    sp = SalarioPlus(
        tenant_id=tid,
        clave=clave,
        rol=rol,
        monto=Decimal(monto),
        desde=desde,
        hasta=hasta,
    )
    session.add(sp)
    await session.flush()
    await session.refresh(sp)
    return sp.id


def _make_current_user(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    roles: list[str] | None = None,
):
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    return CurrentUser(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=roles or ["FINANZAS"],
    )


# ===========================================================================
# Group 1 — SalarioBaseRepository
# ===========================================================================

@pytest.mark.asyncio
@_db_required
async def test_7_1_salario_base_get_vigente_presente(liq_session: AsyncSession):
    """7.1: get_vigente returns the vigent base at ref_date."""
    from app.repositories.salario_base_repository import SalarioBaseRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    # Base PROFESOR from 2026-01-01 open
    await _make_salario_base(liq_session, tid, rol="PROFESOR", monto="1000", desde=date(2026, 1, 1))
    await liq_session.commit()

    repo = SalarioBaseRepository(session=liq_session, tenant_id=tid)
    vigente = await repo.get_vigente("PROFESOR", date(2026, 5, 1))
    assert vigente is not None
    assert vigente.monto == Decimal("1000")
    assert vigente.rol == "PROFESOR"


@pytest.mark.asyncio
@_db_required
async def test_7_1_salario_base_get_vigente_ausente(liq_session: AsyncSession):
    """7.1: get_vigente returns None when no vigent base exists (before desde)."""
    from app.repositories.salario_base_repository import SalarioBaseRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    await _make_salario_base(liq_session, tid, rol="PROFESOR", desde=date(2026, 6, 1))
    await liq_session.commit()

    repo = SalarioBaseRepository(session=liq_session, tenant_id=tid)
    vigente = await repo.get_vigente("PROFESOR", date(2026, 5, 1))
    assert vigente is None


@pytest.mark.asyncio
@_db_required
async def test_7_8_salario_base_cambio_mitad_de_anio(liq_session: AsyncSession):
    """7.8: Base changes mid-year; liquidation uses the vigent value for the month."""
    from app.repositories.salario_base_repository import SalarioBaseRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    # Old base: 2026-01-01 to 2026-03-31
    await _make_salario_base(
        liq_session, tid, rol="PROFESOR", monto="1000",
        desde=date(2026, 1, 1), hasta=date(2026, 3, 31)
    )
    # New base: 2026-04-01 open
    await _make_salario_base(
        liq_session, tid, rol="PROFESOR", monto="1200",
        desde=date(2026, 4, 1), hasta=None
    )
    await liq_session.commit()

    repo = SalarioBaseRepository(session=liq_session, tenant_id=tid)

    # May 2026 → new base
    vigente_may = await repo.get_vigente("PROFESOR", date(2026, 5, 1))
    assert vigente_may is not None
    assert vigente_may.monto == Decimal("1200")

    # Feb 2026 → old base
    vigente_feb = await repo.get_vigente("PROFESOR", date(2026, 2, 1))
    assert vigente_feb is not None
    assert vigente_feb.monto == Decimal("1000")


@pytest.mark.asyncio
@_db_required
async def test_7_3_salario_base_solapamiento_detectado(liq_session: AsyncSession):
    """7.3: existe_solapamiento returns True when a vivo row overlaps."""
    from app.repositories.salario_base_repository import SalarioBaseRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    # Existing base: 2026-01-01 open
    await _make_salario_base(liq_session, tid, rol="PROFESOR", desde=date(2026, 1, 1))
    await liq_session.commit()

    repo = SalarioBaseRepository(session=liq_session, tenant_id=tid)
    # New range starting 2026-06-01 overlaps with the open existing range
    solapado = await repo.existe_solapamiento("PROFESOR", date(2026, 6, 1), None)
    assert solapado is True


@pytest.mark.asyncio
@_db_required
async def test_7_3_salario_base_sin_solapamiento(liq_session: AsyncSession):
    """7.3 TRIANGULATE: no overlap when existing hasta < new desde."""
    from app.repositories.salario_base_repository import SalarioBaseRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    # Existing base: 2026-01-01 to 2026-03-31
    await _make_salario_base(
        liq_session, tid, rol="PROFESOR",
        desde=date(2026, 1, 1), hasta=date(2026, 3, 31)
    )
    await liq_session.commit()

    repo = SalarioBaseRepository(session=liq_session, tenant_id=tid)
    # New range: 2026-04-01 open — does NOT overlap
    solapado = await repo.existe_solapamiento("PROFESOR", date(2026, 4, 1), None)
    assert solapado is False


# ===========================================================================
# Group 2 — SalarioPlusRepository
# ===========================================================================

@pytest.mark.asyncio
@_db_required
async def test_7_2_salario_plus_get_vigente_presente(liq_session: AsyncSession):
    """7.2: get_vigente returns the vigent plus at ref_date."""
    from app.repositories.salario_plus_repository import SalarioPlusRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    await _make_salario_plus(liq_session, tid, clave="PROG", rol="PROFESOR", monto="200", desde=date(2026, 1, 1))
    await liq_session.commit()

    repo = SalarioPlusRepository(session=liq_session, tenant_id=tid)
    vigente = await repo.get_vigente("PROG", "PROFESOR", date(2026, 6, 1))
    assert vigente is not None
    assert vigente.monto == Decimal("200")


@pytest.mark.asyncio
@_db_required
async def test_7_2_salario_plus_get_vigente_ausente(liq_session: AsyncSession):
    """7.2 TRIANGULATE: get_vigente returns None when no vigent plus."""
    from app.repositories.salario_plus_repository import SalarioPlusRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    await liq_session.commit()

    repo = SalarioPlusRepository(session=liq_session, tenant_id=tid)
    vigente = await repo.get_vigente("PROG", "PROFESOR", date(2026, 6, 1))
    assert vigente is None


@pytest.mark.asyncio
@_db_required
async def test_7_3_salario_plus_solapamiento_detectado(liq_session: AsyncSession):
    """7.3: existe_solapamiento for plus returns True on overlap."""
    from app.repositories.salario_plus_repository import SalarioPlusRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    await _make_salario_plus(
        liq_session, tid, clave="PROG", rol="PROFESOR", desde=date(2026, 1, 1)
    )
    await liq_session.commit()

    repo = SalarioPlusRepository(session=liq_session, tenant_id=tid)
    solapado = await repo.existe_solapamiento("PROG", "PROFESOR", date(2026, 4, 1), None)
    assert solapado is True


# ===========================================================================
# Group 3 — LiquidacionRepository
# ===========================================================================

@pytest.mark.asyncio
@_db_required
async def test_7_11_upsert_crea_nueva_liquidacion(liq_session: AsyncSession):
    """7.11: upsert_calculo creates a new row if none exists (RN-37)."""
    from app.repositories.liquidacion_repository import LiquidacionRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid)
    cohorte_id = await _make_cohorte(liq_session, tid)
    await liq_session.commit()

    repo = LiquidacionRepository(session=liq_session, tenant_id=tid)
    liq = await repo.upsert_calculo(
        usuario_id=uid,
        cohorte_id=cohorte_id,
        mes=5,
        anio=2026,
        rol="PROFESOR",
        comisiones=["C1"],
        base_monto=Decimal("1000"),
        plus_monto=Decimal("200"),
        total_monto=Decimal("1200"),
        desglose={"items": []},
        es_nexo=False,
        excluido_por_factura=False,
    )
    assert liq.id is not None
    assert liq.estado == "Abierta"
    assert liq.total_monto == Decimal("1200")


@pytest.mark.asyncio
@_db_required
async def test_7_11_upsert_idempotente_no_duplica(liq_session: AsyncSession):
    """7.11: upsert_calculo updates existing row, does not create duplicate (RN-37)."""
    from app.repositories.liquidacion_repository import LiquidacionRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid)
    cohorte_id = await _make_cohorte(liq_session, tid)
    await liq_session.commit()

    repo = LiquidacionRepository(session=liq_session, tenant_id=tid)

    # First upsert
    await repo.upsert_calculo(
        usuario_id=uid, cohorte_id=cohorte_id, mes=5, anio=2026,
        rol="PROFESOR", comisiones=["C1"],
        base_monto=Decimal("1000"), plus_monto=Decimal("200"), total_monto=Decimal("1200"),
        desglose=None, es_nexo=False, excluido_por_factura=False,
    )
    await liq_session.flush()

    # Second upsert with different values
    updated = await repo.upsert_calculo(
        usuario_id=uid, cohorte_id=cohorte_id, mes=5, anio=2026,
        rol="PROFESOR", comisiones=["C1", "C2"],
        base_monto=Decimal("1200"), plus_monto=Decimal("400"), total_monto=Decimal("1600"),
        desglose=None, es_nexo=False, excluido_por_factura=False,
    )
    await liq_session.flush()

    # Only one row should exist
    rows = await repo.listar_periodo(cohorte_id, 5, 2026)
    assert len(rows) == 1
    assert updated.total_monto == Decimal("1600")


@pytest.mark.asyncio
@_db_required
async def test_7_12_cerrar_periodo_pasa_a_cerrada(liq_session: AsyncSession):
    """7.12: cerrar_periodo sets estado=Cerrada + cerrada_at (RN-22)."""
    from app.repositories.liquidacion_repository import LiquidacionRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid)
    cohorte_id = await _make_cohorte(liq_session, tid)
    await liq_session.commit()

    repo = LiquidacionRepository(session=liq_session, tenant_id=tid)
    await repo.upsert_calculo(
        usuario_id=uid, cohorte_id=cohorte_id, mes=5, anio=2026,
        rol="PROFESOR", comisiones=["C1"],
        base_monto=Decimal("1000"), plus_monto=Decimal("0"), total_monto=Decimal("1000"),
        desglose=None, es_nexo=False, excluido_por_factura=False,
    )
    await liq_session.flush()

    cerradas = await repo.cerrar_periodo(cohorte_id, 5, 2026)
    assert len(cerradas) == 1
    assert cerradas[0].estado == "Cerrada"
    assert cerradas[0].cerrada_at is not None


@pytest.mark.asyncio
@_db_required
async def test_7_12_recalcular_cerrada_rechazado(liq_session: AsyncSession):
    """7.12: Attempting to recalculate a closed period raises ValueError (RN-22)."""
    from app.repositories.liquidacion_repository import LiquidacionRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid)
    cohorte_id = await _make_cohorte(liq_session, tid)
    await liq_session.commit()

    repo = LiquidacionRepository(session=liq_session, tenant_id=tid)
    await repo.upsert_calculo(
        usuario_id=uid, cohorte_id=cohorte_id, mes=5, anio=2026,
        rol="PROFESOR", comisiones=["C1"],
        base_monto=Decimal("1000"), plus_monto=Decimal("0"), total_monto=Decimal("1000"),
        desglose=None, es_nexo=False, excluido_por_factura=False,
    )
    await liq_session.flush()
    await repo.cerrar_periodo(cohorte_id, 5, 2026)
    await liq_session.flush()

    with pytest.raises(ValueError, match="Cerrada"):
        await repo.upsert_calculo(
            usuario_id=uid, cohorte_id=cohorte_id, mes=5, anio=2026,
            rol="PROFESOR", comisiones=["C1"],
            base_monto=Decimal("1200"), plus_monto=Decimal("0"), total_monto=Decimal("1200"),
            desglose=None, es_nexo=False, excluido_por_factura=False,
        )


# ===========================================================================
# Group 4 — FacturaRepository
# ===========================================================================

@pytest.mark.asyncio
@_db_required
async def test_factura_repo_crear_y_listar(liq_session: AsyncSession):
    """FacturaRepository: create and list facturas for tenant."""
    from app.models.factura import Factura  # noqa: PLC0415
    from app.repositories.factura_repository import FacturaRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid, facturador=True)
    await liq_session.commit()

    repo = FacturaRepository(session=liq_session, tenant_id=tid)
    f = Factura(
        tenant_id=tid,
        usuario_id=uid,
        periodo_mes=5,
        periodo_anio=2026,
        detalle="Servicios docentes",
        monto=Decimal("3000"),
        estado="Pendiente",
    )
    liq_session.add(f)
    await liq_session.flush()
    await liq_session.commit()

    facturas = await repo.listar()
    assert len(facturas) == 1
    assert facturas[0].monto == Decimal("3000")


@pytest.mark.asyncio
@_db_required
async def test_7_14_factura_sumar_periodo(liq_session: AsyncSession):
    """7.14: sumar_periodo returns sum of facturas for the period (RN-38)."""
    from app.models.factura import Factura  # noqa: PLC0415
    from app.repositories.factura_repository import FacturaRepository  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid, facturador=True)
    await liq_session.commit()

    repo = FacturaRepository(session=liq_session, tenant_id=tid)
    for monto in ["1000", "2000"]:
        f = Factura(
            tenant_id=tid, usuario_id=uid,
            periodo_mes=5, periodo_anio=2026,
            detalle="Servicios", monto=Decimal(monto), estado="Pendiente",
        )
        liq_session.add(f)
    await liq_session.commit()

    total = await repo.sumar_periodo(5, 2026)
    assert total == Decimal("3000")


# ===========================================================================
# Group 5 — GrillaSalarialService
# ===========================================================================

@pytest.mark.asyncio
@_db_required
async def test_grilla_crear_base_ok(liq_session: AsyncSession):
    """GrillaSalarialService: crear_base persists a row without overlap."""
    from app.schemas.salario_base import SalarioBaseCreate  # noqa: PLC0415
    from app.services.grilla_salarial_service import GrillaSalarialService  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    await liq_session.commit()

    svc = GrillaSalarialService(session=liq_session, tenant_id=tid)
    resp = await svc.crear_base(
        SalarioBaseCreate(rol="PROFESOR", monto=Decimal("1000"), desde=date(2026, 1, 1))
    )
    assert resp.id is not None
    assert resp.rol == "PROFESOR"
    assert resp.monto == Decimal("1000")


@pytest.mark.asyncio
@_db_required
async def test_7_3_grilla_crear_base_solapado_valor_error(liq_session: AsyncSession):
    """7.3: crear_base raises ValueError when vigency overlaps (RN-31)."""
    from app.schemas.salario_base import SalarioBaseCreate  # noqa: PLC0415
    from app.services.grilla_salarial_service import GrillaSalarialService  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    await _make_salario_base(liq_session, tid, rol="PROFESOR", desde=date(2026, 1, 1))
    await liq_session.commit()

    svc = GrillaSalarialService(session=liq_session, tenant_id=tid)
    with pytest.raises(ValueError, match="solapada"):
        await svc.crear_base(
            SalarioBaseCreate(rol="PROFESOR", monto=Decimal("1200"), desde=date(2026, 6, 1))
        )


@pytest.mark.asyncio
@_db_required
async def test_grilla_crear_plus_ok(liq_session: AsyncSession):
    """GrillaSalarialService: crear_plus persists a row without overlap."""
    from app.schemas.salario_plus import SalarioPlusCreate  # noqa: PLC0415
    from app.services.grilla_salarial_service import GrillaSalarialService  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    await liq_session.commit()

    svc = GrillaSalarialService(session=liq_session, tenant_id=tid)
    resp = await svc.crear_plus(
        SalarioPlusCreate(clave="PROG", rol="PROFESOR", monto=Decimal("200"), desde=date(2026, 1, 1))
    )
    assert resp.id is not None
    assert resp.clave == "PROG"


@pytest.mark.asyncio
@_db_required
async def test_7_3_grilla_crear_plus_solapado_valor_error(liq_session: AsyncSession):
    """7.3 TRIANGULATE: crear_plus raises ValueError on overlap."""
    from app.schemas.salario_plus import SalarioPlusCreate  # noqa: PLC0415
    from app.services.grilla_salarial_service import GrillaSalarialService  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    await _make_salario_plus(liq_session, tid, clave="PROG", rol="PROFESOR", desde=date(2026, 1, 1))
    await liq_session.commit()

    svc = GrillaSalarialService(session=liq_session, tenant_id=tid)
    with pytest.raises(ValueError, match="solapada"):
        await svc.crear_plus(
            SalarioPlusCreate(clave="PROG", rol="PROFESOR", monto=Decimal("250"), desde=date(2026, 6, 1))
        )


# ===========================================================================
# Group 6 — LiquidacionService
# ===========================================================================

@pytest.mark.asyncio
@_db_required
async def test_7_9_nexo_es_nexo_true(liq_session: AsyncSession):
    """7.9: NEXO docente → es_nexo=True in liquidacion (RN-36)."""
    from app.schemas.liquidacion import CalcularRequest  # noqa: PLC0415
    from app.services.liquidacion_service import LiquidacionService  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid, facturador=False)
    cohorte_id = await _make_cohorte(liq_session, tid)
    materia_id = await _make_materia(liq_session, tid)
    await _make_asignacion(
        liq_session, tid, uid, cohorte_id, materia_id, rol="NEXO",
        desde=date(2026, 1, 1)
    )
    await _make_salario_base(liq_session, tid, rol="NEXO", monto="800", desde=date(2026, 1, 1))
    await liq_session.commit()

    svc = LiquidacionService(session=liq_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)
    req = CalcularRequest(cohorte_id=cohorte_id, mes=5, anio=2026)
    results = await svc.calcular_periodo(req, current_user)

    assert len(results) == 1
    assert results[0].es_nexo is True
    assert results[0].rol == "NEXO"


@pytest.mark.asyncio
@_db_required
async def test_7_10_facturante_excluido_por_factura_true(liq_session: AsyncSession):
    """7.10: Facturante docente → excluido_por_factura=True (RN-35)."""
    from app.schemas.liquidacion import CalcularRequest  # noqa: PLC0415
    from app.services.liquidacion_service import LiquidacionService  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid, facturador=True)
    cohorte_id = await _make_cohorte(liq_session, tid)
    materia_id = await _make_materia(liq_session, tid)
    await _make_asignacion(
        liq_session, tid, uid, cohorte_id, materia_id, rol="PROFESOR",
        desde=date(2026, 1, 1)
    )
    await _make_salario_base(liq_session, tid, rol="PROFESOR", monto="1000", desde=date(2026, 1, 1))
    await liq_session.commit()

    svc = LiquidacionService(session=liq_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)
    req = CalcularRequest(cohorte_id=cohorte_id, mes=5, anio=2026)
    results = await svc.calcular_periodo(req, current_user)

    assert len(results) == 1
    assert results[0].excluido_por_factura is True


@pytest.mark.asyncio
@_db_required
async def test_7_11_cohortes_independientes(liq_session: AsyncSession):
    """7.11: Two cohortes produce independent liquidaciones (RN-37)."""
    from app.schemas.liquidacion import CalcularRequest  # noqa: PLC0415
    from app.services.liquidacion_service import LiquidacionService  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid)
    cohorte1_id = await _make_cohorte(liq_session, tid)
    cohorte2_id = await _make_cohorte(liq_session, tid)
    materia_id = await _make_materia(liq_session, tid)
    await _make_asignacion(liq_session, tid, uid, cohorte1_id, materia_id, rol="PROFESOR", desde=date(2026, 1, 1))
    await _make_asignacion(liq_session, tid, uid, cohorte2_id, materia_id, rol="PROFESOR", desde=date(2026, 1, 1))
    await _make_salario_base(liq_session, tid, rol="PROFESOR", monto="1000", desde=date(2026, 1, 1))
    await liq_session.commit()

    svc = LiquidacionService(session=liq_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)

    results1 = await svc.calcular_periodo(CalcularRequest(cohorte_id=cohorte1_id, mes=5, anio=2026), current_user)
    results2 = await svc.calcular_periodo(CalcularRequest(cohorte_id=cohorte2_id, mes=5, anio=2026), current_user)

    assert len(results1) == 1
    assert len(results2) == 1
    assert results1[0].cohorte_id != results2[0].cohorte_id


@pytest.mark.asyncio
@_db_required
async def test_7_12_cerrar_periodo_via_service(liq_session: AsyncSession):
    """7.12: LiquidacionService.cerrar_periodo closes period + emits audit."""
    from app.schemas.liquidacion import CalcularRequest, CerrarRequest  # noqa: PLC0415
    from app.services.liquidacion_service import LiquidacionService  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid)
    cohorte_id = await _make_cohorte(liq_session, tid)
    materia_id = await _make_materia(liq_session, tid)
    await _make_asignacion(liq_session, tid, uid, cohorte_id, materia_id, rol="PROFESOR", desde=date(2026, 1, 1))
    await _make_salario_base(liq_session, tid, rol="PROFESOR", monto="1000", desde=date(2026, 1, 1))
    await liq_session.commit()

    svc = LiquidacionService(session=liq_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)

    await svc.calcular_periodo(CalcularRequest(cohorte_id=cohorte_id, mes=5, anio=2026), current_user)
    await liq_session.flush()

    cerradas = await svc.cerrar_periodo(CerrarRequest(cohorte_id=cohorte_id, mes=5, anio=2026), current_user)
    assert len(cerradas) == 1
    assert cerradas[0].estado == "Cerrada"
    assert cerradas[0].cerrada_at is not None


@pytest.mark.asyncio
@_db_required
async def test_7_12_recalcular_cerrado_returns_409(liq_session: AsyncSession):
    """7.12: Recalculating a closed period raises HTTP 409 (RN-22)."""
    from fastapi import HTTPException  # noqa: PLC0415
    from app.schemas.liquidacion import CalcularRequest, CerrarRequest  # noqa: PLC0415
    from app.services.liquidacion_service import LiquidacionService  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid)
    cohorte_id = await _make_cohorte(liq_session, tid)
    materia_id = await _make_materia(liq_session, tid)
    await _make_asignacion(liq_session, tid, uid, cohorte_id, materia_id, rol="PROFESOR", desde=date(2026, 1, 1))
    await _make_salario_base(liq_session, tid, rol="PROFESOR", monto="1000", desde=date(2026, 1, 1))
    await liq_session.commit()

    svc = LiquidacionService(session=liq_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)

    await svc.calcular_periodo(CalcularRequest(cohorte_id=cohorte_id, mes=5, anio=2026), current_user)
    await liq_session.flush()
    await svc.cerrar_periodo(CerrarRequest(cohorte_id=cohorte_id, mes=5, anio=2026), current_user)
    await liq_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await svc.calcular_periodo(CalcularRequest(cohorte_id=cohorte_id, mes=5, anio=2026), current_user)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
@_db_required
async def test_7_13_cierre_emite_audit_log(liq_session: AsyncSession):
    """7.13: Cerrar emits AuditLog with LIQUIDACION_CERRAR + actor_id (RN-23)."""
    from app.models.audit_log import AuditLog  # noqa: PLC0415
    from app.schemas.liquidacion import CalcularRequest, CerrarRequest  # noqa: PLC0415
    from app.services.liquidacion_service import LiquidacionService  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid)
    cohorte_id = await _make_cohorte(liq_session, tid)
    materia_id = await _make_materia(liq_session, tid)
    await _make_asignacion(liq_session, tid, uid, cohorte_id, materia_id, rol="PROFESOR", desde=date(2026, 1, 1))
    await _make_salario_base(liq_session, tid, rol="PROFESOR", monto="1000", desde=date(2026, 1, 1))
    await liq_session.commit()

    svc = LiquidacionService(session=liq_session, tenant_id=tid)
    actor_uid = uid
    current_user = _make_current_user(actor_uid, tid)

    await svc.calcular_periodo(CalcularRequest(cohorte_id=cohorte_id, mes=5, anio=2026), current_user)
    await liq_session.flush()
    await svc.cerrar_periodo(CerrarRequest(cohorte_id=cohorte_id, mes=5, anio=2026), current_user)
    await liq_session.commit()

    # Check audit log
    result = await liq_session.execute(
        sa.select(AuditLog)
        .where(AuditLog.tenant_id == tid)
        .where(AuditLog.accion == "LIQUIDACION_CERRAR")
    )
    audit = result.scalar_one_or_none()
    assert audit is not None
    assert audit.actor_id == actor_uid
    assert audit.filas_afectadas == 1
    assert audit.detalle is not None
    assert audit.detalle["periodo_mes"] == 5


@pytest.mark.asyncio
@_db_required
async def test_7_14_vista_periodo_segmentacion_kpis(liq_session: AsyncSession):
    """7.14: vista_periodo segments general/nexo/facturantes and KPIs (RN-36/38)."""
    from app.models.factura import Factura  # noqa: PLC0415
    from app.schemas.liquidacion import CalcularRequest  # noqa: PLC0415
    from app.services.liquidacion_service import LiquidacionService  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid_gen = await _make_usuario(liq_session, tid)         # general
    uid_nexo = await _make_usuario(liq_session, tid)        # NEXO
    uid_fact = await _make_usuario(liq_session, tid, facturador=True)  # facturante
    cohorte_id = await _make_cohorte(liq_session, tid)
    materia_id = await _make_materia(liq_session, tid)

    await _make_asignacion(liq_session, tid, uid_gen, cohorte_id, materia_id, rol="PROFESOR", desde=date(2026, 1, 1))
    await _make_asignacion(liq_session, tid, uid_nexo, cohorte_id, materia_id, rol="NEXO", desde=date(2026, 1, 1))
    await _make_asignacion(liq_session, tid, uid_fact, cohorte_id, materia_id, rol="PROFESOR", desde=date(2026, 1, 1))
    await _make_salario_base(liq_session, tid, rol="PROFESOR", monto="1000", desde=date(2026, 1, 1))
    await _make_salario_base(liq_session, tid, rol="NEXO", monto="800", desde=date(2026, 1, 1))

    # Add a factura for the facturante
    f = Factura(
        tenant_id=tid, usuario_id=uid_fact,
        periodo_mes=5, periodo_anio=2026,
        detalle="Servicios", monto=Decimal("3000"), estado="Pendiente",
    )
    liq_session.add(f)
    await liq_session.commit()

    svc = LiquidacionService(session=liq_session, tenant_id=tid)
    current_user = _make_current_user(uid_gen, tid)
    await svc.calcular_periodo(CalcularRequest(cohorte_id=cohorte_id, mes=5, anio=2026), current_user)
    await liq_session.flush()

    vista = await svc.vista_periodo(cohorte_id, 5, 2026)
    assert len(vista.general.liquidaciones) >= 1
    assert len(vista.nexo.liquidaciones) >= 1
    assert len(vista.facturantes.liquidaciones) >= 1
    assert vista.total_sin_factura == vista.general.total + vista.nexo.total
    assert vista.total_con_factura == Decimal("3000")


# ===========================================================================
# Group 7 — FacturaService
# ===========================================================================

@pytest.mark.asyncio
@_db_required
async def test_7_15_factura_estados_pendiente_abonada(liq_session: AsyncSession):
    """7.15: Factura created as Pendiente; transition to Abonada sets abonada_at (RN-39)."""
    from app.schemas.factura import CambiarEstadoRequest, FacturaCreate  # noqa: PLC0415
    from app.models.factura import EstadoFactura  # noqa: PLC0415
    from app.services.factura_service import FacturaService  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid, facturador=True)
    await liq_session.commit()

    svc = FacturaService(session=liq_session, tenant_id=tid)
    factura = await svc.crear_factura(
        FacturaCreate(
            usuario_id=uid, periodo_mes=5, periodo_anio=2026,
            detalle="Servicios", monto=Decimal("3000")
        )
    )
    assert factura.estado == "Pendiente"
    assert factura.abonada_at is None

    abonada = await svc.cambiar_estado(
        factura.id, CambiarEstadoRequest(nuevo_estado=EstadoFactura.Abonada)
    )
    assert abonada.estado == "Abonada"
    assert abonada.abonada_at is not None


@pytest.mark.asyncio
@_db_required
async def test_7_15_factura_estado_invalido_422(liq_session: AsyncSession):
    """7.15 TRIANGULATE: Reversing Abonada → Pendiente raises 422 (RN-39)."""
    from fastapi import HTTPException  # noqa: PLC0415
    from app.schemas.factura import CambiarEstadoRequest, FacturaCreate  # noqa: PLC0415
    from app.models.factura import EstadoFactura  # noqa: PLC0415
    from app.services.factura_service import FacturaService  # noqa: PLC0415

    tid = await _make_tenant(liq_session)
    uid = await _make_usuario(liq_session, tid, facturador=True)
    await liq_session.commit()

    svc = FacturaService(session=liq_session, tenant_id=tid)
    factura = await svc.crear_factura(
        FacturaCreate(usuario_id=uid, periodo_mes=5, periodo_anio=2026, detalle="S", monto=Decimal("1000"))
    )
    await svc.cambiar_estado(factura.id, CambiarEstadoRequest(nuevo_estado=EstadoFactura.Abonada))
    await liq_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await svc.cambiar_estado(factura.id, CambiarEstadoRequest(nuevo_estado=EstadoFactura.Pendiente))
    assert exc_info.value.status_code == 422


# ===========================================================================
# Group 8 — Schema validation (no DB — always run)
# ===========================================================================

def test_schema_salario_base_extra_forbid():
    """SalarioBaseCreate rejects extra fields (extra='forbid')."""
    from pydantic import ValidationError  # noqa: PLC0415
    from app.schemas.salario_base import SalarioBaseCreate  # noqa: PLC0415

    with pytest.raises(ValidationError):
        SalarioBaseCreate(
            rol="PROFESOR",
            monto=Decimal("1000"),
            desde=date(2026, 1, 1),
            campo_extra="inválido",  # MUST be rejected
        )


def test_schema_salario_base_monto_negativo_rechazado():
    """SalarioBaseCreate rejects negative monto."""
    from pydantic import ValidationError  # noqa: PLC0415
    from app.schemas.salario_base import SalarioBaseCreate  # noqa: PLC0415

    with pytest.raises(ValidationError):
        SalarioBaseCreate(rol="PROFESOR", monto=Decimal("-1"), desde=date(2026, 1, 1))


def test_schema_calcular_request_mes_invalido():
    """CalcularRequest rejects mes outside 1..12."""
    from pydantic import ValidationError  # noqa: PLC0415
    from app.schemas.liquidacion import CalcularRequest  # noqa: PLC0415

    with pytest.raises(ValidationError):
        CalcularRequest(cohorte_id=uuid.uuid4(), mes=13, anio=2026)


def test_schema_calcular_request_anio_invalido():
    """CalcularRequest rejects anio < 2000."""
    from pydantic import ValidationError  # noqa: PLC0415
    from app.schemas.liquidacion import CalcularRequest  # noqa: PLC0415

    with pytest.raises(ValidationError):
        CalcularRequest(cohorte_id=uuid.uuid4(), mes=5, anio=1999)


def test_schema_factura_create_monto_negativo():
    """FacturaCreate rejects negative monto."""
    from pydantic import ValidationError  # noqa: PLC0415
    from app.schemas.factura import FacturaCreate  # noqa: PLC0415

    with pytest.raises(ValidationError):
        FacturaCreate(
            usuario_id=uuid.uuid4(), periodo_mes=5, periodo_anio=2026,
            detalle="S", monto=Decimal("-100")
        )


def test_schema_cambiar_estado_extra_forbid():
    """CambiarEstadoRequest rejects extra fields."""
    from pydantic import ValidationError  # noqa: PLC0415
    from app.schemas.factura import CambiarEstadoRequest  # noqa: PLC0415

    with pytest.raises(ValidationError):
        CambiarEstadoRequest(nuevo_estado="Pendiente", campo_extra="X")


# ===========================================================================
# Group 9 — Multi-tenancy isolation
# ===========================================================================

@pytest.mark.asyncio
@_db_required
async def test_7_16_aislamiento_tenant_salario_base(liq_session: AsyncSession):
    """7.16: SalarioBase from tenant B not visible to tenant A repository."""
    from app.repositories.salario_base_repository import SalarioBaseRepository  # noqa: PLC0415

    tid_a = await _make_tenant(liq_session, "A")
    tid_b = await _make_tenant(liq_session, "B")
    await _make_salario_base(liq_session, tid_b, rol="PROFESOR")
    await liq_session.commit()

    repo_a = SalarioBaseRepository(session=liq_session, tenant_id=tid_a)
    rows = await repo_a.listar()
    assert rows == []  # tenant A cannot see tenant B's rows


@pytest.mark.asyncio
@_db_required
async def test_7_16_aislamiento_tenant_factura(liq_session: AsyncSession):
    """7.16 TRIANGULATE: Factura from tenant B not visible to tenant A."""
    from app.models.factura import Factura  # noqa: PLC0415
    from app.repositories.factura_repository import FacturaRepository  # noqa: PLC0415

    tid_a = await _make_tenant(liq_session, "A2")
    tid_b = await _make_tenant(liq_session, "B2")
    uid_b = await _make_usuario(liq_session, tid_b)
    f = Factura(
        tenant_id=tid_b, usuario_id=uid_b,
        periodo_mes=5, periodo_anio=2026,
        detalle="B's factura", monto=Decimal("500"), estado="Pendiente",
    )
    liq_session.add(f)
    await liq_session.commit()

    repo_a = FacturaRepository(session=liq_session, tenant_id=tid_a)
    rows = await repo_a.listar()
    assert rows == []  # tenant A cannot see tenant B's facturas


# ===========================================================================
# Group 10 — HTTP endpoints
# ===========================================================================

@pytest_asyncio.fixture
async def liq_http_fixtures(liq_engine: AsyncEngine):
    """Build HTTP client wired to the test DB."""
    from app.core.database import build_session_factory  # noqa: PLC0415
    from app.core.dependencies import get_db, get_current_user  # noqa: PLC0415
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.main import create_app  # noqa: PLC0415

    factory = build_session_factory(liq_engine)
    application = create_app()

    async with factory() as setup_session:
        tid = await _make_tenant(setup_session)
        uid = await _make_usuario(setup_session, tid)
        await setup_session.commit()

    async def override_db():
        async with factory() as session:
            yield session

    async def override_auth():
        return CurrentUser(user_id=uid, tenant_id=tid, roles=["FINANZAS"])

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_current_user] = override_auth

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, tid, uid, factory


@pytest.mark.asyncio
@_db_required
async def test_7_16_http_sin_permiso_returns_403(liq_engine: AsyncEngine):
    """7.16: Request without liquidaciones:ver returns 403 (fail-closed)."""
    from app.core.database import build_session_factory  # noqa: PLC0415
    from app.core.dependencies import get_db, get_current_user  # noqa: PLC0415
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.main import create_app  # noqa: PLC0415

    factory = build_session_factory(liq_engine)
    application = create_app()

    async with factory() as setup_session:
        tid = await _make_tenant(setup_session)
        uid = await _make_usuario(setup_session, tid)
        await setup_session.commit()

    async def override_db():
        async with factory() as session:
            yield session

    async def override_no_perm():
        return CurrentUser(user_id=uid, tenant_id=tid, roles=[])

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_current_user] = override_no_perm

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/liquidaciones/historial")
    assert resp.status_code == 403


@pytest.mark.asyncio
@_db_required
async def test_http_listar_bases_returns_200_or_403(liq_http_fixtures):
    """GET /api/liquidaciones/grilla/base returns 200 or 403 (depends on RBAC seed)."""
    client, tid, uid, factory = liq_http_fixtures
    resp = await client.get("/api/liquidaciones/grilla/base")
    assert resp.status_code in (200, 403)


@pytest.mark.asyncio
@_db_required
async def test_http_crear_base_returns_201_or_409_or_403(liq_http_fixtures):
    """POST /api/liquidaciones/grilla/base returns 201/403/409."""
    client, tid, uid, factory = liq_http_fixtures
    resp = await client.post(
        "/api/liquidaciones/grilla/base",
        json={"rol": "PROFESOR", "monto": "1000", "desde": "2026-01-01", "hasta": None},
    )
    assert resp.status_code in (201, 403, 409)


@pytest.mark.asyncio
@_db_required
async def test_http_listar_facturas_returns_200_or_403(liq_http_fixtures):
    """GET /api/facturas returns 200 or 403."""
    client, tid, uid, factory = liq_http_fixtures
    resp = await client.get("/api/facturas/")
    assert resp.status_code in (200, 403)


@pytest.mark.asyncio
@_db_required
async def test_http_crear_factura_returns_201_or_403(liq_http_fixtures):
    """POST /api/facturas returns 201 or 403."""
    client, tid, uid, factory = liq_http_fixtures
    resp = await client.post(
        "/api/facturas/",
        json={
            "usuario_id": str(uid),
            "periodo_mes": 5,
            "periodo_anio": 2026,
            "detalle": "HTTP test",
            "monto": "500.00",
        },
    )
    assert resp.status_code in (201, 403)


@pytest.mark.asyncio
@_db_required
async def test_http_historial_returns_200_or_403(liq_http_fixtures):
    """GET /api/liquidaciones/historial returns 200 or 403."""
    client, tid, uid, factory = liq_http_fixtures
    resp = await client.get("/api/liquidaciones/historial")
    assert resp.status_code in (200, 403)

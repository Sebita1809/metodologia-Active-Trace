"""
tests/test_analisis_monitor.py — TDD tests for GET /analisis/monitor.

Covers the monitor general de actividades (F2.7): a cross-cutting view of all
students in the tenant with their activity status.

Tests:
  Unit tests (no DB — always run):
    - test_monitor_items_from_multiple_asignaciones (M.1)
    - test_monitor_filtro_materia_id (M.2)
    - test_monitor_filtro_busqueda_nombre_parcial (M.3)
    - test_monitor_estado_sin_datos_sin_calificaciones (M.4)
    - test_monitor_estado_al_dia (M.5)
    - test_monitor_estado_atrasado (M.6)
    - test_monitor_filtro_estado_actividad (M.7)
    - test_monitor_filtro_comision (M.8)
    - test_monitor_filtro_cohorte_id (M.9)
    - test_monitor_busqueda_case_insensitive (M.10)

  Integration tests (require TEST_DATABASE_URL):
    - test_monitor_tenant_isolation (M.11)
    - test_monitor_rbac_403_sin_permiso (M.12)
"""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from app.schemas.analisis import MonitorGeneralItem, MonitorGeneralResponse
from app.services.analisis_service import (
    MonitorFilters,
    _compute_monitor,
)

_requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping monitor integration tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Lightweight helpers (no DB)
# ---------------------------------------------------------------------------

def _make_asignacion(
    asignacion_id: uuid.UUID | None = None,
    materia_id: uuid.UUID | None = None,
    cohorte_id: uuid.UUID | None = None,
    materia_nombre: str = "Matemática",
    cohorte_nombre: str = "Cohorte 2024",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=asignacion_id or uuid.uuid4(),
        materia_id=materia_id or uuid.uuid4(),
        cohorte_id=cohorte_id or uuid.uuid4(),
        materia_nombre=materia_nombre,
        cohorte_nombre=cohorte_nombre,
    )


def _make_entrada(
    entrada_id: uuid.UUID | None = None,
    version_id: uuid.UUID | None = None,
    nombre: str = "Juan",
    apellidos: str = "Pérez",
    email: str = "juan@test.com",
    comision: str | None = "A",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=entrada_id or uuid.uuid4(),
        version_id=version_id or uuid.uuid4(),
        nombre=nombre,
        apellidos=apellidos,
        email=email,
        comision=comision,
    )


def _make_cal(
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
# Unit tests — no DB (always run)
# ---------------------------------------------------------------------------

def test_monitor_items_from_multiple_asignaciones():
    """M.1: Monitor returns items from multiple asignaciones of the same tenant."""
    asig1 = _make_asignacion(materia_nombre="Matemática", cohorte_nombre="C2024")
    asig2 = _make_asignacion(materia_nombre="Física", cohorte_nombre="C2023")

    e1 = _make_entrada(nombre="Ana", apellidos="López")
    e2 = _make_entrada(nombre="Bob", apellidos="Smith")

    # Bundle: (asignacion, entradas, calificaciones)
    bundles = [
        (asig1, [e1], [_make_cal(e1.id, aprobado=True)]),
        (asig2, [e2], [_make_cal(e2.id, aprobado=True)]),
    ]

    result = _compute_monitor(bundles, filters=MonitorFilters())

    assert result.total == 2
    nombres = {item.nombre for item in result.items}
    assert "Ana" in nombres
    assert "Bob" in nombres


def test_monitor_filtro_materia_id():
    """M.2: materia_id filter returns only items from that materia."""
    mat_id = uuid.uuid4()
    asig1 = _make_asignacion(materia_id=mat_id, materia_nombre="Matemática", cohorte_nombre="C2024")
    asig2 = _make_asignacion(materia_nombre="Física", cohorte_nombre="C2024")

    e1 = _make_entrada(nombre="Ana", apellidos="López")
    e2 = _make_entrada(nombre="Bob", apellidos="Smith")

    bundles = [
        (asig1, [e1], []),
        (asig2, [e2], []),
    ]

    result = _compute_monitor(bundles, filters=MonitorFilters(materia_id=mat_id))

    assert result.total == 1
    assert result.items[0].nombre == "Ana"


def test_monitor_filtro_busqueda_nombre_parcial():
    """M.3: busqueda filters by partial name match (case-insensitive)."""
    asig = _make_asignacion()
    e1 = _make_entrada(nombre="Ana", apellidos="López")
    e2 = _make_entrada(nombre="Roberto", apellidos="García")

    bundles = [(asig, [e1, e2], [])]

    result = _compute_monitor(bundles, filters=MonitorFilters(busqueda="ana"))

    assert result.total == 1
    assert result.items[0].nombre == "Ana"


def test_monitor_estado_sin_datos_sin_calificaciones():
    """M.4: estado='sin_datos' when no calificaciones exist for the student."""
    asig = _make_asignacion()
    e = _make_entrada()

    bundles = [(asig, [e], [])]  # no calificaciones

    result = _compute_monitor(bundles, filters=MonitorFilters())

    assert result.total == 1
    assert result.items[0].estado == "sin_datos"
    assert result.items[0].actividades_aprobadas == 0
    assert result.items[0].actividades_totales == 0


def test_monitor_estado_al_dia():
    """M.5: estado='al_dia' when all calificaciones are aprobado=True."""
    asig = _make_asignacion()
    e = _make_entrada()
    cals = [
        _make_cal(e.id, "Act1", aprobado=True),
        _make_cal(e.id, "Act2", aprobado=True),
    ]

    bundles = [(asig, [e], cals)]

    result = _compute_monitor(bundles, filters=MonitorFilters())

    assert result.total == 1
    item = result.items[0]
    assert item.estado == "al_dia"
    assert item.actividades_aprobadas == 2
    assert item.actividades_totales == 2


def test_monitor_estado_atrasado():
    """M.6: estado='atrasado' when at least one calificacion has aprobado=False."""
    asig = _make_asignacion()
    e = _make_entrada()
    cals = [
        _make_cal(e.id, "Act1", aprobado=True),
        _make_cal(e.id, "Act2", aprobado=False),
    ]

    bundles = [(asig, [e], cals)]

    result = _compute_monitor(bundles, filters=MonitorFilters())

    assert result.total == 1
    item = result.items[0]
    assert item.estado == "atrasado"
    assert item.actividades_aprobadas == 1
    assert item.actividades_totales == 2


def test_monitor_filtro_estado_actividad():
    """M.7: estado_actividad filter returns only students matching that estado."""
    asig = _make_asignacion()
    e_ok = _make_entrada(nombre="Ana", apellidos="OK")
    e_late = _make_entrada(nombre="Bob", apellidos="Late")
    e_nodata = _make_entrada(nombre="Carol", apellidos="NoData")

    cals_ok = [_make_cal(e_ok.id, "Act1", aprobado=True)]
    cals_late = [_make_cal(e_late.id, "Act1", aprobado=False)]

    bundles = [
        (asig, [e_ok, e_late, e_nodata], cals_ok + cals_late),
    ]

    result_al_dia = _compute_monitor(bundles, filters=MonitorFilters(estado_actividad="al_dia"))
    assert result_al_dia.total == 1
    assert result_al_dia.items[0].nombre == "Ana"

    result_atrasado = _compute_monitor(bundles, filters=MonitorFilters(estado_actividad="atrasado"))
    assert result_atrasado.total == 1
    assert result_atrasado.items[0].nombre == "Bob"

    result_sin_datos = _compute_monitor(bundles, filters=MonitorFilters(estado_actividad="sin_datos"))
    assert result_sin_datos.total == 1
    assert result_sin_datos.items[0].nombre == "Carol"


def test_monitor_filtro_comision():
    """M.8: comision filter returns only students with the matching comision string."""
    asig = _make_asignacion()
    e_a = _make_entrada(nombre="Ana", apellidos="A", comision="A")
    e_b = _make_entrada(nombre="Bob", apellidos="B", comision="B")

    bundles = [(asig, [e_a, e_b], [])]

    result = _compute_monitor(bundles, filters=MonitorFilters(comision="A"))

    assert result.total == 1
    assert result.items[0].nombre == "Ana"


def test_monitor_filtro_cohorte_id():
    """M.9: cohorte_id filter returns only students from that cohorte's asignacion."""
    coh_id = uuid.uuid4()
    asig1 = _make_asignacion(cohorte_id=coh_id, cohorte_nombre="Target")
    asig2 = _make_asignacion(cohorte_nombre="Other")

    e1 = _make_entrada(nombre="Ana", apellidos="Target")
    e2 = _make_entrada(nombre="Bob", apellidos="Other")

    bundles = [
        (asig1, [e1], []),
        (asig2, [e2], []),
    ]

    result = _compute_monitor(bundles, filters=MonitorFilters(cohorte_id=coh_id))

    assert result.total == 1
    assert result.items[0].nombre == "Ana"


def test_monitor_busqueda_case_insensitive():
    """M.10: busqueda is case-insensitive and matches partial apellidos too."""
    asig = _make_asignacion()
    e1 = _make_entrada(nombre="María", apellidos="González")
    e2 = _make_entrada(nombre="Carlos", apellidos="Rodríguez")

    bundles = [(asig, [e1, e2], [])]

    # uppercase partial match against apellidos
    result = _compute_monitor(bundles, filters=MonitorFilters(busqueda="GONZ"))
    assert result.total == 1
    assert result.items[0].nombre == "María"


# ---------------------------------------------------------------------------
# Integration tests (require TEST_DATABASE_URL)
# ---------------------------------------------------------------------------

@_requires_db
async def test_monitor_tenant_isolation(analisis_session):
    """M.11: Alumnos de tenant B NO aparecen en el monitor de tenant A."""
    from app.services.analisis_service import get_monitor_general  # noqa: PLC0415

    # re-use helpers from test_analisis.py via local imports
    from tests.test_analisis import (  # noqa: PLC0415
        _make_tenant,
        _make_materia,
        _make_cohorte,
        _make_usuario,
        _make_asignacion as _mk_asig,
        _make_version_padron,
        _make_entrada as _mk_entrada,
        _make_calificacion,
    )

    tid_a = await _make_tenant(analisis_session, "_MA")
    tid_b = await _make_tenant(analisis_session, "_MB")

    # Tenant B has a student
    uid_b = await _make_usuario(analisis_session, tid_b)
    mat_b = await _make_materia(analisis_session, tid_b)
    coh_b = await _make_cohorte(analisis_session, tid_b)
    await _mk_asig(analisis_session, tid_b, uid_b, mat_b, coh_b)
    ver_b = await _make_version_padron(analisis_session, tid_b, mat_b, coh_b, uid_b)
    await _mk_entrada(analisis_session, tid_b, ver_b, nombre="TenantB", apellidos="Student")
    await analisis_session.commit()

    # Query monitor for tenant A — should return empty
    result = await get_monitor_general(
        tenant_id=tid_a,
        filters=MonitorFilters(),
        db=analisis_session,
    )

    assert result.total == 0
    assert result.items == []


@_requires_db
def test_monitor_rbac_403_sin_permiso(app_instance):
    """M.12: /analisis/monitor returns 401/403 without a valid auth token."""
    import asyncio  # noqa: PLC0415
    from httpx import ASGITransport, AsyncClient  # noqa: PLC0415

    async def _run():
        transport = ASGITransport(app=app_instance)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/analisis/monitor")
            assert resp.status_code in (401, 403), (
                f"Expected 401/403 for /analisis/monitor, got {resp.status_code}"
            )

    asyncio.get_event_loop().run_until_complete(_run())

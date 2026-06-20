"""
tests/test_coloquios_unit.py — Unit tests for C-14 evaluaciones/coloquios (no DB required).

Tasks covered (unit layer, always run):
  T1.1-T1.3  — Model instantiation (imports work, fields exist)
  T2.1-T2.6  — Schema validation (EvaluacionCreate, ReservarRequest, etc.)
  T3.1-T3.4  — Pure helpers (hay_cupo, cupos_libres)
  T4.x       — Repository imports / construction patterns
  T5.x       — Service pure-function unit tests
  T6.x       — Router import + RBAC wiring (import-level only)

Integration tests (require TEST_DATABASE_URL) are in test_coloquios_integration.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# T1: Model imports and field existence
# ---------------------------------------------------------------------------

def test_evaluacion_model_import():
    """T1.1: Evaluacion model can be imported and instantiated."""
    from app.models.evaluacion import Evaluacion, TipoEvaluacion, EstadoEvaluacion

    assert Evaluacion.__tablename__ == "evaluacion"
    assert TipoEvaluacion.COLOQUIO == "Coloquio"
    assert TipoEvaluacion.PARCIAL == "Parcial"
    assert TipoEvaluacion.TP == "TP"
    assert TipoEvaluacion.RECUPERATORIO == "Recuperatorio"
    assert EstadoEvaluacion.ACTIVA == "Activa"
    assert EstadoEvaluacion.CERRADA == "Cerrada"


def test_reserva_evaluacion_model_import():
    """T1.2: ReservaEvaluacion model can be imported and has correct tablename."""
    from app.models.reserva_evaluacion import ReservaEvaluacion, EstadoReserva

    assert ReservaEvaluacion.__tablename__ == "reserva_evaluacion"
    assert EstadoReserva.ACTIVA == "Activa"
    assert EstadoReserva.CANCELADA == "Cancelada"


def test_resultado_evaluacion_model_import():
    """T1.3: ResultadoEvaluacion model can be imported and has correct tablename."""
    from app.models.resultado_evaluacion import ResultadoEvaluacion

    assert ResultadoEvaluacion.__tablename__ == "resultado_evaluacion"


# ---------------------------------------------------------------------------
# T2: Schema validation
# ---------------------------------------------------------------------------

def test_evaluacion_create_schema_valid():
    """T2.1: EvaluacionCreate accepts valid input."""
    from app.schemas.coloquios import EvaluacionCreate

    schema = EvaluacionCreate(
        materia_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        tipo="Coloquio",
        instancia="Coloquio Febrero 2026",
        dias_disponibles=5,
        cupo_por_dia=10,
    )
    assert schema.tipo == "Coloquio"
    assert schema.dias_disponibles == 5
    assert schema.cupo_por_dia == 10


def test_evaluacion_create_schema_invalid_tipo():
    """T2.2: EvaluacionCreate rejects invalid tipo."""
    from app.schemas.coloquios import EvaluacionCreate
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EvaluacionCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo="Examen",  # invalid
            instancia="Test",
            dias_disponibles=5,
            cupo_por_dia=10,
        )


def test_evaluacion_create_schema_invalid_dias():
    """T2.3: EvaluacionCreate rejects dias_disponibles <= 0."""
    from app.schemas.coloquios import EvaluacionCreate
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EvaluacionCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo="Coloquio",
            instancia="Test",
            dias_disponibles=0,  # invalid
            cupo_por_dia=10,
        )


def test_evaluacion_create_schema_extra_forbidden():
    """T2.4: EvaluacionCreate rejects unknown extra fields (extra='forbid')."""
    from app.schemas.coloquios import EvaluacionCreate
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EvaluacionCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo="Coloquio",
            instancia="Test",
            dias_disponibles=5,
            cupo_por_dia=10,
            unknown_field="oops",  # should be rejected
        )


def test_reservar_request_schema_valid():
    """T2.5: ReservarRequest accepts a valid fecha_hora."""
    from app.schemas.coloquios import ReservarRequest

    ts = datetime.now(tz=timezone.utc)
    schema = ReservarRequest(fecha_hora=ts)
    assert schema.fecha_hora == ts


def test_registrar_resultado_request_schema_valid():
    """T2.6: RegistrarResultadoRequest accepts alumno_id and nota_final."""
    from app.schemas.coloquios import RegistrarResultadoRequest

    schema = RegistrarResultadoRequest(alumno_id=uuid.uuid4(), nota_final="8")
    assert schema.nota_final == "8"


# ---------------------------------------------------------------------------
# T3: Pure helpers — hay_cupo, cupos_libres
# ---------------------------------------------------------------------------

def test_hay_cupo_returns_true_when_below_limit():
    """T3.1: hay_cupo → True when reservas < cupo_por_dia."""
    from app.services.coloquio_helpers import hay_cupo

    assert hay_cupo(reservas_activas_en_fecha=3, cupo_por_dia=5) is True


def test_hay_cupo_returns_false_when_at_limit():
    """T3.2: hay_cupo → False when reservas == cupo_por_dia (no more slots)."""
    from app.services.coloquio_helpers import hay_cupo

    assert hay_cupo(reservas_activas_en_fecha=5, cupo_por_dia=5) is False


def test_cupos_libres_correct():
    """T3.3: cupos_libres returns cupo_por_dia - reservas_activas."""
    from app.services.coloquio_helpers import cupos_libres

    assert cupos_libres(cupo_por_dia=10, reservas_activas=3) == 7


def test_cupos_libres_never_negative():
    """T3.4: cupos_libres returns 0 when reservas exceed cupo (never negative)."""
    from app.services.coloquio_helpers import cupos_libres

    assert cupos_libres(cupo_por_dia=5, reservas_activas=8) == 0


# ---------------------------------------------------------------------------
# T3 TRIANGULATE: Additional edge cases for pure helpers
# ---------------------------------------------------------------------------

def test_hay_cupo_with_zero_reservas():
    """T3.5: hay_cupo with 0 reservas always returns True (any cupo > 0)."""
    from app.services.coloquio_helpers import hay_cupo

    assert hay_cupo(0, 1) is True
    assert hay_cupo(0, 100) is True


def test_hay_cupo_exceeds_limit():
    """T3.6: hay_cupo returns False even when reservas exceeds cupo (edge case)."""
    from app.services.coloquio_helpers import hay_cupo

    # This shouldn't happen normally, but the function must handle it gracefully
    assert hay_cupo(10, 5) is False


def test_cupos_libres_when_full():
    """T3.7: cupos_libres returns 0 when exactly at capacity."""
    from app.services.coloquio_helpers import cupos_libres

    assert cupos_libres(cupo_por_dia=5, reservas_activas=5) == 0


def test_evaluacion_create_all_tipos_valid():
    """T3.8: EvaluacionCreate accepts all four valid tipos."""
    from app.schemas.coloquios import EvaluacionCreate

    for tipo in ["Parcial", "TP", "Coloquio", "Recuperatorio"]:
        schema = EvaluacionCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo=tipo,
            instancia="Test",
            dias_disponibles=3,
            cupo_por_dia=5,
        )
        assert schema.tipo == tipo


def test_metricas_panel_schema():
    """T3.9: MetricasPanel schema validates correctly with all counters."""
    from app.schemas.coloquios import MetricasPanel

    metrics = MetricasPanel(
        total_evaluaciones=10,
        total_reservas_activas=25,
        total_resultados=8,
        evaluaciones_cerradas=2,
    )
    assert metrics.total_evaluaciones == 10
    assert metrics.evaluaciones_cerradas == 2


# ---------------------------------------------------------------------------
# T4: Repository constructors
# ---------------------------------------------------------------------------

def test_evaluacion_repository_constructor():
    """T4.1: EvaluacionRepository can be constructed (import check)."""
    from unittest.mock import AsyncMock

    from app.repositories.evaluacion_repository import EvaluacionRepository

    mock_session = AsyncMock()
    repo = EvaluacionRepository(session=mock_session, tenant_id=uuid.uuid4())
    assert repo._model.__tablename__ == "evaluacion"


def test_reserva_repository_constructor():
    """T4.2: ReservaEvaluacionRepository can be constructed (import check)."""
    from unittest.mock import AsyncMock

    from app.repositories.reserva_evaluacion_repository import ReservaEvaluacionRepository

    mock_session = AsyncMock()
    repo = ReservaEvaluacionRepository(session=mock_session, tenant_id=uuid.uuid4())
    assert repo._model.__tablename__ == "reserva_evaluacion"


def test_resultado_repository_constructor():
    """T4.3: ResultadoEvaluacionRepository can be constructed (import check)."""
    from unittest.mock import AsyncMock

    from app.repositories.resultado_evaluacion_repository import ResultadoEvaluacionRepository

    mock_session = AsyncMock()
    repo = ResultadoEvaluacionRepository(session=mock_session, tenant_id=uuid.uuid4())
    assert repo._model.__tablename__ == "resultado_evaluacion"


# ---------------------------------------------------------------------------
# T5: Service import checks
# ---------------------------------------------------------------------------

def test_evaluacion_service_import():
    """T5.1: EvaluacionService can be imported."""
    from app.services.evaluacion_service import EvaluacionService  # noqa: F401

    assert EvaluacionService is not None


def test_reserva_service_import():
    """T5.2: ReservaService can be imported."""
    from app.services.reserva_service import ReservaService  # noqa: F401

    assert ReservaService is not None


def test_resultado_service_import():
    """T5.3: ResultadoService can be imported."""
    from app.services.resultado_service import ResultadoService  # noqa: F401

    assert ResultadoService is not None


# ---------------------------------------------------------------------------
# T6: Router import check (no HTTP calls)
# ---------------------------------------------------------------------------

def test_migration_file_structure():
    """T6.2: Migration 010 has correct revision, down_revision, upgrade, and downgrade."""
    import importlib.util
    import os

    mig_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "alembic",
        "versions",
        "010_evaluaciones_coloquios.py",
    )
    assert os.path.exists(mig_path), "Migration file must exist"

    spec = importlib.util.spec_from_file_location("migration_010", mig_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.revision == "010"
    assert mod.down_revision == "009"
    assert hasattr(mod, "upgrade"), "Migration must have upgrade()"
    assert hasattr(mod, "downgrade"), "Migration must have downgrade()"


def test_coloquios_router_file_exists():
    """T6.1: coloquios router module file exists and has correct route definitions."""
    import os

    # Check the file exists
    router_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "app",
        "api",
        "v1",
        "routers",
        "coloquios.py",
    )
    assert os.path.exists(router_path), "coloquios router file must exist"

    # Check it contains the expected routes
    with open(router_path) as f:
        content = f.read()

    assert "coloquios:gestionar" in content
    assert "coloquios:ver" in content
    assert "coloquios:reservar" in content
    assert "/{evaluacion_id}/reservas" in content
    assert "/{evaluacion_id}/resultados" in content

"""
tests/test_calificaciones.py — TDD tests for CalificacionService and UmbralMateriaService.

Tests:
  Unit tests (no DB):
    - test_compute_aprobado_numerico_below
    - test_compute_aprobado_numerico_equal
    - test_compute_aprobado_numerico_above
    - test_compute_aprobado_textual_satisfactorio
    - test_compute_aprobado_textual_supera
    - test_compute_aprobado_textual_no_satisfactorio
    - test_compute_aprobado_default_umbral

  Integration tests (require TEST_DATABASE_URL):
    - test_preview_import_xlsx
    - test_confirm_import_selected_activities
    - test_confirm_import_aprobado_correct
    - test_finalizacion_preview_textuales_only
    - test_umbral_upsert_create_and_update
    - test_umbral_isolation_between_docentes
    - test_rbac_403_without_permission
    - test_multitenant_isolation
"""
from __future__ import annotations

import csv
import io
import os
import uuid
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine
from app.services.calificacion_service import _compute_aprobado

# Integration tests only — unit tests below are not skipped
_requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping calificaciones integration tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Unit tests — no DB required (always run)
# ---------------------------------------------------------------------------

def test_compute_aprobado_numerico_below():
    """55.0 below umbral 60 → aprobado=False"""
    assert _compute_aprobado(55.0, None, 60) is False


def test_compute_aprobado_numerico_equal():
    """60.0 equals umbral 60 → aprobado=True"""
    assert _compute_aprobado(60.0, None, 60) is True


def test_compute_aprobado_numerico_above():
    """75.0 above umbral 60 → aprobado=True"""
    assert _compute_aprobado(75.0, None, 60) is True


def test_compute_aprobado_textual_satisfactorio():
    """"Satisfactorio" is in default valores_aprobatorios → aprobado=True"""
    assert _compute_aprobado(None, "Satisfactorio") is True


def test_compute_aprobado_textual_supera():
    """"Supera lo esperado" is in default valores_aprobatorios → aprobado=True"""
    assert _compute_aprobado(None, "Supera lo esperado") is True


def test_compute_aprobado_textual_no_satisfactorio():
    """"No satisfactorio" is NOT in default valores_aprobatorios → aprobado=False"""
    assert _compute_aprobado(None, "No satisfactorio") is False


def test_compute_aprobado_default_umbral():
    """59.0 below default umbral 60 → aprobado=False"""
    assert _compute_aprobado(59.0, None) is False


# ---------------------------------------------------------------------------
# Integration test fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def calificaciones_engine() -> AsyncEngine:
    """Create a full schema engine for calificaciones tests."""
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
async def cal_session(calificaciones_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(calificaciones_engine, expire_on_commit=False)
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
    t = Tenant(slug=f"cal-{uuid.uuid4().hex[:8]}{suffix}", nombre="Cal Test", activo=True)
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


async def _make_asignacion(
    session: AsyncSession,
    tid: uuid.UUID,
    usuario_id: uuid.UUID,
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
) -> uuid.UUID:
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    a = Asignacion(
        tenant_id=tid,
        usuario_id=usuario_id,
        rol="PROFESOR",
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        desde=date.today(),
    )
    session.add(a)
    await session.flush()
    await session.refresh(a)
    return a.id


async def _make_domain_usuario(
    session: AsyncSession, tid: uuid.UUID, email: str | None = None
) -> tuple[uuid.UUID, str]:
    """Create a domain Usuario and return (id, plaintext_email)."""
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.models.usuario import Usuario  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    if email is None:
        email = f"usr_{uuid.uuid4().hex[:8]}@example.com"
    u = Usuario(
        tenant_id=tid, nombre="Test", apellidos="User",
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id, email


async def _make_version_padron(
    session: AsyncSession,
    tid: uuid.UUID,
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> uuid.UUID:
    from app.models.version_padron import VersionPadron  # noqa: PLC0415
    v = VersionPadron(
        tenant_id=tid,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        cargado_por=usuario_id,
        cargado_at=datetime.now(tz=timezone.utc),
        activa=True,
        origen="archivo",
    )
    session.add(v)
    await session.flush()
    await session.refresh(v)
    return v.id


async def _make_entrada_padron(
    session: AsyncSession,
    tid: uuid.UUID,
    version_id: uuid.UUID,
    email: str,
) -> uuid.UUID:
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.models.entrada_padron import EntradaPadron  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    e = EntradaPadron(
        tenant_id=tid,
        version_id=version_id,
        nombre="Test",
        apellidos="User",
        email=crypto.encrypt(email),
    )
    session.add(e)
    await session.flush()
    await session.refresh(e)
    return e.id


def _make_service(session: AsyncSession, tenant_id: uuid.UUID):
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.services.audit_service import AuditService  # noqa: PLC0415
    from app.services.calificacion_service import CalificacionService  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    audit_svc = AuditService(session=session, tenant_id=tenant_id)
    return CalificacionService(
        session=session, tenant_id=tenant_id, crypto=crypto, audit_svc=audit_svc
    )


def _make_umbral_service(session: AsyncSession, tenant_id: uuid.UUID):
    from app.services.umbral_materia_service import UmbralMateriaService  # noqa: PLC0415
    return UmbralMateriaService(session=session, tenant_id=tenant_id)


def _make_current_user(user_id: uuid.UUID, tenant_id: uuid.UUID):
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    return CurrentUser(user_id=user_id, tenant_id=tenant_id, roles=[])


def _build_xlsx_grades(
    emails: list[str],
    actividades_numericas: list[str],
    actividades_textuales: list[str],
    grades: dict | None = None,
) -> bytes:
    """Build an in-memory XLSX file with LMS grade structure."""
    import openpyxl  # noqa: PLC0415
    wb = openpyxl.Workbook()
    ws = wb.active

    # Header row: email + numeric actividades (suffixed with " (Real)") + textual
    headers = ["email"] + actividades_numericas + actividades_textuales
    ws.append(headers)

    for email in emails:
        row = [email]
        for act in actividades_numericas:
            val = grades.get((email, act), 70) if grades else 70
            row.append(val)
        for act in actividades_textuales:
            val = grades.get((email, act), "Satisfactorio") if grades else "Satisfactorio"
            row.append(val)
        ws.append(row)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Integration test: preview_import with xlsx
# ---------------------------------------------------------------------------

@_requires_db
async def test_preview_import_xlsx(cal_session: AsyncSession):
    """preview_import parses xlsx, detects activities, does NOT write to DB."""
    from app.models.calificacion import Calificacion  # noqa: PLC0415

    tid = await _make_tenant(cal_session)
    uid, _ = await _make_domain_usuario(cal_session, tid)
    await cal_session.commit()

    svc = _make_service(cal_session, tid)
    asignacion_id = uuid.uuid4()  # not in DB — preview doesn't need it

    # Build xlsx with numeric + textual activities
    xlsx_bytes = _build_xlsx_grades(
        emails=["a@test.com", "b@test.com"],
        actividades_numericas=["Tarea1 (Real)", "Parcial (Real)"],
        actividades_textuales=["Escala actividad"],
    )

    result = await svc.preview_import(xlsx_bytes, "notas.xlsx", asignacion_id)

    assert result.actividades_numericas == ["Tarea1 (Real)", "Parcial (Real)"]
    assert result.actividades_textuales == ["Escala actividad"]
    assert result.alumnos_detectados == 2

    # Nothing persisted
    count = await cal_session.scalar(
        sa.select(sa.func.count()).select_from(Calificacion).where(Calificacion.tenant_id == tid)
    )
    assert count == 0


# ---------------------------------------------------------------------------
# Integration test: confirm_import with selected activities
# ---------------------------------------------------------------------------

@_requires_db
async def test_confirm_import_selected_activities(cal_session: AsyncSession):
    """confirm_import only creates Calificacion rows for selected activities."""
    from app.models.audit_log import AuditLog  # noqa: PLC0415
    from app.models.calificacion import Calificacion  # noqa: PLC0415
    from app.schemas.calificacion import ImportConfirmRequest  # noqa: PLC0415

    tid = await _make_tenant(cal_session)
    uid, email = await _make_domain_usuario(cal_session, tid, email="student@test.com")
    materia = await _make_materia(cal_session, tid)
    cohorte = await _make_cohorte(cal_session, tid)
    asig_id = await _make_asignacion(cal_session, tid, uid, materia, cohorte)
    version = await _make_version_padron(cal_session, tid, materia, cohorte, uid)
    await _make_entrada_padron(cal_session, tid, version, email)
    await cal_session.commit()

    svc = _make_service(cal_session, tid)
    current_user = _make_current_user(uid, tid)

    xlsx_bytes = _build_xlsx_grades(
        emails=[email],
        actividades_numericas=["Tarea1 (Real)", "Parcial (Real)"],
        actividades_textuales=[],
    )

    request = ImportConfirmRequest(
        asignacion_id=asig_id,
        actividades_seleccionadas=["Tarea1 (Real)"],  # only 1 of 2
    )

    result = await svc.confirm_import(xlsx_bytes, "notas.xlsx", request, current_user)
    await cal_session.commit()

    # Only 1 calificacion per the 1 selected activity
    assert len(result) == 1
    assert result[0].actividad == "Tarea1 (Real)"

    # DB count matches
    count = await cal_session.scalar(
        sa.select(sa.func.count()).select_from(Calificacion).where(Calificacion.tenant_id == tid)
    )
    assert count == 1

    # Audit log emitted
    audit = await cal_session.scalar(
        sa.select(AuditLog)
        .where(AuditLog.tenant_id == tid)
        .where(AuditLog.accion == "CALIFICACIONES_IMPORTAR")
    )
    assert audit is not None
    assert audit.filas_afectadas == 1


# ---------------------------------------------------------------------------
# Integration test: aprobado computed correctly with custom umbral
# ---------------------------------------------------------------------------

@_requires_db
async def test_confirm_import_aprobado_correct(cal_session: AsyncSession):
    """Grades below umbral_pct=70 → aprobado=False; at 70 → aprobado=True."""
    from app.models.calificacion import Calificacion  # noqa: PLC0415
    from app.schemas.calificacion import ImportConfirmRequest  # noqa: PLC0415

    tid = await _make_tenant(cal_session)
    uid, email_low = await _make_domain_usuario(cal_session, tid, email="low@test.com")
    _, email_pass = await _make_domain_usuario(cal_session, tid, email="pass@test.com")
    materia = await _make_materia(cal_session, tid)
    cohorte = await _make_cohorte(cal_session, tid)
    asig_id = await _make_asignacion(cal_session, tid, uid, materia, cohorte)
    version = await _make_version_padron(cal_session, tid, materia, cohorte, uid)
    await _make_entrada_padron(cal_session, tid, version, email_low)
    await _make_entrada_padron(cal_session, tid, version, email_pass)

    # Set custom umbral of 70
    from app.models.umbral_materia import UmbralMateria  # noqa: PLC0415
    umbral = UmbralMateria(
        tenant_id=tid,
        asignacion_id=asig_id,
        materia_id=materia,
        umbral_pct=70,
        valores_aprobatorios=["Satisfactorio"],
    )
    cal_session.add(umbral)
    await cal_session.commit()

    svc = _make_service(cal_session, tid)
    current_user = _make_current_user(uid, tid)

    xlsx_bytes = _build_xlsx_grades(
        emails=[email_low, email_pass],
        actividades_numericas=["Examen (Real)"],
        actividades_textuales=[],
        grades={
            (email_low, "Examen (Real)"): 65,   # below 70 → reprobado
            (email_pass, "Examen (Real)"): 70,  # exactly 70 → aprobado
        },
    )

    request = ImportConfirmRequest(
        asignacion_id=asig_id,
        actividades_seleccionadas=["Examen (Real)"],
    )

    result = await svc.confirm_import(xlsx_bytes, "notas.xlsx", request, current_user)
    await cal_session.commit()

    by_email: dict[str, bool] = {}
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.models.entrada_padron import EntradaPadron  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)

    for cal_read in result:
        # Look up the entrada_padron to get the email
        ep = await cal_session.scalar(
            sa.select(EntradaPadron).where(EntradaPadron.id == cal_read.entrada_padron_id)
        )
        assert ep is not None
        decoded = crypto.decrypt(ep.email)
        by_email[decoded] = cal_read.aprobado

    assert by_email[email_low] is False, "65 < 70 should be reprobado"
    assert by_email[email_pass] is True, "70 == 70 should be aprobado"


# ---------------------------------------------------------------------------
# Integration test: finalizacion_preview returns textual-only
# ---------------------------------------------------------------------------

@_requires_db
async def test_finalizacion_preview_textuales_only(cal_session: AsyncSession):
    """finalizacion_preview only returns textual items for which no calificacion exists."""
    import csv  # noqa: PLC0415
    import io  # noqa: PLC0415

    tid = await _make_tenant(cal_session)
    uid, email = await _make_domain_usuario(cal_session, tid, email="fin@test.com")
    materia = await _make_materia(cal_session, tid)
    cohorte = await _make_cohorte(cal_session, tid)
    asig_id = await _make_asignacion(cal_session, tid, uid, materia, cohorte)
    version = await _make_version_padron(cal_session, tid, materia, cohorte, uid)
    await _make_entrada_padron(cal_session, tid, version, email)
    await cal_session.commit()

    svc = _make_service(cal_session, tid)

    # Build CSV finalization file with one textual activity
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["email", "actividad", "finalizado"])
    writer.writeheader()
    writer.writerow({"email": email, "actividad": "Escala calidad", "finalizado": "true"})
    csv_bytes = output.getvalue().encode("utf-8")

    result = await svc.finalizacion_preview(csv_bytes, "fin.csv", asig_id)

    assert len(result.items) == 1
    assert result.items[0].actividad == "Escala calidad"
    assert result.items[0].alumno_email == email


# ---------------------------------------------------------------------------
# Integration test: umbral upsert create and update
# ---------------------------------------------------------------------------

@_requires_db
async def test_umbral_upsert_create_and_update(cal_session: AsyncSession):
    """upsert creates a new UmbralMateria; second call updates the existing one."""
    from app.models.umbral_materia import UmbralMateria  # noqa: PLC0415

    tid = await _make_tenant(cal_session)
    uid, _ = await _make_domain_usuario(cal_session, tid)
    materia = await _make_materia(cal_session, tid)
    cohorte = await _make_cohorte(cal_session, tid)
    asig_id = await _make_asignacion(cal_session, tid, uid, materia, cohorte)
    await cal_session.commit()

    svc = _make_umbral_service(cal_session, tid)

    # Create
    r1 = await svc.upsert(asig_id, materia, 65, ["Bien", "Excelente"])
    await cal_session.commit()

    assert r1.umbral_pct == 65
    assert r1.valores_aprobatorios == ["Bien", "Excelente"]

    count = await cal_session.scalar(
        sa.select(sa.func.count()).select_from(UmbralMateria).where(UmbralMateria.tenant_id == tid)
    )
    assert count == 1

    # Update — same asignacion, different values
    r2 = await svc.upsert(asig_id, materia, 70, ["Muy bien"])
    await cal_session.commit()

    assert r2.umbral_pct == 70
    assert r2.valores_aprobatorios == ["Muy bien"]

    # Still only 1 row
    count2 = await cal_session.scalar(
        sa.select(sa.func.count()).select_from(UmbralMateria).where(UmbralMateria.tenant_id == tid)
    )
    assert count2 == 1


# ---------------------------------------------------------------------------
# Integration test: umbral isolation between docentes (asignaciones)
# ---------------------------------------------------------------------------

@_requires_db
async def test_umbral_isolation_between_docentes(cal_session: AsyncSession):
    """Two asignaciones get independent umbrales — each get() returns the right one."""
    tid = await _make_tenant(cal_session)
    uid_a, _ = await _make_domain_usuario(cal_session, tid, email="prof_a@test.com")
    uid_b, _ = await _make_domain_usuario(cal_session, tid, email="prof_b@test.com")
    materia = await _make_materia(cal_session, tid)
    cohorte = await _make_cohorte(cal_session, tid)
    asig_a = await _make_asignacion(cal_session, tid, uid_a, materia, cohorte)
    asig_b = await _make_asignacion(cal_session, tid, uid_b, materia, cohorte)
    await cal_session.commit()

    svc = _make_umbral_service(cal_session, tid)

    await svc.upsert(asig_a, materia, 60, ["OK"])
    await svc.upsert(asig_b, materia, 80, ["Excelente"])
    await cal_session.commit()

    r_a = await svc.get(asig_a)
    r_b = await svc.get(asig_b)

    assert r_a.umbral_pct == 60
    assert r_b.umbral_pct == 80


# ---------------------------------------------------------------------------
# Integration test: RBAC 403 without permission
# ---------------------------------------------------------------------------

@_requires_db
async def test_rbac_403_without_permission(app_instance):
    """Calificaciones endpoints return 401/403 without auth token."""
    from httpx import ASGITransport, AsyncClient  # noqa: PLC0415

    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /api/calificaciones/ — no auth
        resp = await client.get("/api/calificaciones/", params={"asignacion_id": str(uuid.uuid4())})
        assert resp.status_code in (401, 403)

        # GET /api/calificaciones/umbral — no auth
        resp = await client.get("/api/calificaciones/umbral", params={"asignacion_id": str(uuid.uuid4())})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Integration test: multi-tenant isolation
# ---------------------------------------------------------------------------

@_requires_db
async def test_multitenant_isolation(cal_session: AsyncSession):
    """Calificaciones from tenant A are invisible to tenant B's repository."""
    from app.models.calificacion import Calificacion  # noqa: PLC0415
    from app.repositories.calificacion_repository import CalificacionRepository  # noqa: PLC0415

    tid_a = await _make_tenant(cal_session, suffix="_A")
    tid_b = await _make_tenant(cal_session, suffix="_B")
    uid_a, email_a = await _make_domain_usuario(cal_session, tid_a, email="a@a.com")
    uid_b, email_b = await _make_domain_usuario(cal_session, tid_b, email="b@b.com")
    mat_a = await _make_materia(cal_session, tid_a)
    mat_b = await _make_materia(cal_session, tid_b)
    coh_a = await _make_cohorte(cal_session, tid_a)
    coh_b = await _make_cohorte(cal_session, tid_b)
    asig_a = await _make_asignacion(cal_session, tid_a, uid_a, mat_a, coh_a)
    asig_b = await _make_asignacion(cal_session, tid_b, uid_b, mat_b, coh_b)
    ver_a = await _make_version_padron(cal_session, tid_a, mat_a, coh_a, uid_a)
    ep_a = await _make_entrada_padron(cal_session, tid_a, ver_a, email_a)
    await cal_session.commit()

    # Create a calificacion in tenant A
    cal = Calificacion(
        tenant_id=tid_a,
        entrada_padron_id=ep_a,
        materia_id=mat_a,
        actividad="Tarea (Real)",
        nota_numerica=80,
        aprobado=True,
        origen="Importado",
    )
    cal_session.add(cal)
    await cal_session.commit()

    # Tenant B's repo should return nothing
    repo_b = CalificacionRepository(session=cal_session, tenant_id=tid_b)
    result_b = await repo_b.list_by_entradas([ep_a])  # ep_a belongs to tenant A
    assert result_b == [], "Tenant B should not see Tenant A's calificaciones"

    # Tenant A's repo should see it
    repo_a = CalificacionRepository(session=cal_session, tenant_id=tid_a)
    result_a = await repo_a.list_by_entradas([ep_a])
    assert len(result_a) == 1

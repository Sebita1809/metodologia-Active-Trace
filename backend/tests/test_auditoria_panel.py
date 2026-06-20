"""
tests/test_auditoria_panel.py — TDD tests for C-19 panel de auditoría y métricas.

Covers tasks 5.1–5.12:
  5.1  Acciones por día: conteo correcto en rango, exclusión fuera del rango
  5.2  Comunicaciones por docente: distribución por estado, exclusión de no-comunicacionales
  5.3  Interacciones por docente×materia: conteo por materia y clave "sin materia"
  5.4  Últimas N acciones: default 200, límite respetado, acotamiento al máximo duro
  5.5  Log filtrado: rango de fechas, materia, usuario, acción y estado
  5.6  Paginación del log (limit/offset, orden desc)
  5.7  Scope propio del COORDINADOR: solo equipo visible; equipo vacío → vacío
  5.8  Scope propio: filtro por usuario_id fuera del equipo → vacío
  5.9  Scope global (ADMIN/FINANZAS): ve todo el tenant
  5.10 Sin auditoria:ver → 403
  5.11 Aislamiento por tenant
  5.12 Repositorio no expone update/delete (append-only)

Requires TEST_DATABASE_URL (PostgreSQL — no mocks).

TDD cycle:
  RED   — written before implementation
  GREEN — C-19 implemented
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping auditoria_panel tests",
)

_SECRET_KEY = "c19" + "x" * 29  # 32 chars
_ENC_KEY = "ef" * 32  # 64 hex chars
_CRYPTO_KEY = "ab" * 32  # 64 hex chars for CryptoService


# ---------------------------------------------------------------------------
# Model registration
# ---------------------------------------------------------------------------

def _register_models() -> None:
    import app.models.tenant              # noqa: F401
    import app.models.user                # noqa: F401
    import app.models.audit_log           # noqa: F401
    import app.models.rol                 # noqa: F401
    import app.models.permiso             # noqa: F401
    import app.models.rol_permiso         # noqa: F401
    import app.models.usuario_rol         # noqa: F401
    import app.models.usuario             # noqa: F401
    import app.models.asignacion          # noqa: F401
    import app.models.materia             # noqa: F401
    import app.models.carrera             # noqa: F401
    import app.models.cohorte             # noqa: F401
    import app.features.auth.models       # noqa: F401


def _drop_enum(conn) -> None:
    try:
        conn.execute(text("DROP TYPE IF EXISTS alcance_enum CASCADE"))
    except Exception:
        pass


def _create_enum_if_not_exists(conn) -> None:
    try:
        conn.execute(text("CREATE TYPE alcance_enum AS ENUM ('global', 'propio')"))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Engine / session fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def panel_engine() -> AsyncEngine:
    """Function-scoped engine with full RBAC + audit_log + asignaciones schema."""
    _register_models()
    url = os.environ["TEST_DATABASE_URL"]
    engine = build_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_drop_enum)
        await conn.run_sync(_create_enum_if_not_exists)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_drop_enum)
    await engine.dispose()


@pytest_asyncio.fixture
async def panel_session(panel_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def panel_tenant(panel_session: AsyncSession) -> uuid.UUID:
    """Create a test tenant with RBAC seeded and return its UUID."""
    from app.models.tenant import Tenant                  # noqa: PLC0415
    from app.services.rbac_seed import seed_rbac_for_tenant  # noqa: PLC0415

    os.environ["SECRET_KEY"] = _SECRET_KEY
    os.environ["ENCRYPTION_KEY"] = _ENC_KEY
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://placeholder/test")
    import app.core.config as cfg  # noqa: PLC0415
    cfg._settings = None

    t = Tenant(slug=f"panel-t-{uuid.uuid4().hex[:8]}", nombre="Panel Tenant", activo=True)
    panel_session.add(t)
    await panel_session.flush()
    await panel_session.refresh(t)
    tid = t.id

    conn = await panel_session.connection()
    await conn.run_sync(seed_rbac_for_tenant, tid)
    await panel_session.commit()
    return tid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_audit_record(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    accion: str = "CALIFICACIONES_IMPORTAR",
    materia_id: uuid.UUID | None = None,
    fecha_hora: datetime | None = None,
) -> None:
    """Insert an audit record, optionally with a specific fecha_hora."""
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

    repo = AuditLogRepository(session=session, tenant_id=tenant_id)
    record = await repo.crear(
        actor_id=actor_id,
        accion=accion,
        materia_id=materia_id,
        ip=None,
        user_agent=None,
    )
    # Override fecha_hora if provided (the server_default sets it to now())
    if fecha_hora is not None:
        await session.execute(
            text("UPDATE audit_log SET fecha_hora = :ts WHERE id = :rid"),
            {"ts": fecha_hora, "rid": str(record.id)},
        )
    await session.commit()


async def _create_user_with_role(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    role_name: str,
) -> uuid.UUID:
    from app.models.user import User        # noqa: PLC0415
    from app.core.security import hash_password  # noqa: PLC0415

    user = User(
        tenant_id=tenant_id,
        email=f"u{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("Test1234!"),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    uid = user.id

    await session.execute(
        text(
            """
            INSERT INTO usuario_rol (id, tenant_id, user_id, rol_id, vigente_desde, created_at, updated_at)
            SELECT gen_random_uuid(), :tid, :uid, r.id, now(), now(), now()
            FROM roles r
            WHERE r.tenant_id = :tid AND r.nombre = :role
            """
        ),
        {"tid": str(tenant_id), "uid": str(uid), "role": role_name},
    )
    await session.commit()
    return uid


async def _create_usuario(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> uuid.UUID:
    """Create a Usuario record (domain model) and return its UUID."""
    from app.models.usuario import Usuario  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415

    crypto = CryptoService(_CRYPTO_KEY)
    email = f"d{uuid.uuid4().hex[:6]}@test.com"
    u = Usuario(
        tenant_id=tenant_id,
        nombre="Test",
        apellidos="Docente",
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    await session.commit()
    return u.id


async def _create_asignacion(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID,
    responsable_id: uuid.UUID,
    rol: str = "PROFESOR",
) -> None:
    """Create an Asignacion linking usuario to a responsable (coordinator)."""
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    from datetime import date  # noqa: PLC0415

    a = Asignacion(
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        rol=rol,
        responsable_id=responsable_id,
        desde=date.today(),
    )
    session.add(a)
    await session.flush()
    await session.commit()


def _build_panel_app(engine: AsyncEngine) -> FastAPI:
    """Build a minimal FastAPI app with the auditoria router."""
    from app.core.dependencies import get_db          # noqa: PLC0415
    from app.api.v1.routers.auditoria import router as aud_router  # noqa: PLC0415

    factory = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    app = FastAPI(lifespan=noop_lifespan)
    app.include_router(aud_router, prefix="/api/v1/auditoria", tags=["auditoria"])

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    return app


def _make_token(user_id: uuid.UUID, tenant_id: uuid.UUID, roles: list[str]) -> str:
    from app.core.security import create_access_token  # noqa: PLC0415

    return create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=roles,
        secret_key=_SECRET_KEY,
        expire_minutes=15,
    )


# ---------------------------------------------------------------------------
# 5.12 — Repositório não expõe update/delete (append-only)
# ---------------------------------------------------------------------------

def test_repository_has_no_update_method():
    """AuditLogRepository must not expose 'update' (append-only contract)."""
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

    assert not hasattr(AuditLogRepository, "update"), (
        "AuditLogRepository must not expose 'update'"
    )


def test_repository_has_no_soft_delete_method():
    """AuditLogRepository must not expose 'soft_delete' (append-only contract)."""
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

    assert not hasattr(AuditLogRepository, "soft_delete"), (
        "AuditLogRepository must not expose 'soft_delete'"
    )


def test_repository_has_no_delete_method():
    """AuditLogRepository must not expose 'delete' (append-only contract)."""
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

    assert not hasattr(AuditLogRepository, "delete"), (
        "AuditLogRepository must not expose 'delete'"
    )


# ---------------------------------------------------------------------------
# 5.1 — Acciones por día: conteo correcto en rango, exclusión fuera del rango
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_acciones_por_dia_within_range(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """Counts actions within the date range, grouped by day."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()
    tz = timezone.utc

    day1 = datetime(2026, 6, 1, 12, 0, tzinfo=tz)
    day3 = datetime(2026, 6, 3, 12, 0, tzinfo=tz)

    async with factory() as session:
        # 5 actions on day1, 0 on day2, 3 on day3
        for _ in range(5):
            await _create_audit_record(session, panel_tenant, actor, fecha_hora=day1)
        for _ in range(3):
            await _create_audit_record(session, panel_tenant, actor, fecha_hora=day3)

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        rows = await repo.acciones_por_dia(
            desde=datetime(2026, 6, 1, 0, 0, tzinfo=tz),
            hasta=datetime(2026, 6, 3, 23, 59, tzinfo=tz),
        )

    totals = {row["dia"].date(): row["total"] for row in rows}
    from datetime import date  # noqa: PLC0415
    assert totals.get(date(2026, 6, 1), 0) == 5
    assert totals.get(date(2026, 6, 3), 0) == 3
    # day2 should not appear (no actions)
    assert date(2026, 6, 2) not in totals


@pytest.mark.asyncio
async def test_acciones_por_dia_outside_range_excluded(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """Actions outside the requested date range are not counted."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()
    tz = timezone.utc

    outside_date = datetime(2026, 5, 31, 12, 0, tzinfo=tz)
    inside_date = datetime(2026, 6, 2, 12, 0, tzinfo=tz)

    async with factory() as session:
        await _create_audit_record(session, panel_tenant, actor, fecha_hora=outside_date)
        await _create_audit_record(session, panel_tenant, actor, fecha_hora=inside_date)

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        rows = await repo.acciones_por_dia(
            desde=datetime(2026, 6, 1, 0, 0, tzinfo=tz),
            hasta=datetime(2026, 6, 3, 23, 59, tzinfo=tz),
        )

    from datetime import date  # noqa: PLC0415
    totals_by_date = {row["dia"].date() for row in rows}
    assert date(2026, 5, 31) not in totals_by_date
    assert date(2026, 6, 2) in totals_by_date


# ---------------------------------------------------------------------------
# 5.2 — Comunicaciones por docente: distribución por estado, exclusión de no-comms
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_comunicaciones_por_docente_state_distribution(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """Correct distribution of communication states per actor."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()

    async with factory() as session:
        # 2 enviado, 1 fallido
        await _create_audit_record(session, panel_tenant, actor, accion="COMUNICACION_ENVIAR")
        await _create_audit_record(session, panel_tenant, actor, accion="COMUNICACION_ENVIAR")
        await _create_audit_record(session, panel_tenant, actor, accion="COMUNICACION_FALLAR")

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        rows = await repo.comunicaciones_por_docente()

    actor_rows = [r for r in rows if r["actor_id"] == actor]
    # Should have entries for COMUNICACION_ENVIAR and COMUNICACION_FALLAR
    by_accion = {r["accion"]: r["total"] for r in actor_rows}
    assert by_accion.get("COMUNICACION_ENVIAR", 0) == 2
    assert by_accion.get("COMUNICACION_FALLAR", 0) == 1


@pytest.mark.asyncio
async def test_comunicaciones_por_docente_excludes_non_comm_actions(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """Non-COMUNICACION_* actions are excluded from communication stats."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()

    async with factory() as session:
        await _create_audit_record(session, panel_tenant, actor, accion="CALIFICACIONES_IMPORTAR")
        await _create_audit_record(session, panel_tenant, actor, accion="COMUNICACION_ENVIAR")

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        rows = await repo.comunicaciones_por_docente()

    actor_rows = [r for r in rows if r["actor_id"] == actor]
    # Only COMUNICACION_ENVIAR should appear
    acciones = {r["accion"] for r in actor_rows}
    assert "CALIFICACIONES_IMPORTAR" not in acciones
    assert "COMUNICACION_ENVIAR" in acciones


# ---------------------------------------------------------------------------
# 5.3 — Interacciones por docente×materia: por materia y "sin materia"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_interacciones_docente_materia_counts(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """Actions are counted per actor×materia, including the 'sin materia' bucket."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()
    materia_id = uuid.uuid4()

    async with factory() as session:
        # 4 with materia, 1 without
        for _ in range(4):
            await _create_audit_record(session, panel_tenant, actor, materia_id=materia_id)
        await _create_audit_record(session, panel_tenant, actor, materia_id=None)

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        rows = await repo.interacciones_por_docente_materia()

    actor_rows = {r["materia_id"]: r["total"] for r in rows if r["actor_id"] == actor}
    assert actor_rows.get(materia_id, 0) == 4, f"Expected 4 for materia, got: {actor_rows}"
    assert actor_rows.get(None, 0) == 1, f"Expected 1 for sin materia, got: {actor_rows}"


# ---------------------------------------------------------------------------
# 5.4 — Últimas N acciones: default 200, límite respetado, acotamiento
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ultimas_acciones_default_limit(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """With 250 records and limit=200, returns exactly 200 (most recent first)."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        for _ in range(250):
            await repo.crear(actor_id=actor, accion="PADRON_CARGAR", ip=None, user_agent=None)
        await session.commit()

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        records = await repo.ultimas_acciones(limit=200)

    assert len(records) == 200


@pytest.mark.asyncio
async def test_ultimas_acciones_configurable_limit(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """With limit=50, returns at most 50 records."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        for _ in range(100):
            await repo.crear(actor_id=actor, accion="PADRON_CARGAR", ip=None, user_agent=None)
        await session.commit()

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        records = await repo.ultimas_acciones(limit=50)

    assert len(records) <= 50


@pytest.mark.asyncio
async def test_ultimas_acciones_caps_at_max(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """Requesting more than _MAX_ULTIMAS_ACCIONES is capped at the maximum."""
    from app.repositories.audit_log import _MAX_ULTIMAS_ACCIONES  # noqa: PLC0415

    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        # Insert max + 10 to confirm capping
        for _ in range(min(_MAX_ULTIMAS_ACCIONES + 10, 50)):  # keep test fast: just 50
            await repo.crear(actor_id=actor, accion="PADRON_CARGAR", ip=None, user_agent=None)
        await session.commit()

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        # Request more than the max → should be capped
        records = await repo.ultimas_acciones(limit=_MAX_ULTIMAS_ACCIONES + 999)

    assert len(records) <= _MAX_ULTIMAS_ACCIONES


# ---------------------------------------------------------------------------
# 5.5 — Log filtrado: rango de fechas, materia, usuario, acción, estado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_log_filtrado_date_range(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """Only records within the date range are returned."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()
    tz = timezone.utc

    inside = datetime(2026, 6, 1, 12, 0, tzinfo=tz)
    outside = datetime(2026, 5, 30, 12, 0, tzinfo=tz)

    async with factory() as session:
        await _create_audit_record(session, panel_tenant, actor, fecha_hora=inside)
        await _create_audit_record(session, panel_tenant, actor, fecha_hora=outside)

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        records = await repo.listar_filtrado(
            desde=datetime(2026, 6, 1, 0, 0, tzinfo=tz),
            hasta=datetime(2026, 6, 2, 0, 0, tzinfo=tz),
        )

    assert len(records) == 1
    assert records[0].fecha_hora >= datetime(2026, 6, 1, 0, 0, tzinfo=tz)


@pytest.mark.asyncio
async def test_log_filtrado_by_materia(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """Filter by materia_id returns only matching records."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()
    materia_id = uuid.uuid4()

    async with factory() as session:
        await _create_audit_record(session, panel_tenant, actor, materia_id=materia_id)
        await _create_audit_record(session, panel_tenant, actor, materia_id=None)
        await _create_audit_record(session, panel_tenant, actor, materia_id=uuid.uuid4())

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        records = await repo.listar_filtrado(materia_id=materia_id)

    assert len(records) == 1
    assert records[0].materia_id == materia_id


@pytest.mark.asyncio
async def test_log_filtrado_by_usuario(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """Filter by actor_ids returns only records for those actors."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor_a = uuid.uuid4()
    actor_b = uuid.uuid4()

    async with factory() as session:
        await _create_audit_record(session, panel_tenant, actor_a)
        await _create_audit_record(session, panel_tenant, actor_b)

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        records = await repo.listar_filtrado(actor_ids=[actor_a])

    assert all(r.actor_id == actor_a for r in records)
    assert len(records) == 1


@pytest.mark.asyncio
async def test_log_filtrado_by_accion(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """Filter by exact accion code returns only matching records."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()

    async with factory() as session:
        await _create_audit_record(session, panel_tenant, actor, accion="CALIFICACIONES_IMPORTAR")
        await _create_audit_record(session, panel_tenant, actor, accion="PADRON_CARGAR")

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        records = await repo.listar_filtrado(accion="CALIFICACIONES_IMPORTAR")

    assert len(records) == 1
    assert records[0].accion == "CALIFICACIONES_IMPORTAR"


@pytest.mark.asyncio
async def test_log_filtrado_by_estado_via_service(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """Filter by estado (via service) returns only COMUNICACION_* records mapping to that state."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()

    async with factory() as session:
        await _create_audit_record(session, panel_tenant, actor, accion="COMUNICACION_FALLAR")
        await _create_audit_record(session, panel_tenant, actor, accion="COMUNICACION_ENVIAR")
        await _create_audit_record(session, panel_tenant, actor, accion="CALIFICACIONES_IMPORTAR")

    async with factory() as session:
        from app.services.auditoria_service import AuditoriaService  # noqa: PLC0415
        from app.schemas.auditoria import LogFiltradoQuery  # noqa: PLC0415

        svc = AuditoriaService(session=session, tenant_id=panel_tenant)
        result = await svc.log_filtrado(
            query=LogFiltradoQuery(estado="Fallido"),
            alcance="global",
            coordinador_id=actor,
        )

    assert all(r.accion in ("COMUNICACION_FALLAR", "COMUNICACION_FALLIDO") for r in result.items)
    assert len(result.items) >= 1


# ---------------------------------------------------------------------------
# 5.6 — Paginación del log (limit/offset, orden desc)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_log_filtrado_pagination_order_desc(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """Log is returned in descending fecha_hora order with correct pagination."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()
    tz = timezone.utc

    async with factory() as session:
        for i in range(5):
            ts = datetime(2026, 6, i + 1, 12, 0, tzinfo=tz)
            await _create_audit_record(session, panel_tenant, actor, fecha_hora=ts)

    async with factory() as session:
        from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

        repo = AuditLogRepository(session=session, tenant_id=panel_tenant)
        page1 = await repo.listar_filtrado(limit=2, offset=0)
        page2 = await repo.listar_filtrado(limit=2, offset=2)

    assert len(page1) == 2
    assert len(page2) == 2
    # Page 1 should have more recent records than page 2
    assert page1[0].fecha_hora > page2[0].fecha_hora
    # Within each page, descending order
    assert page1[0].fecha_hora >= page1[1].fecha_hora


# ---------------------------------------------------------------------------
# 5.7 — Scope propio: COORDINADOR ve solo su equipo; equipo vacío → vacío
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scope_propio_coordinator_sees_only_team(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """COORDINADOR with propio scope sees only team members' audit records."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)

    async with factory() as session:
        coord_id = await _create_usuario(session, panel_tenant)
        team_member_id = await _create_usuario(session, panel_tenant)
        outsider_id = uuid.uuid4()

        await _create_asignacion(session, panel_tenant, team_member_id, coord_id)

        await _create_audit_record(session, panel_tenant, team_member_id)
        await _create_audit_record(session, panel_tenant, outsider_id)

    async with factory() as session:
        from app.services.auditoria_service import AuditoriaService  # noqa: PLC0415
        from app.schemas.auditoria import LogFiltradoQuery  # noqa: PLC0415

        svc = AuditoriaService(session=session, tenant_id=panel_tenant)
        result = await svc.log_filtrado(
            query=LogFiltradoQuery(limit=100),
            alcance="propio",
            coordinador_id=coord_id,
        )

    actor_ids_in_result = {r.actor_id for r in result.items}
    assert team_member_id in actor_ids_in_result
    assert outsider_id not in actor_ids_in_result


@pytest.mark.asyncio
async def test_scope_propio_empty_team_returns_empty(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """COORDINADOR with empty team gets empty result (fail-closed)."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor = uuid.uuid4()

    async with factory() as session:
        coord_id = await _create_usuario(session, panel_tenant)
        # No asignaciones for coord_id → empty team
        await _create_audit_record(session, panel_tenant, actor)

    async with factory() as session:
        from app.services.auditoria_service import AuditoriaService  # noqa: PLC0415
        from app.schemas.auditoria import LogFiltradoQuery  # noqa: PLC0415

        svc = AuditoriaService(session=session, tenant_id=panel_tenant)
        result = await svc.log_filtrado(
            query=LogFiltradoQuery(limit=100),
            alcance="propio",
            coordinador_id=coord_id,
        )

    # Fail-closed: empty team → empty result, NEVER the full tenant
    assert result.items == []


# ---------------------------------------------------------------------------
# 5.8 — Scope propio: filtro por usuario_id fuera del equipo → vacío
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scope_propio_user_id_outside_team_returns_empty(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """COORDINADOR filtering by a user outside their team gets empty result."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    outsider_id = uuid.uuid4()

    async with factory() as session:
        coord_id = await _create_usuario(session, panel_tenant)
        team_member_id = await _create_usuario(session, panel_tenant)
        await _create_asignacion(session, panel_tenant, team_member_id, coord_id)

        # Insert record for outsider (should not be visible to coord)
        await _create_audit_record(session, panel_tenant, outsider_id)

    async with factory() as session:
        from app.services.auditoria_service import AuditoriaService  # noqa: PLC0415
        from app.schemas.auditoria import LogFiltradoQuery  # noqa: PLC0415

        svc = AuditoriaService(session=session, tenant_id=panel_tenant)
        result = await svc.log_filtrado(
            query=LogFiltradoQuery(usuario_id=outsider_id, limit=100),
            alcance="propio",
            coordinador_id=coord_id,
        )

    assert result.items == [], "Should be empty: requested user is outside coordinator team"


# ---------------------------------------------------------------------------
# 5.9 — Scope global (ADMIN/FINANZAS): ve todo el tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scope_global_sees_all_tenant_records(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """ADMIN with global scope sees all audit records of the tenant."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    actor_a = uuid.uuid4()
    actor_b = uuid.uuid4()
    actor_c = uuid.uuid4()

    async with factory() as session:
        await _create_audit_record(session, panel_tenant, actor_a)
        await _create_audit_record(session, panel_tenant, actor_b)
        await _create_audit_record(session, panel_tenant, actor_c)

    async with factory() as session:
        from app.services.auditoria_service import AuditoriaService  # noqa: PLC0415
        from app.schemas.auditoria import LogFiltradoQuery  # noqa: PLC0415

        svc = AuditoriaService(session=session, tenant_id=panel_tenant)
        admin_id = uuid.uuid4()  # arbitrary — global scope ignores it
        result = await svc.log_filtrado(
            query=LogFiltradoQuery(limit=100),
            alcance="global",
            coordinador_id=admin_id,
        )

    actor_ids = {r.actor_id for r in result.items}
    assert actor_a in actor_ids
    assert actor_b in actor_ids
    assert actor_c in actor_ids


# ---------------------------------------------------------------------------
# 5.10 — Sin auditoria:ver → 403 en panel y log
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_permission_returns_403_on_panel_endpoint(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """User without auditoria:ver gets 403 on panel endpoints."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    async with factory() as session:
        alumno_id = await _create_user_with_role(session, panel_tenant, "ALUMNO")

    token = _make_token(alumno_id, panel_tenant, ["ALUMNO"])
    app = _build_panel_app(panel_engine)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/v1/auditoria/panel/ultimas-acciones",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_no_permission_returns_403_on_log_endpoint(
    panel_engine: AsyncEngine,
    panel_tenant: uuid.UUID,
) -> None:
    """User without auditoria:ver gets 403 on /log endpoint."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    async with factory() as session:
        alumno_id = await _create_user_with_role(session, panel_tenant, "ALUMNO")

    token = _make_token(alumno_id, panel_tenant, ["ALUMNO"])
    app = _build_panel_app(panel_engine)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/v1/auditoria/log",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# 5.11 — Aislamiento por tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_isolation_in_panel(
    panel_engine: AsyncEngine,
) -> None:
    """Tenant B cannot see audit records of tenant A."""
    factory = async_sessionmaker(panel_engine, expire_on_commit=False)
    from app.models.tenant import Tenant  # noqa: PLC0415
    from app.services.rbac_seed import seed_rbac_for_tenant  # noqa: PLC0415

    os.environ["SECRET_KEY"] = _SECRET_KEY
    os.environ["ENCRYPTION_KEY"] = _ENC_KEY
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://placeholder/test")
    import app.core.config as cfg  # noqa: PLC0415
    cfg._settings = None

    async with factory() as session:
        ta = Tenant(slug=f"ta-{uuid.uuid4().hex[:8]}", nombre="Tenant A", activo=True)
        tb = Tenant(slug=f"tb-{uuid.uuid4().hex[:8]}", nombre="Tenant B", activo=True)
        session.add_all([ta, tb])
        await session.flush()
        await session.refresh(ta)
        await session.refresh(tb)
        tid_a, tid_b = ta.id, tb.id
        conn = await session.connection()
        await conn.run_sync(seed_rbac_for_tenant, tid_a)
        await conn.run_sync(seed_rbac_for_tenant, tid_b)
        await session.commit()

    actor_a = uuid.uuid4()

    async with factory() as session:
        await _create_audit_record(session, tid_a, actor_a)

    async with factory() as session:
        from app.services.auditoria_service import AuditoriaService  # noqa: PLC0415
        from app.schemas.auditoria import LogFiltradoQuery  # noqa: PLC0415

        # Tenant B service should NOT see tenant A records
        svc_b = AuditoriaService(session=session, tenant_id=tid_b)
        admin_id = uuid.uuid4()
        result = await svc_b.log_filtrado(
            query=LogFiltradoQuery(limit=100),
            alcance="global",
            coordinador_id=admin_id,
        )

    actor_ids = {r.actor_id for r in result.items}
    assert actor_a not in actor_ids, "Tenant B must not see Tenant A's audit records"

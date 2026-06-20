"""
tests/test_impersonation_service.py — TDD tests for ImpersonationService (Task 8).

Verifies:
  - Starting impersonation without impersonacion:usar → 403 (8.1)
  - Starting with permission emits token with 'impersonando' claim + audits INICIAR (8.2)
  - Ending impersonation audits FINALIZAR (actor_id=A, impersonado_id=B) (8.3)
  - Auditable action under impersonation attributed to real actor (8.6)

Requires TEST_DATABASE_URL (PostgreSQL — no mocks).

TDD cycle:
  RED   — written before implementation
  GREEN — impersonation_service.py and router created
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping impersonation_service tests",
)

_SECRET_KEY = "imp" + "x" * 29  # 32 chars
_ENC_KEY = "cd" * 32  # 64 hex chars


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _register_models():
    import app.models.tenant       # noqa: F401
    import app.models.user         # noqa: F401
    import app.models.audit_log    # noqa: F401
    import app.models.rol          # noqa: F401
    import app.models.permiso      # noqa: F401
    import app.models.rol_permiso  # noqa: F401
    import app.models.usuario_rol  # noqa: F401
    import app.features.auth.models  # noqa: F401


def _create_enum_if_not_exists(conn):
    try:
        conn.execute(text("CREATE TYPE alcance_enum AS ENUM ('global', 'propio')"))
    except Exception:
        pass


def _drop_enum(conn):
    try:
        conn.execute(text("DROP TYPE IF EXISTS alcance_enum CASCADE"))
    except Exception:
        pass


@pytest_asyncio.fixture
async def imp_engine() -> AsyncEngine:
    """Full schema with RBAC + audit_log."""
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
async def imp_session(imp_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(imp_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def seeded_tenant(imp_session: AsyncSession) -> uuid.UUID:
    """Create a tenant, seed RBAC, and return tenant_id."""
    from app.models.tenant import Tenant  # noqa: PLC0415
    from app.services.rbac_seed import seed_rbac_for_tenant  # noqa: PLC0415

    # Override settings for this test
    os.environ["SECRET_KEY"] = _SECRET_KEY
    os.environ["ENCRYPTION_KEY"] = _ENC_KEY
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://placeholder/test")
    import app.core.config as cfg  # noqa: PLC0415
    cfg._settings = None  # reset cache

    t = Tenant(slug=f"imp-t-{uuid.uuid4().hex[:8]}", nombre="Imp Tenant", activo=True)
    imp_session.add(t)
    await imp_session.flush()
    await imp_session.refresh(t)
    tid = t.id

    conn = await imp_session.connection()
    await conn.run_sync(seed_rbac_for_tenant, tid)
    await imp_session.commit()
    return tid


def _build_test_app(engine: AsyncEngine) -> FastAPI:
    """Build a minimal FastAPI app with impersonation router wired to test DB."""
    from app.core.dependencies import get_db  # noqa: PLC0415
    from app.api.v1.routers.impersonacion import router as imp_router  # noqa: PLC0415

    factory = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    app = FastAPI(lifespan=noop_lifespan)
    app.include_router(imp_router, prefix="/api/impersonacion", tags=["impersonacion"])

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


async def _create_user_with_role(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    role_name: str,
) -> uuid.UUID:
    """Helper: create a user and assign a role. Returns user_id."""
    from app.models.user import User  # noqa: PLC0415
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


# ---------------------------------------------------------------------------
# Task 8.1 — No permission → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_impersonation_without_permission_returns_403(
    imp_engine: AsyncEngine,
    seeded_tenant: uuid.UUID,
):
    """Initiating impersonation without impersonacion:usar returns 403."""
    from app.core.security import create_access_token  # noqa: PLC0415

    factory = async_sessionmaker(imp_engine, expire_on_commit=False)
    async with factory() as session:
        actor_id = await _create_user_with_role(session, seeded_tenant, "COORDINADOR")

    token = create_access_token(
        user_id=actor_id,
        tenant_id=seeded_tenant,
        roles=["COORDINADOR"],
        secret_key=_SECRET_KEY,
        expire_minutes=15,
    )

    app = _build_test_app(imp_engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/impersonacion/iniciar",
            json={"usuario_id": str(uuid.uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Task 8.2 — With permission, emits distinguishable token + audits INICIAR
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_impersonation_with_permission_emits_token_and_audits(
    imp_engine: AsyncEngine,
    seeded_tenant: uuid.UUID,
):
    """Admin starting impersonation receives a token with 'impersonando' claim and audit record."""
    from app.core.security import create_access_token, verify_token  # noqa: PLC0415
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

    factory = async_sessionmaker(imp_engine, expire_on_commit=False)
    async with factory() as session:
        actor_id = await _create_user_with_role(session, seeded_tenant, "ADMIN")
        target_id = await _create_user_with_role(session, seeded_tenant, "COORDINADOR")

    token = create_access_token(
        user_id=actor_id,
        tenant_id=seeded_tenant,
        roles=["ADMIN"],
        secret_key=_SECRET_KEY,
        expire_minutes=15,
    )

    app = _build_test_app(imp_engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/impersonacion/iniciar",
            json={"usuario_id": str(target_id)},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "access_token" in data, f"No access_token in response: {data}"

    # Token must contain 'impersonando' claim
    imp_token = data["access_token"]
    claims = verify_token(imp_token, secret_key=_SECRET_KEY, expected_scope="access")
    assert claims.get("impersonando") == str(target_id), (
        f"Expected impersonando={target_id}, got: {claims}"
    )
    assert claims["sub"] == str(actor_id), "sub must be the real actor"

    # Audit record: IMPERSONACION_INICIAR with actor_id=actor, impersonado_id=target
    async with factory() as session:
        repo = AuditLogRepository(session=session, tenant_id=seeded_tenant)
        records = await repo.listar()

    iniciar_records = [r for r in records if r.accion == "IMPERSONACION_INICIAR"]
    assert len(iniciar_records) >= 1, (
        f"Expected IMPERSONACION_INICIAR audit record, got: {[r.accion for r in records]}"
    )
    rec = iniciar_records[0]
    assert rec.actor_id == actor_id, f"actor_id should be {actor_id}, got {rec.actor_id}"
    assert rec.impersonado_id == target_id, (
        f"impersonado_id should be {target_id}, got {rec.impersonado_id}"
    )


# ---------------------------------------------------------------------------
# Task 8.3 — End impersonation audits FINALIZAR
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_end_impersonation_audits_finalizar(
    imp_engine: AsyncEngine,
    seeded_tenant: uuid.UUID,
):
    """Calling /impersonacion/finalizar records IMPERSONACION_FINALIZAR."""
    from app.core.security import create_access_token  # noqa: PLC0415
    from app.repositories.audit_log import AuditLogRepository  # noqa: PLC0415

    factory = async_sessionmaker(imp_engine, expire_on_commit=False)
    async with factory() as session:
        actor_id = await _create_user_with_role(session, seeded_tenant, "ADMIN")
        target_id = await _create_user_with_role(session, seeded_tenant, "COORDINADOR")

    # Token with impersonando claim (simulating an active impersonation session)
    imp_token = create_access_token(
        user_id=actor_id,
        tenant_id=seeded_tenant,
        roles=["COORDINADOR"],
        secret_key=_SECRET_KEY,
        expire_minutes=15,
        impersonando_user_id=target_id,
    )

    app = _build_test_app(imp_engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/impersonacion/finalizar",
            headers={"Authorization": f"Bearer {imp_token}"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    async with factory() as session:
        repo = AuditLogRepository(session=session, tenant_id=seeded_tenant)
        records = await repo.listar()

    fin_records = [r for r in records if r.accion == "IMPERSONACION_FINALIZAR"]
    assert len(fin_records) >= 1, (
        f"Expected IMPERSONACION_FINALIZAR record, got: {[r.accion for r in records]}"
    )
    rec = fin_records[0]
    assert rec.actor_id == actor_id
    assert rec.impersonado_id == target_id


# ---------------------------------------------------------------------------
# Task 8.6 — Auditable action under impersonation attributed to real actor
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_under_impersonation_attributed_to_real_actor(
    imp_session: AsyncSession,
    seeded_tenant: uuid.UUID,
):
    """Under impersonation session, audit record has actor_id=A and impersonado_id=B."""
    from app.services.audit_service import AuditService  # noqa: PLC0415
    from app.services.audit_codes import AccionAuditoria  # noqa: PLC0415
    from app.core.auth_context import CurrentUser  # noqa: PLC0415

    actor_id = uuid.uuid4()
    impersonado_id = uuid.uuid4()

    current_user = CurrentUser(
        user_id=actor_id,
        tenant_id=seeded_tenant,
        roles=["COORDINADOR"],
        impersonando_user_id=impersonado_id,
    )

    svc = AuditService(session=imp_session, tenant_id=seeded_tenant)
    record = await svc.registrar(
        current_user,
        AccionAuditoria.CALIFICACIONES_IMPORTAR,
        ip="10.0.0.1",
        user_agent="pytest",
    )

    assert record.actor_id == actor_id, "actor_id must be real actor A"
    assert record.impersonado_id == impersonado_id, "impersonado_id must be impersonated user B"

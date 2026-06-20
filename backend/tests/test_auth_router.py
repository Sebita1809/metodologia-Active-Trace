"""
tests/test_auth_router.py — Integration tests for auth router and get_current_user.

TDD cycle:
  8.1  RED    — login endpoint 200/401 (requires TEST_DATABASE_URL).
  8.4  RED    — get_current_user: no token → 401; valid → ok; partial_token → 401.
  8.5  GREEN  — implement get_current_user.
  8.6  TRIANGULATE — identity from JWT, not query param.

Tests 8.4 and 8.6 do NOT require a DB (JWT-only validation).
Test 8.1 requires TEST_DATABASE_URL.
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from fastapi import FastAPI, Depends
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

_SECRET_KEY = "s" * 32
_ENC_KEY = "ab" * 32


# ---------------------------------------------------------------------------
# Shared: minimal app fixture (no lifespan, no DB needed for JWT tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def jwt_only_app():
    """FastAPI app with get_current_user wired, no DB needed."""
    import app.core.config as cfg  # noqa: PLC0415

    # Ensure env vars are set so Settings() can be instantiated
    os.environ.setdefault("SECRET_KEY", _SECRET_KEY)
    os.environ.setdefault("ENCRYPTION_KEY", _ENC_KEY)
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://placeholder/test")
    cfg._settings = None  # reset cache so new env vars take effect

    from app.core.dependencies import get_current_user  # noqa: PLC0415
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.core.rate_limiter import limiter  # noqa: PLC0415

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    app = FastAPI(lifespan=noop_lifespan)
    app.state.limiter = limiter

    @app.get("/api/test/me")
    async def me(user: CurrentUser = Depends(get_current_user)):
        return {"user_id": str(user.user_id), "tenant_id": str(user.tenant_id)}

    @app.get("/api/test/identity")
    async def identity(
        user_id: str | None = None,
        user: CurrentUser = Depends(get_current_user),
    ):
        return {"identity": str(user.user_id)}

    return app


@pytest_asyncio.fixture
async def jwt_client(jwt_only_app):
    transport = ASGITransport(app=jwt_only_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _make_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID, roles: list = None) -> str:
    import os  # noqa: PLC0415
    os.environ.setdefault("SECRET_KEY", _SECRET_KEY)
    os.environ.setdefault("ENCRYPTION_KEY", _ENC_KEY)
    from app.core.security import create_access_token  # noqa: PLC0415
    return create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=roles or [],
        secret_key=_SECRET_KEY,
        expire_minutes=15,
    )


def _make_partial_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    from app.core.security import create_partial_token  # noqa: PLC0415
    return create_partial_token(
        user_id=user_id,
        tenant_id=tenant_id,
        secret_key=_SECRET_KEY,
    )


# ---------------------------------------------------------------------------
# 8.4 RED / 8.5 GREEN — get_current_user dependency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_protected_without_token_returns_401(jwt_client: AsyncClient):
    """No Authorization header → 401."""
    resp = await jwt_client.get("/api/test/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_with_valid_token_returns_200(jwt_client: AsyncClient):
    """Valid Bearer access token → 200 with user identity."""
    uid = uuid.uuid4()
    tid = uuid.uuid4()
    token = _make_access_token(uid, tid)

    resp = await jwt_client.get("/api/test/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == str(uid)
    assert data["tenant_id"] == str(tid)


@pytest.mark.asyncio
async def test_protected_with_partial_token_returns_401(jwt_client: AsyncClient):
    """Token with scope='2fa_pending' → 401 (wrong scope for access-protected routes)."""
    uid = uuid.uuid4()
    tid = uuid.uuid4()
    partial = _make_partial_token(uid, tid)

    resp = await jwt_client.get("/api/test/me", headers={"Authorization": f"Bearer {partial}"})

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_with_invalid_token_returns_401(jwt_client: AsyncClient):
    """Tampered token → 401."""
    resp = await jwt_client.get("/api/test/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 8.6 TRIANGULATE — identity comes from JWT, not from request parameters
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_identity_from_jwt_not_query_param(jwt_client: AsyncClient):
    """user_id query parameter is ignored; identity comes from JWT sub claim."""
    real_uid = uuid.uuid4()
    tid = uuid.uuid4()
    fake_uid = uuid.uuid4()
    token = _make_access_token(real_uid, tid)

    # Pass a different user_id in the query string
    resp = await jwt_client.get(
        f"/api/test/identity?user_id={fake_uid}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["identity"] == str(real_uid)
    assert data["identity"] != str(fake_uid)


# ---------------------------------------------------------------------------
# 8.1 RED — login endpoint integration (requires TEST_DATABASE_URL)
# ---------------------------------------------------------------------------

pytestmark_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping login integration tests",
)


@pytest_asyncio.fixture
async def login_engine():
    from app.core.database import build_engine, Base  # noqa: PLC0415
    import app.models.tenant  # noqa: PLC0415, F401
    import app.models.user  # noqa: PLC0415, F401
    import app.features.auth.models  # noqa: PLC0415, F401

    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        yield None
        return

    engine = build_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def login_integration_app(login_engine):
    if login_engine is None:
        yield None
        return

    from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: PLC0415
    from app.core.dependencies import get_db  # noqa: PLC0415
    from app.core.rate_limiter import limiter  # noqa: PLC0415
    from app.api.v1.routers.auth import router as auth_router  # noqa: PLC0415

    limiter._storage.reset()
    factory = async_sessionmaker(login_engine, expire_on_commit=False)

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    app = FastAPI(lifespan=noop_lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # Inject test settings for get_auth_service
    os.environ["SECRET_KEY"] = _SECRET_KEY
    os.environ["ENCRYPTION_KEY"] = _ENC_KEY
    os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"

    yield app


@pytest_asyncio.fixture
async def login_client(login_integration_app):
    if login_integration_app is None:
        pytest.skip("TEST_DATABASE_URL not set")
        return

    transport = ASGITransport(app=login_integration_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def login_seed(login_engine):
    if login_engine is None:
        pytest.skip("TEST_DATABASE_URL not set")
        return

    from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: PLC0415
    from app.core.security import hash_password  # noqa: PLC0415
    from app.models.tenant import Tenant  # noqa: PLC0415
    from app.models.user import User  # noqa: PLC0415

    factory = async_sessionmaker(login_engine, expire_on_commit=False)
    async with factory() as session:
        t = Tenant(slug="login-test", nombre="Login Test", activo=True)
        session.add(t)
        await session.flush()
        await session.refresh(t)

        u = User(
            tenant_id=t.id,
            email="test@example.com",
            password_hash=hash_password("correct_pass"),
            is_active=True,
        )
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return str(t.id), u


@pytest.mark.asyncio
@pytestmark_db
async def test_login_valid_credentials_returns_200(login_client: AsyncClient, login_seed):
    """POST /api/auth/login with valid credentials returns 200 with tokens."""
    tenant_id, user = login_seed

    resp = await login_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "correct_pass"},
        headers={"X-Tenant-ID": tenant_id},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data or "partial_token" in data


@pytest.mark.asyncio
@pytestmark_db
async def test_login_wrong_password_returns_401(login_client: AsyncClient, login_seed):
    """POST /api/auth/login with wrong password returns 401."""
    tenant_id, _ = login_seed

    resp = await login_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "wrong_pass"},
        headers={"X-Tenant-ID": tenant_id},
    )

    assert resp.status_code == 401

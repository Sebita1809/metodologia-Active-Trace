"""
tests/test_auth_e2e.py — End-to-end integration tests for the auth system.

TDD cycle:
  9.1 Full session flow: login → use protected endpoint → refresh → use → logout → refresh fails
  9.2 2FA full flow: login → partial_token → verify_2fa_gate → use endpoint
  9.3 Password recovery: forgot → reset → login with new password OK → old password fails
  9.4 Tenant isolation: refresh token of user A not accepted for user B (same hash, diff tenant)
  9.5 Identity immutability: endpoint uses user_id from JWT, ignores query param

Requires: TEST_DATABASE_URL (all tests use a real PostgreSQL DB).
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

import pyotp
import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping E2E auth tests",
)

_SECRET_KEY = "e2e" + "x" * 29  # 32 chars
_ENC_KEY = "cd" * 32  # 64 hex chars
_PASSWORD = "password_abc_123"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def e2e_engine() -> AsyncEngine:
    from app.core.database import build_engine, Base  # noqa: PLC0415
    import app.models.tenant  # noqa: PLC0415, F401
    import app.models.user  # noqa: PLC0415, F401
    import app.features.auth.models  # noqa: PLC0415, F401

    url = os.environ["TEST_DATABASE_URL"]
    engine = build_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def e2e_session(e2e_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(e2e_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def e2e_seed(e2e_session: AsyncSession):
    """Seed two tenants each with one user. Returns (svc1, svc2, user1, user2, t1_id, t2_id)."""
    from app.core.security import hash_password  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.features.auth.service import AuthService  # noqa: PLC0415
    from app.models.tenant import Tenant  # noqa: PLC0415
    from app.models.user import User  # noqa: PLC0415

    t1 = Tenant(slug="e2e-t1", nombre="E2E Tenant 1", activo=True)
    t2 = Tenant(slug="e2e-t2", nombre="E2E Tenant 2", activo=True)
    e2e_session.add_all([t1, t2])
    await e2e_session.flush()
    await e2e_session.refresh(t1)
    await e2e_session.refresh(t2)

    u1 = User(tenant_id=t1.id, email="alice@e2e.test", password_hash=hash_password(_PASSWORD), is_active=True)
    u2 = User(tenant_id=t2.id, email="bob@e2e.test", password_hash=hash_password(_PASSWORD), is_active=True)
    e2e_session.add_all([u1, u2])
    await e2e_session.commit()
    await e2e_session.refresh(u1)
    await e2e_session.refresh(u2)

    crypto = CryptoService(_ENC_KEY)

    svc1 = AuthService(session=e2e_session, crypto=crypto, secret_key=_SECRET_KEY, access_token_expire_minutes=15)
    svc2 = AuthService(session=e2e_session, crypto=crypto, secret_key=_SECRET_KEY, access_token_expire_minutes=15)

    return svc1, svc2, u1, u2, t1.id, t2.id


def _http_app(e2e_engine):
    """Create a test FastAPI app with real DB for E2E router tests."""
    from sqlalchemy.ext.asyncio import async_sessionmaker as sm  # noqa: PLC0415
    from app.core.dependencies import get_db, get_current_user  # noqa: PLC0415
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.core.rate_limiter import limiter  # noqa: PLC0415
    from app.api.v1.routers.auth import router as auth_router  # noqa: PLC0415
    import app.core.config as cfg  # noqa: PLC0415

    # Set test env vars for get_settings()
    os.environ["SECRET_KEY"] = _SECRET_KEY
    os.environ["ENCRYPTION_KEY"] = _ENC_KEY
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://placeholder/test")
    cfg._settings = None  # reset cache

    limiter._storage.reset()
    factory = sm(e2e_engine, expire_on_commit=False)

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

    @app.get("/api/test/me")
    async def me(user: CurrentUser = Depends(get_current_user)):
        return {"user_id": str(user.user_id), "tenant_id": str(user.tenant_id)}

    return app


@pytest_asyncio.fixture
async def http_client(e2e_engine: AsyncEngine):
    app = _http_app(e2e_engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def http_seed(e2e_engine: AsyncEngine):
    from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: PLC0415
    from app.core.security import hash_password  # noqa: PLC0415
    from app.models.tenant import Tenant  # noqa: PLC0415
    from app.models.user import User  # noqa: PLC0415

    factory = async_sessionmaker(e2e_engine, expire_on_commit=False)
    async with factory() as session:
        t1 = Tenant(slug="http-e2e-t1", nombre="HTTP E2E T1", activo=True)
        t2 = Tenant(slug="http-e2e-t2", nombre="HTTP E2E T2", activo=True)
        session.add_all([t1, t2])
        await session.flush()
        await session.refresh(t1)
        await session.refresh(t2)

        u1 = User(tenant_id=t1.id, email="alice@http.test", password_hash=hash_password(_PASSWORD), is_active=True)
        u2 = User(tenant_id=t2.id, email="bob@http.test", password_hash=hash_password(_PASSWORD), is_active=True)
        session.add_all([u1, u2])
        await session.commit()
        await session.refresh(u1)
        await session.refresh(u2)
        return str(t1.id), str(t2.id), u1, u2


# ---------------------------------------------------------------------------
# Service-level E2E fixtures (no HTTP, raw service calls)
# ---------------------------------------------------------------------------

# 9.1 Full session flow (service level)

@pytest.mark.asyncio
async def test_full_session_flow(e2e_seed):
    """login → use access token → refresh → use new token → logout → refresh fails."""
    from app.core.exceptions import AuthenticationError  # noqa: PLC0415
    from app.core.security import verify_token  # noqa: PLC0415

    svc1, _, u1, _, t1_id, _ = e2e_seed

    # Login
    login_result = await svc1.login(email="alice@e2e.test", password=_PASSWORD, tenant_id=t1_id)
    from app.features.auth.schemas import TokenResponse  # noqa: PLC0415
    assert isinstance(login_result, TokenResponse)

    # Access token is valid
    claims = verify_token(login_result.access_token, secret_key=_SECRET_KEY, expected_scope="access")
    assert claims["sub"] == str(u1.id)

    # Refresh — rotates token
    new_result = await svc1.refresh(raw_token=login_result.refresh_token, tenant_id=t1_id)
    assert new_result.refresh_token != login_result.refresh_token

    # New access token is valid
    new_claims = verify_token(new_result.access_token, secret_key=_SECRET_KEY, expected_scope="access")
    assert new_claims["sub"] == str(u1.id)

    # Logout — revokes new token
    await svc1.logout(raw_token=new_result.refresh_token, tenant_id=t1_id)

    # Refresh with revoked token fails
    with pytest.raises(AuthenticationError):
        await svc1.refresh(raw_token=new_result.refresh_token, tenant_id=t1_id)


# 9.2 2FA full flow (service level)

@pytest.mark.asyncio
async def test_2fa_full_flow(e2e_seed):
    """login → partial_token → verify_2fa_gate → full session."""
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.features.auth.repository import TotpSecretRepository  # noqa: PLC0415
    from app.features.auth.schemas import PartialTokenResponse, TokenResponse  # noqa: PLC0415

    svc1, _, u1, _, t1_id, _ = e2e_seed

    # Enroll and confirm 2FA
    await svc1.enroll_2fa(user_id=u1.id, tenant_id=t1_id, email=u1.email)
    totp_repo = TotpSecretRepository(session=svc1._session, tenant_id=t1_id)
    pending = await totp_repo.get_pending_for_user(u1.id)
    raw_secret = CryptoService(_ENC_KEY).decrypt(pending.encrypted_secret)
    current_code = pyotp.TOTP(raw_secret).now()
    await svc1.confirm_2fa(user_id=u1.id, tenant_id=t1_id, code=current_code)

    # Login → partial_token
    result = await svc1.login(email="alice@e2e.test", password=_PASSWORD, tenant_id=t1_id)
    assert isinstance(result, PartialTokenResponse)
    assert result.requires_2fa is True

    # Gate verification → full session
    full = await svc1.verify_2fa_gate(
        partial_token=result.partial_token,
        code=pyotp.TOTP(raw_secret).now(),
    )
    assert isinstance(full, TokenResponse)
    assert full.access_token


# 9.3 Password recovery flow (service level)

@pytest.mark.asyncio
async def test_password_recovery_flow(e2e_seed):
    """forgot → reset with new password → old password fails → new password works."""
    from app.core.exceptions import AuthenticationError  # noqa: PLC0415
    from app.features.auth.schemas import TokenResponse  # noqa: PLC0415

    svc1, _, _, _, t1_id, _ = e2e_seed

    raw_token = await svc1.forgot_password(email="alice@e2e.test", tenant_id=t1_id)
    assert raw_token is not None

    new_password = "new_password_xyz_456"
    await svc1.reset_password(raw_token=raw_token, new_password=new_password, tenant_id=t1_id)

    with pytest.raises(AuthenticationError):
        await svc1.login(email="alice@e2e.test", password=_PASSWORD, tenant_id=t1_id)

    result = await svc1.login(email="alice@e2e.test", password=new_password, tenant_id=t1_id)
    assert isinstance(result, TokenResponse)


# 9.4 Tenant isolation (service level)

@pytest.mark.asyncio
async def test_refresh_token_tenant_isolation_e2e(e2e_seed):
    """Refresh token of user in tenant A cannot be used from tenant B scope."""
    from app.core.exceptions import AuthenticationError  # noqa: PLC0415

    svc1, svc2, _, _, t1_id, t2_id = e2e_seed

    login_result = await svc1.login(email="alice@e2e.test", password=_PASSWORD, tenant_id=t1_id)
    raw_refresh = login_result.refresh_token

    # Tenant B tries to use tenant A's token — must fail
    with pytest.raises(AuthenticationError):
        await svc2.refresh(raw_token=raw_refresh, tenant_id=t2_id)


# 9.5 Identity immutability (HTTP level)

@pytest.mark.asyncio
async def test_identity_immutability_via_http(http_client: AsyncClient, http_seed):
    """user_id query param is ignored; JWT sub claim determines identity."""
    from app.core.security import create_access_token  # noqa: PLC0415

    t1_id, _, u1, _ = http_seed
    real_uid = u1.id
    fake_uid = uuid.uuid4()

    token = create_access_token(
        user_id=real_uid,
        tenant_id=uuid.UUID(t1_id),
        roles=[],
        secret_key=_SECRET_KEY,
        expire_minutes=15,
    )

    resp = await http_client.get(
        f"/api/test/me?user_id={fake_uid}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == str(real_uid)
    assert data["user_id"] != str(fake_uid)

"""
tests/test_auth_models.py — TDD tests for auth SQLAlchemy models.

TDD cycle:
  2.1 RED    — written before models exist; tests fail at import.
  2.2 GREEN  — implement models.py.
  2.3 TRIANGULATE — tenant_id NOT NULL, token_hash NOT NULL.

Requires: TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping auth model DB tests",
)


@pytest_asyncio.fixture
async def auth_engine() -> AsyncEngine:
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
async def auth_session(auth_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(auth_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def seed_tenant_and_user(auth_session: AsyncSession):
    from app.models.tenant import Tenant  # noqa: PLC0415
    from app.models.user import User  # noqa: PLC0415

    tenant = Tenant(slug="auth-test-tenant", nombre="Auth Test", activo=True)
    auth_session.add(tenant)
    await auth_session.flush()
    await auth_session.refresh(tenant)

    user = User(
        tenant_id=tenant.id,
        email="alice@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$test",
        is_active=True,
    )
    auth_session.add(user)
    await auth_session.commit()
    await auth_session.refresh(user)
    return tenant.id, user.id


# ---------------------------------------------------------------------------
# 2.1 RED / 2.2 GREEN — RefreshToken
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_token_persists(auth_session: AsyncSession, seed_tenant_and_user):
    from app.features.auth.models import RefreshToken  # noqa: PLC0415

    tenant_id, user_id = seed_tenant_and_user
    expires = datetime.now(tz=timezone.utc) + timedelta(days=7)
    rt = RefreshToken(
        user_id=user_id,
        tenant_id=tenant_id,
        token_hash="abc123" * 10,  # 60 chars
        expires_at=expires,
    )
    auth_session.add(rt)
    await auth_session.commit()
    await auth_session.refresh(rt)

    assert rt.id is not None
    assert isinstance(rt.id, uuid.UUID)
    assert rt.revoked_at is None
    assert rt.created_at is not None


@pytest.mark.asyncio
async def test_password_reset_token_persists(auth_session: AsyncSession, seed_tenant_and_user):
    from app.features.auth.models import PasswordResetToken  # noqa: PLC0415

    tenant_id, user_id = seed_tenant_and_user
    expires = datetime.now(tz=timezone.utc) + timedelta(minutes=15)
    prt = PasswordResetToken(
        user_id=user_id,
        tenant_id=tenant_id,
        token_hash="def456" * 10,
        expires_at=expires,
    )
    auth_session.add(prt)
    await auth_session.commit()
    await auth_session.refresh(prt)

    assert prt.id is not None
    assert prt.used_at is None
    assert prt.created_at is not None


@pytest.mark.asyncio
async def test_totp_secret_persists(auth_session: AsyncSession, seed_tenant_and_user):
    from app.features.auth.models import TotpSecret  # noqa: PLC0415

    tenant_id, user_id = seed_tenant_and_user
    ts = TotpSecret(
        user_id=user_id,
        tenant_id=tenant_id,
        encrypted_secret="encrypted_base64_value",
        confirmed=False,
    )
    auth_session.add(ts)
    await auth_session.commit()
    await auth_session.refresh(ts)

    assert ts.id is not None
    assert ts.confirmed is False
    assert ts.created_at is not None


# ---------------------------------------------------------------------------
# 2.3 TRIANGULATE — tenant_id and token_hash NOT NULL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_token_tenant_id_not_null(auth_session: AsyncSession, seed_tenant_and_user):
    """RefreshToken requires tenant_id — null raises IntegrityError."""
    from app.features.auth.models import RefreshToken  # noqa: PLC0415

    _, user_id = seed_tenant_and_user
    expires = datetime.now(tz=timezone.utc) + timedelta(days=7)
    rt = RefreshToken(
        user_id=user_id,
        tenant_id=None,
        token_hash="x" * 60,
        expires_at=expires,
    )
    auth_session.add(rt)
    with pytest.raises((IntegrityError, Exception)):
        await auth_session.flush()


@pytest.mark.asyncio
async def test_refresh_token_token_hash_not_null(auth_session: AsyncSession, seed_tenant_and_user):
    """RefreshToken requires token_hash — null raises IntegrityError."""
    from app.features.auth.models import RefreshToken  # noqa: PLC0415

    tenant_id, user_id = seed_tenant_and_user
    expires = datetime.now(tz=timezone.utc) + timedelta(days=7)
    rt = RefreshToken(
        user_id=user_id,
        tenant_id=tenant_id,
        token_hash=None,
        expires_at=expires,
    )
    auth_session.add(rt)
    with pytest.raises((IntegrityError, Exception)):
        await auth_session.flush()

"""
tests/test_auth_repository.py — TDD tests for auth repositories.

TDD cycle:
  4.1 RED    — written before repository.py exists; tests fail at import.
  4.2 GREEN  — implement RefreshTokenRepository.
  4.3 RED    — PasswordResetTokenRepository tests (also written here).
  4.4 GREEN  — implement PasswordResetTokenRepository.
  4.5 RED    — TotpSecretRepository tests (also written here).
  4.6 GREEN  — implement TotpSecretRepository.
  4.7 TRIANGULATE — tenant isolation: tokens of tenant A not visible from B.

Requires: TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping auth repository DB tests",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def auth_repo_engine() -> AsyncEngine:
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
async def auth_repo_session(auth_repo_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(auth_repo_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def seed_data(auth_repo_session: AsyncSession):
    """Create two tenants each with one user.

    Returns (tenant1_id, user1_id, tenant2_id, user2_id).
    """
    from app.models.tenant import Tenant  # noqa: PLC0415
    from app.models.user import User  # noqa: PLC0415

    t1 = Tenant(slug="repo-test-t1", nombre="Repo Test 1", activo=True)
    t2 = Tenant(slug="repo-test-t2", nombre="Repo Test 2", activo=True)
    auth_repo_session.add_all([t1, t2])
    await auth_repo_session.flush()
    await auth_repo_session.refresh(t1)
    await auth_repo_session.refresh(t2)

    u1 = User(
        tenant_id=t1.id,
        email="alice@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$test",
        is_active=True,
    )
    u2 = User(
        tenant_id=t2.id,
        email="bob@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$test",
        is_active=True,
    )
    auth_repo_session.add_all([u1, u2])
    await auth_repo_session.commit()
    await auth_repo_session.refresh(u1)
    await auth_repo_session.refresh(u2)
    return t1.id, u1.id, t2.id, u2.id


# ---------------------------------------------------------------------------
# 4.1 RED / 4.2 GREEN — RefreshTokenRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_token_repo_create(auth_repo_session: AsyncSession, seed_data):
    """create() persists a new RefreshToken and returns it with an id."""
    from app.features.auth.repository import RefreshTokenRepository  # noqa: PLC0415

    t1_id, u1_id, _, _ = seed_data
    repo = RefreshTokenRepository(session=auth_repo_session, tenant_id=t1_id)
    expires = datetime.now(tz=timezone.utc) + timedelta(days=7)

    rt = await repo.create(user_id=u1_id, token_hash="a" * 64, expires_at=expires)

    assert rt.id is not None
    assert isinstance(rt.id, uuid.UUID)
    assert rt.token_hash == "a" * 64
    assert rt.revoked_at is None


@pytest.mark.asyncio
async def test_refresh_token_repo_get_by_hash_existing(auth_repo_session: AsyncSession, seed_data):
    """get_by_hash() returns the active (non-revoked) token when it exists."""
    from app.features.auth.repository import RefreshTokenRepository  # noqa: PLC0415

    t1_id, u1_id, _, _ = seed_data
    repo = RefreshTokenRepository(session=auth_repo_session, tenant_id=t1_id)
    expires = datetime.now(tz=timezone.utc) + timedelta(days=7)

    await repo.create(user_id=u1_id, token_hash="b" * 64, expires_at=expires)
    result = await repo.get_by_hash("b" * 64)

    assert result is not None
    assert result.token_hash == "b" * 64
    assert result.tenant_id == t1_id


@pytest.mark.asyncio
async def test_refresh_token_repo_get_by_hash_nonexistent(auth_repo_session: AsyncSession, seed_data):
    """get_by_hash() returns None when no token matches the hash."""
    from app.features.auth.repository import RefreshTokenRepository  # noqa: PLC0415

    t1_id, _, _, _ = seed_data
    repo = RefreshTokenRepository(session=auth_repo_session, tenant_id=t1_id)

    result = await repo.get_by_hash("z" * 64)

    assert result is None


@pytest.mark.asyncio
async def test_refresh_token_repo_revoke(auth_repo_session: AsyncSession, seed_data):
    """revoke() sets revoked_at; subsequent get_by_hash returns None (not active)."""
    from app.features.auth.repository import RefreshTokenRepository  # noqa: PLC0415

    t1_id, u1_id, _, _ = seed_data
    repo = RefreshTokenRepository(session=auth_repo_session, tenant_id=t1_id)
    expires = datetime.now(tz=timezone.utc) + timedelta(days=7)

    await repo.create(user_id=u1_id, token_hash="c" * 64, expires_at=expires)
    await repo.revoke("c" * 64)

    result = await repo.get_by_hash("c" * 64)
    assert result is None


@pytest.mark.asyncio
async def test_refresh_token_repo_revoke_all_for_user(auth_repo_session: AsyncSession, seed_data):
    """revoke_all_for_user() revokes every active token for the given user."""
    from app.features.auth.repository import RefreshTokenRepository  # noqa: PLC0415

    t1_id, u1_id, _, _ = seed_data
    repo = RefreshTokenRepository(session=auth_repo_session, tenant_id=t1_id)
    expires = datetime.now(tz=timezone.utc) + timedelta(days=7)

    await repo.create(user_id=u1_id, token_hash="d" * 64, expires_at=expires)
    await repo.create(user_id=u1_id, token_hash="e" * 64, expires_at=expires)
    await repo.revoke_all_for_user(u1_id)

    assert await repo.get_by_hash("d" * 64) is None
    assert await repo.get_by_hash("e" * 64) is None


# ---------------------------------------------------------------------------
# 4.3 RED / 4.4 GREEN — PasswordResetTokenRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_password_reset_repo_create(auth_repo_session: AsyncSession, seed_data):
    """create() persists a PasswordResetToken with used_at=None."""
    from app.features.auth.repository import PasswordResetTokenRepository  # noqa: PLC0415

    t1_id, u1_id, _, _ = seed_data
    repo = PasswordResetTokenRepository(session=auth_repo_session, tenant_id=t1_id)
    expires = datetime.now(tz=timezone.utc) + timedelta(minutes=15)

    prt = await repo.create(user_id=u1_id, token_hash="f" * 64, expires_at=expires)

    assert prt.id is not None
    assert prt.used_at is None


@pytest.mark.asyncio
async def test_password_reset_repo_get_valid_by_hash(auth_repo_session: AsyncSession, seed_data):
    """get_valid_by_hash() returns the token when not used and not expired."""
    from app.features.auth.repository import PasswordResetTokenRepository  # noqa: PLC0415

    t1_id, u1_id, _, _ = seed_data
    repo = PasswordResetTokenRepository(session=auth_repo_session, tenant_id=t1_id)
    expires = datetime.now(tz=timezone.utc) + timedelta(minutes=15)

    await repo.create(user_id=u1_id, token_hash="g" * 64, expires_at=expires)
    result = await repo.get_valid_by_hash("g" * 64)

    assert result is not None
    assert result.token_hash == "g" * 64


@pytest.mark.asyncio
async def test_password_reset_repo_get_valid_excludes_used(auth_repo_session: AsyncSession, seed_data):
    """get_valid_by_hash() returns None when the token has been used."""
    from app.features.auth.repository import PasswordResetTokenRepository  # noqa: PLC0415

    t1_id, u1_id, _, _ = seed_data
    repo = PasswordResetTokenRepository(session=auth_repo_session, tenant_id=t1_id)
    expires = datetime.now(tz=timezone.utc) + timedelta(minutes=15)

    await repo.create(user_id=u1_id, token_hash="h" * 64, expires_at=expires)
    await repo.mark_used("h" * 64)

    result = await repo.get_valid_by_hash("h" * 64)
    assert result is None


@pytest.mark.asyncio
async def test_password_reset_repo_get_valid_excludes_expired(auth_repo_session: AsyncSession, seed_data):
    """get_valid_by_hash() returns None for an already-expired token."""
    from app.features.auth.repository import PasswordResetTokenRepository  # noqa: PLC0415

    t1_id, u1_id, _, _ = seed_data
    repo = PasswordResetTokenRepository(session=auth_repo_session, tenant_id=t1_id)
    expires = datetime.now(tz=timezone.utc) - timedelta(minutes=1)  # already expired

    await repo.create(user_id=u1_id, token_hash="i" * 64, expires_at=expires)
    result = await repo.get_valid_by_hash("i" * 64)

    assert result is None


@pytest.mark.asyncio
async def test_password_reset_repo_invalidate_previous_for_user(
    auth_repo_session: AsyncSession, seed_data
):
    """invalidate_previous_for_user() marks used all outstanding tokens for a user."""
    from app.features.auth.repository import PasswordResetTokenRepository  # noqa: PLC0415

    t1_id, u1_id, _, _ = seed_data
    repo = PasswordResetTokenRepository(session=auth_repo_session, tenant_id=t1_id)
    expires = datetime.now(tz=timezone.utc) + timedelta(minutes=15)

    await repo.create(user_id=u1_id, token_hash="j" * 64, expires_at=expires)
    await repo.invalidate_previous_for_user(u1_id)

    result = await repo.get_valid_by_hash("j" * 64)
    assert result is None


# ---------------------------------------------------------------------------
# 4.5 RED / 4.6 GREEN — TotpSecretRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_totp_repo_create_pending(auth_repo_session: AsyncSession, seed_data):
    """create_pending() persists a TotpSecret with confirmed=False."""
    from app.features.auth.repository import TotpSecretRepository  # noqa: PLC0415

    t1_id, u1_id, _, _ = seed_data
    repo = TotpSecretRepository(session=auth_repo_session, tenant_id=t1_id)

    ts = await repo.create_pending(user_id=u1_id, encrypted_secret="enc_secret_value")

    assert ts.id is not None
    assert ts.confirmed is False
    assert ts.encrypted_secret == "enc_secret_value"


@pytest.mark.asyncio
async def test_totp_repo_get_for_user_returns_none_before_confirm(
    auth_repo_session: AsyncSession, seed_data
):
    """get_for_user() returns None while enrollment is pending (confirmed=False)."""
    from app.features.auth.repository import TotpSecretRepository  # noqa: PLC0415

    t1_id, u1_id, _, _ = seed_data
    repo = TotpSecretRepository(session=auth_repo_session, tenant_id=t1_id)

    await repo.create_pending(user_id=u1_id, encrypted_secret="enc_secret")
    result = await repo.get_for_user(u1_id)

    assert result is None


@pytest.mark.asyncio
async def test_totp_repo_confirm_makes_it_active(auth_repo_session: AsyncSession, seed_data):
    """confirm() flips confirmed=True; get_for_user() then returns the secret."""
    from app.features.auth.repository import TotpSecretRepository  # noqa: PLC0415

    t1_id, u1_id, _, _ = seed_data
    repo = TotpSecretRepository(session=auth_repo_session, tenant_id=t1_id)

    ts = await repo.create_pending(user_id=u1_id, encrypted_secret="enc_secret")
    await repo.confirm(ts.id)

    result = await repo.get_for_user(u1_id)
    assert result is not None
    assert result.confirmed is True


@pytest.mark.asyncio
async def test_totp_repo_get_pending_for_user(auth_repo_session: AsyncSession, seed_data):
    """get_pending_for_user() returns the unconfirmed TotpSecret."""
    from app.features.auth.repository import TotpSecretRepository  # noqa: PLC0415

    t1_id, u1_id, _, _ = seed_data
    repo = TotpSecretRepository(session=auth_repo_session, tenant_id=t1_id)

    await repo.create_pending(user_id=u1_id, encrypted_secret="pending_secret")
    result = await repo.get_pending_for_user(u1_id)

    assert result is not None
    assert result.confirmed is False


# ---------------------------------------------------------------------------
# 4.7 TRIANGULATE — tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_token_tenant_isolation(auth_repo_session: AsyncSession, seed_data):
    """Refresh tokens created for tenant A are not visible from tenant B scope."""
    from app.features.auth.repository import RefreshTokenRepository  # noqa: PLC0415

    t1_id, u1_id, t2_id, _ = seed_data
    repo1 = RefreshTokenRepository(session=auth_repo_session, tenant_id=t1_id)
    repo2 = RefreshTokenRepository(session=auth_repo_session, tenant_id=t2_id)
    expires = datetime.now(tz=timezone.utc) + timedelta(days=7)

    await repo1.create(user_id=u1_id, token_hash="k" * 64, expires_at=expires)

    result = await repo2.get_by_hash("k" * 64)
    assert result is None


@pytest.mark.asyncio
async def test_password_reset_token_tenant_isolation(auth_repo_session: AsyncSession, seed_data):
    """Password reset tokens of tenant A are not visible from tenant B scope."""
    from app.features.auth.repository import PasswordResetTokenRepository  # noqa: PLC0415

    t1_id, u1_id, t2_id, _ = seed_data
    repo1 = PasswordResetTokenRepository(session=auth_repo_session, tenant_id=t1_id)
    repo2 = PasswordResetTokenRepository(session=auth_repo_session, tenant_id=t2_id)
    expires = datetime.now(tz=timezone.utc) + timedelta(minutes=15)

    await repo1.create(user_id=u1_id, token_hash="l" * 64, expires_at=expires)

    result = await repo2.get_valid_by_hash("l" * 64)
    assert result is None


@pytest.mark.asyncio
async def test_totp_secret_tenant_isolation(auth_repo_session: AsyncSession, seed_data):
    """TOTP secrets confirmed for tenant A are not visible from tenant B scope."""
    from app.features.auth.repository import TotpSecretRepository  # noqa: PLC0415

    t1_id, u1_id, t2_id, _ = seed_data
    repo1 = TotpSecretRepository(session=auth_repo_session, tenant_id=t1_id)
    repo2 = TotpSecretRepository(session=auth_repo_session, tenant_id=t2_id)

    ts = await repo1.create_pending(user_id=u1_id, encrypted_secret="secret_t1")
    await repo1.confirm(ts.id)

    result = await repo2.get_for_user(u1_id)
    assert result is None

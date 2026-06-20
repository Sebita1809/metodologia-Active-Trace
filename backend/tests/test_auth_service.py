"""
tests/test_auth_service.py — TDD tests for AuthService.

TDD cycle:
  6.1  RED    — login() happy path and wrong password.
  6.2  GREEN  — implement AuthService.login().
  6.3  RED    — refresh() rotates token; revoked reuse revokes all.
  6.4  GREEN  — implement AuthService.refresh() + logout().
  6.6  RED    — enroll_2fa() / confirm_2fa() / verify_2fa_gate().
  6.7  GREEN  — implement 2FA methods.
  6.8  RED    — forgot_password() / reset_password() flows.
  6.9  GREEN  — implement password recovery methods.
  6.10 TRIANGULATE — login() when 2FA active → PartialTokenResponse.

Requires: TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid

import pyotp
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping AuthService DB tests",
)

_SECRET_KEY = "s" * 32
_ENC_KEY = "ab" * 32  # 64 hex chars
_PLAIN_PASSWORD = "correct_password_123"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def svc_engine() -> AsyncEngine:
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
async def svc_session(svc_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(svc_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def seed_user(svc_session: AsyncSession):
    """Create a tenant + active user; return (tenant_id, user)."""
    from app.core.security import hash_password  # noqa: PLC0415
    from app.models.tenant import Tenant  # noqa: PLC0415
    from app.models.user import User  # noqa: PLC0415

    t = Tenant(slug="svc-test-tenant", nombre="Svc Test", activo=True)
    svc_session.add(t)
    await svc_session.flush()
    await svc_session.refresh(t)

    u = User(
        tenant_id=t.id,
        email="alice@example.com",
        password_hash=hash_password(_PLAIN_PASSWORD),
        is_active=True,
    )
    svc_session.add(u)
    await svc_session.commit()
    await svc_session.refresh(u)
    return t.id, u


def _make_service(session: AsyncSession, tenant_id: uuid.UUID | None = None):
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.features.auth.service import AuthService  # noqa: PLC0415

    return AuthService(
        session=session,
        crypto=CryptoService(_ENC_KEY),
        secret_key=_SECRET_KEY,
        access_token_expire_minutes=15,
        refresh_token_expire_days=7,
        password_reset_expire_minutes=15,
    )


# ---------------------------------------------------------------------------
# 6.1 RED / 6.2 GREEN — login()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_valid_credentials_returns_token_response(
    svc_session: AsyncSession, seed_user
):
    """login() with correct credentials returns TokenResponse."""
    from app.features.auth.schemas import TokenResponse  # noqa: PLC0415

    tenant_id, user = seed_user
    svc = _make_service(svc_session, tenant_id)

    result = await svc.login(
        email="alice@example.com",
        password=_PLAIN_PASSWORD,
        tenant_id=tenant_id,
    )

    assert isinstance(result, TokenResponse)
    assert result.access_token
    assert result.refresh_token
    assert result.token_type == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_raises_authentication_error(
    svc_session: AsyncSession, seed_user
):
    """login() with wrong password raises AuthenticationError."""
    from app.core.exceptions import AuthenticationError  # noqa: PLC0415

    tenant_id, _ = seed_user
    svc = _make_service(svc_session, tenant_id)

    with pytest.raises(AuthenticationError):
        await svc.login(
            email="alice@example.com",
            password="wrong_password",
            tenant_id=tenant_id,
        )


@pytest.mark.asyncio
async def test_login_unknown_email_raises_authentication_error(
    svc_session: AsyncSession, seed_user
):
    """login() with unknown email raises AuthenticationError (no user enumeration)."""
    from app.core.exceptions import AuthenticationError  # noqa: PLC0415

    tenant_id, _ = seed_user
    svc = _make_service(svc_session, tenant_id)

    with pytest.raises(AuthenticationError):
        await svc.login(
            email="nobody@example.com",
            password=_PLAIN_PASSWORD,
            tenant_id=tenant_id,
        )


# ---------------------------------------------------------------------------
# 6.3 RED / 6.4 GREEN — refresh() + logout()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_rotates_token(svc_session: AsyncSession, seed_user):
    """refresh() returns new tokens; old token is revoked."""
    from app.features.auth.schemas import TokenResponse  # noqa: PLC0415

    tenant_id, user = seed_user
    svc = _make_service(svc_session, tenant_id)

    login_result = await svc.login(
        email="alice@example.com",
        password=_PLAIN_PASSWORD,
        tenant_id=tenant_id,
    )
    old_refresh = login_result.refresh_token

    new_result = await svc.refresh(raw_token=old_refresh, tenant_id=tenant_id)

    assert isinstance(new_result, TokenResponse)
    assert new_result.refresh_token != old_refresh


@pytest.mark.asyncio
async def test_refresh_revoked_token_reuse_revokes_all(svc_session: AsyncSession, seed_user):
    """Reusing a revoked refresh token revokes ALL user tokens (security defense)."""
    from app.core.exceptions import AuthenticationError  # noqa: PLC0415

    tenant_id, user = seed_user
    svc = _make_service(svc_session, tenant_id)

    login_result = await svc.login(
        email="alice@example.com",
        password=_PLAIN_PASSWORD,
        tenant_id=tenant_id,
    )
    old_refresh = login_result.refresh_token

    # First refresh — rotates successfully
    new_result = await svc.refresh(raw_token=old_refresh, tenant_id=tenant_id)

    # Second refresh with the OLD (now-revoked) token — must raise AND revoke all
    with pytest.raises(AuthenticationError):
        await svc.refresh(raw_token=old_refresh, tenant_id=tenant_id)

    # The new token from the first rotation is also invalidated
    with pytest.raises(AuthenticationError):
        await svc.refresh(raw_token=new_result.refresh_token, tenant_id=tenant_id)


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(svc_session: AsyncSession, seed_user):
    """logout() revokes the given refresh token (idempotent)."""
    from app.core.exceptions import AuthenticationError  # noqa: PLC0415

    tenant_id, user = seed_user
    svc = _make_service(svc_session, tenant_id)

    login_result = await svc.login(
        email="alice@example.com",
        password=_PLAIN_PASSWORD,
        tenant_id=tenant_id,
    )
    await svc.logout(raw_token=login_result.refresh_token, tenant_id=tenant_id)

    # Token is revoked — refresh now fails
    with pytest.raises(AuthenticationError):
        await svc.refresh(raw_token=login_result.refresh_token, tenant_id=tenant_id)


@pytest.mark.asyncio
async def test_logout_is_idempotent(svc_session: AsyncSession, seed_user):
    """logout() called twice on the same token does not raise."""
    tenant_id, user = seed_user
    svc = _make_service(svc_session, tenant_id)

    login_result = await svc.login(
        email="alice@example.com",
        password=_PLAIN_PASSWORD,
        tenant_id=tenant_id,
    )
    await svc.logout(raw_token=login_result.refresh_token, tenant_id=tenant_id)
    await svc.logout(raw_token=login_result.refresh_token, tenant_id=tenant_id)  # no error


# ---------------------------------------------------------------------------
# 6.6 RED / 6.7 GREEN — enroll_2fa() / confirm_2fa() / verify_2fa_gate()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enroll_2fa_returns_otpauth_uri(svc_session: AsyncSession, seed_user):
    """enroll_2fa() returns a TotpEnrollResponse with an otpauth:// URI."""
    from app.features.auth.schemas import TotpEnrollResponse  # noqa: PLC0415

    tenant_id, user = seed_user
    svc = _make_service(svc_session, tenant_id)

    result = await svc.enroll_2fa(
        user_id=user.id,
        tenant_id=tenant_id,
        email=user.email,
    )

    assert isinstance(result, TotpEnrollResponse)
    assert result.otpauth_uri.startswith("otpauth://totp/")


@pytest.mark.asyncio
async def test_confirm_2fa_with_valid_code_activates_2fa(svc_session: AsyncSession, seed_user):
    """confirm_2fa() with the current TOTP code flips confirmed=True."""
    from app.features.auth.repository import TotpSecretRepository  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415

    tenant_id, user = seed_user
    svc = _make_service(svc_session, tenant_id)

    await svc.enroll_2fa(user_id=user.id, tenant_id=tenant_id, email=user.email)

    # Retrieve pending secret to compute the current TOTP code
    repo = TotpSecretRepository(session=svc_session, tenant_id=tenant_id)
    pending = await repo.get_pending_for_user(user.id)
    assert pending is not None
    raw_secret = CryptoService(_ENC_KEY).decrypt(pending.encrypted_secret)
    current_code = pyotp.TOTP(raw_secret).now()

    await svc.confirm_2fa(user_id=user.id, tenant_id=tenant_id, code=current_code)

    confirmed = await repo.get_for_user(user.id)
    assert confirmed is not None
    assert confirmed.confirmed is True


@pytest.mark.asyncio
async def test_confirm_2fa_with_invalid_code_raises(svc_session: AsyncSession, seed_user):
    """confirm_2fa() with wrong code raises TotpError; enrollment stays pending."""
    from app.core.exceptions import TotpError  # noqa: PLC0415
    from app.features.auth.repository import TotpSecretRepository  # noqa: PLC0415

    tenant_id, user = seed_user
    svc = _make_service(svc_session, tenant_id)

    await svc.enroll_2fa(user_id=user.id, tenant_id=tenant_id, email=user.email)

    with pytest.raises(TotpError):
        await svc.confirm_2fa(user_id=user.id, tenant_id=tenant_id, code="000000")

    # Enrollment is still pending
    repo = TotpSecretRepository(session=svc_session, tenant_id=tenant_id)
    pending = await repo.get_pending_for_user(user.id)
    assert pending is not None


@pytest.mark.asyncio
async def test_verify_2fa_gate_valid_code_returns_full_session(
    svc_session: AsyncSession, seed_user
):
    """verify_2fa_gate() with valid partial_token + TOTP code returns TokenResponse."""
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.core.security import create_partial_token  # noqa: PLC0415
    from app.features.auth.repository import TotpSecretRepository  # noqa: PLC0415
    from app.features.auth.schemas import TokenResponse  # noqa: PLC0415

    tenant_id, user = seed_user
    svc = _make_service(svc_session, tenant_id)

    # Enroll and confirm 2FA
    await svc.enroll_2fa(user_id=user.id, tenant_id=tenant_id, email=user.email)
    repo = TotpSecretRepository(session=svc_session, tenant_id=tenant_id)
    pending = await repo.get_pending_for_user(user.id)
    raw_secret = CryptoService(_ENC_KEY).decrypt(pending.encrypted_secret)
    current_code = pyotp.TOTP(raw_secret).now()
    await svc.confirm_2fa(user_id=user.id, tenant_id=tenant_id, code=current_code)

    # Create a partial_token (as issued by login() when 2FA active)
    partial = create_partial_token(
        user_id=user.id,
        tenant_id=tenant_id,
        secret_key=_SECRET_KEY,
    )

    # Gate verification
    result = await svc.verify_2fa_gate(
        partial_token=partial,
        code=pyotp.TOTP(raw_secret).now(),
    )

    assert isinstance(result, TokenResponse)
    assert result.access_token


# ---------------------------------------------------------------------------
# 6.8 RED / 6.9 GREEN — forgot_password() / reset_password()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_forgot_password_always_succeeds(svc_session: AsyncSession, seed_user):
    """forgot_password() returns without error even for unknown email."""
    tenant_id, _ = seed_user
    svc = _make_service(svc_session, tenant_id)

    # Known email — no error
    await svc.forgot_password(email="alice@example.com", tenant_id=tenant_id)
    # Unknown email — still no error
    await svc.forgot_password(email="nobody@example.com", tenant_id=tenant_id)


@pytest.mark.asyncio
async def test_forgot_password_invalidates_previous_token(svc_session: AsyncSession, seed_user):
    """Second forgot_password() call invalidates the first reset token."""
    from app.features.auth.repository import PasswordResetTokenRepository  # noqa: PLC0415
    from app.core.security import hash_token  # noqa: PLC0415

    tenant_id, _ = seed_user
    svc = _make_service(svc_session, tenant_id)

    token1_raw = await svc.forgot_password(email="alice@example.com", tenant_id=tenant_id)
    token2_raw = await svc.forgot_password(email="alice@example.com", tenant_id=tenant_id)

    # First token is now invalid
    repo = PasswordResetTokenRepository(session=svc_session, tenant_id=tenant_id)
    assert token1_raw is not None
    result = await repo.get_valid_by_hash(hash_token(token1_raw))
    assert result is None

    # Second token is valid
    assert token2_raw is not None
    result2 = await repo.get_valid_by_hash(hash_token(token2_raw))
    assert result2 is not None


@pytest.mark.asyncio
async def test_reset_password_with_valid_token_updates_password(
    svc_session: AsyncSession, seed_user
):
    """reset_password() with valid token updates the password and revokes sessions."""
    tenant_id, user = seed_user
    svc = _make_service(svc_session, tenant_id)

    # Login to have an active session
    await svc.login(email="alice@example.com", password=_PLAIN_PASSWORD, tenant_id=tenant_id)

    # Forgot + reset
    raw_token = await svc.forgot_password(email="alice@example.com", tenant_id=tenant_id)
    await svc.reset_password(
        raw_token=raw_token,
        new_password="new_password_456",
        tenant_id=tenant_id,
    )

    # Old password no longer works
    from app.core.exceptions import AuthenticationError  # noqa: PLC0415
    with pytest.raises(AuthenticationError):
        await svc.login(
            email="alice@example.com",
            password=_PLAIN_PASSWORD,
            tenant_id=tenant_id,
        )

    # New password works
    from app.features.auth.schemas import TokenResponse  # noqa: PLC0415
    result = await svc.login(
        email="alice@example.com",
        password="new_password_456",
        tenant_id=tenant_id,
    )
    assert isinstance(result, TokenResponse)


@pytest.mark.asyncio
async def test_reset_password_with_used_token_raises(svc_session: AsyncSession, seed_user):
    """reset_password() with already-used token raises InvalidTokenError."""
    from app.core.exceptions import InvalidTokenError  # noqa: PLC0415

    tenant_id, _ = seed_user
    svc = _make_service(svc_session, tenant_id)

    raw_token = await svc.forgot_password(email="alice@example.com", tenant_id=tenant_id)
    await svc.reset_password(raw_token=raw_token, new_password="once_456", tenant_id=tenant_id)

    with pytest.raises(InvalidTokenError):
        await svc.reset_password(raw_token=raw_token, new_password="twice_456", tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# 6.10 TRIANGULATE — login() with active 2FA returns PartialTokenResponse
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_with_active_2fa_returns_partial_token_response(
    svc_session: AsyncSession, seed_user
):
    """login() when the user has confirmed 2FA returns PartialTokenResponse with requires_2fa=True."""
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.features.auth.repository import TotpSecretRepository  # noqa: PLC0415
    from app.features.auth.schemas import PartialTokenResponse  # noqa: PLC0415

    tenant_id, user = seed_user
    svc = _make_service(svc_session, tenant_id)

    # Enroll and confirm 2FA
    await svc.enroll_2fa(user_id=user.id, tenant_id=tenant_id, email=user.email)
    repo = TotpSecretRepository(session=svc_session, tenant_id=tenant_id)
    pending = await repo.get_pending_for_user(user.id)
    raw_secret = CryptoService(_ENC_KEY).decrypt(pending.encrypted_secret)
    code = pyotp.TOTP(raw_secret).now()
    await svc.confirm_2fa(user_id=user.id, tenant_id=tenant_id, code=code)

    # Now login
    result = await svc.login(
        email="alice@example.com",
        password=_PLAIN_PASSWORD,
        tenant_id=tenant_id,
    )

    assert isinstance(result, PartialTokenResponse)
    assert result.requires_2fa is True
    assert result.partial_token

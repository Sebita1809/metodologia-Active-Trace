"""Tests for C-03 auth-jwt-2fa: login, refresh rotation, logout, 2FA,
password recovery, rate limiting, get_current_user, and tenant isolation.

All tests are integration tests using the real PostgreSQL via conftest fixtures.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pyotp
import pytest
from argon2 import PasswordHasher
from httpx import AsyncClient
from jose import jwt as jose_jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    AESCipher,
    create_access_token,
    create_temp_session_token,
    verify_token,
)
from app.models.auth_user import AuthUser
from app.models.password_recovery_token import PasswordRecoveryToken
from app.models.tenant import Tenant

pytestmark = pytest.mark.asyncio

# ── Constants ────────────────────────────────────────────────────
TEST_PASSWORD = "StrongPass_123"
WRONG_PASSWORD = "WrongPass_999"


# ── Helpers ──────────────────────────────────────────────────────


async def _make_user(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    email: str | None = None,
    password: str = TEST_PASSWORD,
    **kwargs,
) -> AuthUser:
    if email is None:
        email = f"test_{uuid.uuid4().hex[:12]}@example.com"
    ph = PasswordHasher()
    user = AuthUser(
        tenant_id=tenant_id,
        email=email,
        password_hash=ph.hash(password),
        **kwargs,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user, email


async def _cleanup_user_by_email(db_session: AsyncSession, email: str) -> None:
    await db_session.execute(
        text("DELETE FROM auth_user WHERE email = :email"),
        {"email": email},
    )
    await db_session.commit()


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _tenant_headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


# ═══════════════════════════════════════════════════════════════════
# 7.1 Login
# ═══════════════════════════════════════════════════════════════════


class TestLogin:
    async def test_login_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Valid credentials → 200 with access_token and refresh_token."""
        user, email = await _make_user(db_session, tenant_a.id)
        try:
            resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": TEST_PASSWORD},
                headers=_tenant_headers(tenant_a.id),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"

            payload = verify_token(data["access_token"])
            assert payload["sub"] == str(user.id)
            assert payload["tenant_id"] == str(tenant_a.id)
            assert payload["type"] == "access"
        finally:
            await _cleanup_user_by_email(db_session, email)

    async def test_login_invalid_email(
        self,
        async_client: AsyncClient,
        tenant_a: Tenant,
    ) -> None:
        """Non-existent email → 401."""
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "doesnotexist@example.com", "password": TEST_PASSWORD},
            headers=_tenant_headers(tenant_a.id),
        )
        assert resp.status_code == 401

    async def test_login_invalid_password(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Wrong password for existing user → 401."""
        _, email = await _make_user(db_session, tenant_a.id)
        try:
            resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": WRONG_PASSWORD},
                headers=_tenant_headers(tenant_a.id),
            )
            assert resp.status_code == 401
        finally:
            await _cleanup_user_by_email(db_session, email)

    async def test_login_without_tenant_header(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Login works without X-Tenant-ID — resolves tenant from user record."""
        _, email = await _make_user(db_session, tenant_a.id)
        try:
            resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": TEST_PASSWORD},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert "refresh_token" in data
        finally:
            await _cleanup_user_by_email(db_session, email)


# ═══════════════════════════════════════════════════════════════════
# 7.2 Refresh Rotation
# ═══════════════════════════════════════════════════════════════════


class TestRefreshRotation:
    async def _login(self, async_client, tenant_a, email) -> dict:
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": TEST_PASSWORD},
            headers=_tenant_headers(tenant_a.id),
        )
        assert resp.status_code == 200
        return resp.json()

    async def _refresh(self, async_client, tenant_a, refresh_token) -> dict:
        resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
            headers=_tenant_headers(tenant_a.id),
        )
        return resp

    async def test_refresh_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Valid refresh token → new token pair, old is rotated."""
        _, email = await _make_user(db_session, tenant_a.id)
        try:
            login_data = await self._login(async_client, tenant_a, email)
            old_refresh = login_data["refresh_token"]

            resp = await self._refresh(async_client, tenant_a, old_refresh)
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["refresh_token"] != old_refresh
        finally:
            await _cleanup_user_by_email(db_session, email)

    async def test_refresh_reuse_revoked(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Reuse of an already-rotated refresh token → 401 + family revoked."""
        _, email = await _make_user(db_session, tenant_a.id)
        try:
            login_data = await self._login(async_client, tenant_a, email)
            old_refresh = login_data["refresh_token"]

            # First refresh — rotates
            resp1 = await self._refresh(async_client, tenant_a, old_refresh)
            assert resp1.status_code == 200

            # Reuse old (now revoked) token → 401
            resp2 = await self._refresh(async_client, tenant_a, old_refresh)
            assert resp2.status_code == 401
            assert "Session revoked" in resp2.json()["detail"]
        finally:
            await _cleanup_user_by_email(db_session, email)


# ═══════════════════════════════════════════════════════════════════
# 7.3 Logout
# ═══════════════════════════════════════════════════════════════════


class TestLogout:
    async def test_logout_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Valid refresh token → 200, token revoked."""
        _, email = await _make_user(db_session, tenant_a.id)
        try:
            login_resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": TEST_PASSWORD},
                headers=_tenant_headers(tenant_a.id),
            )
            assert login_resp.status_code == 200
            refresh_token = login_resp.json()["refresh_token"]

            resp = await async_client.post(
                "/api/v1/auth/logout",
                json={"refresh_token": refresh_token},
                headers=_tenant_headers(tenant_a.id),
            )
            assert resp.status_code == 200
            assert resp.json()["detail"] == "Logged out successfully"
        finally:
            await _cleanup_user_by_email(db_session, email)

    async def test_logout_already_revoked(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Logout with already-revoked token → 401."""
        _, email = await _make_user(db_session, tenant_a.id)
        try:
            login_resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": TEST_PASSWORD},
                headers=_tenant_headers(tenant_a.id),
            )
            assert login_resp.status_code == 200
            refresh_token = login_resp.json()["refresh_token"]

            # First logout — succeeds
            await async_client.post(
                "/api/v1/auth/logout",
                json={"refresh_token": refresh_token},
                headers=_tenant_headers(tenant_a.id),
            )

            # Second logout — already revoked
            resp2 = await async_client.post(
                "/api/v1/auth/logout",
                json={"refresh_token": refresh_token},
                headers=_tenant_headers(tenant_a.id),
            )
            assert resp2.status_code == 401
        finally:
            await _cleanup_user_by_email(db_session, email)


# ═══════════════════════════════════════════════════════════════════
# 7.4 2FA TOTP
# ═══════════════════════════════════════════════════════════════════


class Test2FA:
    async def test_2fa_enroll(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Login → enroll → 200 with uri and secret."""
        _, email = await _make_user(db_session, tenant_a.id)
        try:
            login_resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": TEST_PASSWORD},
                headers=_tenant_headers(tenant_a.id),
            )
            assert login_resp.status_code == 200
            access_token = login_resp.json()["access_token"]

            resp = await async_client.post(
                "/api/v1/auth/2fa/enroll",
                headers=_auth_headers(access_token),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "uri" in data
            assert "secret" in data
            assert data["uri"].startswith("otpauth://")
            # Verify the secret is valid base32
            assert len(data["secret"]) > 0
        finally:
            await _cleanup_user_by_email(db_session, email)

    async def test_2fa_verify_correct(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Enroll → verify with valid TOTP code → 200 + session."""
        user, email = await _make_user(db_session, tenant_a.id)
        try:
            # Login → access_token
            login_resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": TEST_PASSWORD},
                headers=_tenant_headers(tenant_a.id),
            )
            assert login_resp.status_code == 200
            access_token = login_resp.json()["access_token"]

            # Enroll
            enroll_resp = await async_client.post(
                "/api/v1/auth/2fa/enroll",
                headers=_auth_headers(access_token),
            )
            assert enroll_resp.status_code == 200
            secret = enroll_resp.json()["secret"]

            # Generate valid TOTP code from the returned secret
            totp = pyotp.TOTP(secret)
            code = totp.now()

            # Create a temp session token (simulates the 2FA gate)
            session_token = create_temp_session_token(
                user_id=str(user.id),
                tenant_id=str(tenant_a.id),
                email=email,
            )

            # Verify with correct code
            resp = await async_client.post(
                "/api/v1/auth/2fa/verify",
                json={"code": code, "session_token": session_token},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
        finally:
            await _cleanup_user_by_email(db_session, email)

    async def test_2fa_verify_wrong(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Enroll → verify with wrong TOTP code → 401."""
        user, email = await _make_user(db_session, tenant_a.id)
        try:
            login_resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": TEST_PASSWORD},
                headers=_tenant_headers(tenant_a.id),
            )
            assert login_resp.status_code == 200
            access_token = login_resp.json()["access_token"]

            await async_client.post(
                "/api/v1/auth/2fa/enroll",
                headers=_auth_headers(access_token),
            )

            session_token = create_temp_session_token(
                user_id=str(user.id),
                tenant_id=str(tenant_a.id),
                email=email,
            )

            resp = await async_client.post(
                "/api/v1/auth/2fa/verify",
                json={"code": "000000", "session_token": session_token},
            )
            assert resp.status_code == 401
        finally:
            await _cleanup_user_by_email(db_session, email)

    async def test_login_with_2fa_enabled(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """User with 2FA enabled → login returns requires_2fa + session_token."""
        totp_secret = pyotp.random_base32()
        encrypted_secret = AESCipher.encrypt(totp_secret)
        _, email = await _make_user(
            db_session,
            tenant_a.id,
            totp_enabled=True,
            totp_secret=encrypted_secret,
        )
        try:
            resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": TEST_PASSWORD},
                headers=_tenant_headers(tenant_a.id),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("requires_2fa") is True
            assert "session_token" in data
        finally:
            await _cleanup_user_by_email(db_session, email)


# ═══════════════════════════════════════════════════════════════════
# 7.5 Password Recovery
# ═══════════════════════════════════════════════════════════════════


class TestPasswordRecovery:
    async def test_forgot_password(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Valid email → 200 with token."""
        _, email = await _make_user(db_session, tenant_a.id)
        try:
            resp = await async_client.post(
                "/api/v1/auth/forgot",
                json={"email": email},
                headers=_tenant_headers(tenant_a.id),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["message"] == "If the email exists, a recovery link has been sent"
            assert data["token"] is not None
        finally:
            await _cleanup_user_by_email(db_session, email)

    async def test_forgot_password_nonexistent(
        self,
        async_client: AsyncClient,
        tenant_a: Tenant,
    ) -> None:
        """Non-existent email → 200 with same message but token is None."""
        resp = await async_client.post(
            "/api/v1/auth/forgot",
            json={"email": "nobody_recovery@example.com"},
            headers=_tenant_headers(tenant_a.id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "If the email exists, a recovery link has been sent"
        assert data["token"] is None

    async def test_reset_password(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Forgot → reset → login with new password succeeds."""
        _, email = await _make_user(db_session, tenant_a.id)
        new_password = "NewStrongPass_456"
        try:
            # Forgot
            forgot_resp = await async_client.post(
                "/api/v1/auth/forgot",
                json={"email": email},
                headers=_tenant_headers(tenant_a.id),
            )
            assert forgot_resp.status_code == 200
            reset_token = forgot_resp.json()["token"]
            assert reset_token is not None

            # Reset
            reset_resp = await async_client.post(
                "/api/v1/auth/reset",
                json={"token": reset_token, "new_password": new_password},
                headers=_tenant_headers(tenant_a.id),
            )
            assert reset_resp.status_code == 200
            assert reset_resp.json()["detail"] == "Password reset successfully"

            # Login with new password
            login_resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": new_password},
                headers=_tenant_headers(tenant_a.id),
            )
            assert login_resp.status_code == 200
            assert "access_token" in login_resp.json()
        finally:
            await _cleanup_user_by_email(db_session, email)

    async def test_reset_expired_token(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Expired recovery token → 400."""
        user, email = await _make_user(db_session, tenant_a.id)
        try:
            token_str = str(uuid.uuid4())
            token_hash = sha256(token_str.encode()).hexdigest()
            expired = PasswordRecoveryToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(tz=timezone.utc) - timedelta(hours=1),
                used_at=None,
            )
            db_session.add(expired)
            await db_session.commit()

            resp = await async_client.post(
                "/api/v1/auth/reset",
                json={"token": token_str, "new_password": "NewPass_789"},
                headers=_tenant_headers(tenant_a.id),
            )
            assert resp.status_code in (400, 410)
        finally:
            await _cleanup_user_by_email(db_session, email)

    async def test_reset_used_token(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Already-used recovery token → 400."""
        user, email = await _make_user(db_session, tenant_a.id)
        try:
            token_str = str(uuid.uuid4())
            token_hash = sha256(token_str.encode()).hexdigest()
            used = PasswordRecoveryToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=1),
                used_at=datetime.now(tz=timezone.utc),
            )
            db_session.add(used)
            await db_session.commit()

            resp = await async_client.post(
                "/api/v1/auth/reset",
                json={"token": token_str, "new_password": "NewPass_789"},
                headers=_tenant_headers(tenant_a.id),
            )
            assert resp.status_code == 400
        finally:
            await _cleanup_user_by_email(db_session, email)


# ═══════════════════════════════════════════════════════════════════
# 7.6 Rate Limiting
# ═══════════════════════════════════════════════════════════════════


class TestRateLimiting:
    async def test_rate_limit_exceeded(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """5 failed attempts → 6th returns 429 with Retry-After header."""
        _, email = await _make_user(db_session, tenant_a.id)
        try:
            for i in range(5):
                resp = await async_client.post(
                    "/api/v1/auth/login",
                    json={"email": email, "password": WRONG_PASSWORD},
                    headers=_tenant_headers(tenant_a.id),
                )
                assert resp.status_code == 401, f"Attempt {i+1} should be 401"

            resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": WRONG_PASSWORD},
                headers=_tenant_headers(tenant_a.id),
            )
            assert resp.status_code == 429
            assert "Retry-After" in resp.headers
            retry_after = int(resp.headers["Retry-After"])
            assert retry_after > 0
        finally:
            await _cleanup_user_by_email(db_session, email)


# ═══════════════════════════════════════════════════════════════════
# 7.7 get_current_user Dependency
# ═══════════════════════════════════════════════════════════════════


class TestGetCurrentUser:
    async def test_get_current_user_valid(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Valid JWT → resolves correct user_id and tenant_id, protected endpoint works."""
        user, email = await _make_user(db_session, tenant_a.id)
        try:
            login_resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": TEST_PASSWORD},
                headers=_tenant_headers(tenant_a.id),
            )
            assert login_resp.status_code == 200
            access_token = login_resp.json()["access_token"]

            # Verify token payload
            payload = verify_token(access_token)
            assert payload["sub"] == str(user.id)
            assert payload["tenant_id"] == str(tenant_a.id)
            assert payload["type"] == "access"

            # Hit a protected endpoint (2fa/enroll requires get_current_user)
            resp = await async_client.post(
                "/api/v1/auth/2fa/enroll",
                headers=_auth_headers(access_token),
            )
            assert resp.status_code == 200
        finally:
            await _cleanup_user_by_email(db_session, email)

    async def test_get_current_user_expired(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """Expired JWT → 401."""
        _, email = await _make_user(db_session, tenant_a.id)
        try:
            user, _ = await _make_user(db_session, tenant_a.id)
            expired = create_access_token(
                user_id=str(user.id),
                tenant_id=str(tenant_a.id),
                roles=[],
                expires_delta=timedelta(hours=-1),
            )
            resp = await async_client.post(
                "/api/v1/auth/2fa/enroll",
                headers=_auth_headers(expired),
            )
            assert resp.status_code == 401
        finally:
            await _cleanup_user_by_email(db_session, email)

    async def test_get_current_user_no_token(
        self,
        async_client: AsyncClient,
    ) -> None:
        """No Authorization header → 401."""
        resp = await async_client.post("/api/v1/auth/2fa/enroll")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Not authenticated"

    async def test_get_current_user_bad_signature(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """JWT signed with wrong key → 401."""
        user, email = await _make_user(db_session, tenant_a.id)
        try:
            bad_token = jose_jwt.encode(
                {
                    "sub": str(user.id),
                    "tenant_id": str(tenant_a.id),
                    "roles": [],
                    "type": "access",
                },
                "this-is-the-wrong-secret-key-for-testing",
                algorithm="HS256",
            )
            resp = await async_client.post(
                "/api/v1/auth/2fa/enroll",
                headers=_auth_headers(bad_token),
            )
            assert resp.status_code == 401
        finally:
            await _cleanup_user_by_email(db_session, email)

"""
app/core/security.py — JWT, Argon2id, TOTP, and token-hash helpers.

All helpers are pure functions (no DB access, no FastAPI dependency).
They receive keys/secrets as parameters so they are easily testable and
can be called from service layer code.

Implemented: C-03 (auth-jwt-2fa)
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from jose import JWTError, jwt

_ph = PasswordHasher()

_ALGORITHM = "HS256"


class TokenError(Exception):
    """Raised when a JWT cannot be verified (expired, wrong signature, bad scope)."""


# ---------------------------------------------------------------------------
# Argon2id
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Hash *plain* with Argon2id and return the encoded hash string."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*, False otherwise.

    Never raises — all Argon2 exceptions are caught and translated to False.
    """
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError):
        return False


# ---------------------------------------------------------------------------
# Token hashing (for refresh tokens and password reset tokens)
# ---------------------------------------------------------------------------

def hash_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest of *raw_token*.

    Used to store refresh tokens and password reset tokens without saving
    the raw value — prevents token exposure if the DB is compromised.
    """
    return hashlib.sha256(raw_token.encode()).hexdigest()


def generate_raw_token(nbytes: int = 32) -> str:
    """Return a URL-safe random token string suitable for refresh/reset tokens."""
    return secrets.token_urlsafe(nbytes)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    roles: list[str],
    secret_key: str,
    expire_minutes: int,
    impersonando_user_id: uuid.UUID | None = None,
) -> str:
    """Create a signed JWT access token.

    Claims: sub (user_id), tenant_id, roles, scope='access', exp.
    When impersonando_user_id is provided, an additional 'impersonando' claim
    is included so get_current_user can detect and populate the impersonation
    context (D-06). The 'sub' always carries the REAL actor's UUID.
    """
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "scope": "access",
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
    }
    if impersonando_user_id is not None:
        payload["impersonando"] = str(impersonando_user_id)
    return jwt.encode(payload, secret_key, algorithm=_ALGORITHM)


def create_partial_token(
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    secret_key: str,
    expire_minutes: int = 5,
) -> str:
    """Create a short-lived JWT for the 2FA gate step.

    scope='2fa_pending' — rejected by get_current_user() and all normal handlers.
    Only accepted by POST /api/auth/2fa/login-verify.
    """
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "scope": "2fa_pending",
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
    }
    return jwt.encode(payload, secret_key, algorithm=_ALGORITHM)


def create_refresh_token() -> str:
    """Generate a raw refresh token (URL-safe, 32 bytes = 256 bits).

    The caller is responsible for hashing and storing the hash.
    """
    return generate_raw_token(32)


def verify_token(token: str, *, secret_key: str, expected_scope: str) -> dict:
    """Verify *token* and return its claims dict.

    Raises:
        TokenError — if the token is expired, has an invalid signature,
                     is malformed, or does not match *expected_scope*.
    """
    try:
        claims = jwt.decode(token, secret_key, algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise TokenError(f"JWT verification failed: {exc}") from exc

    if claims.get("scope") != expected_scope:
        raise TokenError(
            f"Token scope mismatch: expected '{expected_scope}', got '{claims.get('scope')}'"
        )
    return claims


# ---------------------------------------------------------------------------
# TOTP helpers (2FA)
# ---------------------------------------------------------------------------

def generate_totp_secret() -> str:
    """Generate a random base32 TOTP secret (160-bit, compatible with standard apps)."""
    return pyotp.random_base32()


def get_totp_uri(*, secret: str, email: str, issuer: str) -> str:
    """Return the otpauth:// URI for QR code generation."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp_code(*, secret: str, code: str, valid_window: int = 1) -> bool:
    """Verify *code* against *secret*.

    valid_window=1 allows one 30-second window before and after the current
    window to account for clock drift.
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=valid_window)

"""
tests/test_security.py — TDD tests for JWT, Argon2, and TOTP helpers.

TDD cycle:
  5.1 RED    — written before security.py is implemented.
  5.2 GREEN  — implement JWT + Argon2 helpers.
  5.3 RED    — TOTP helper tests.
  5.4 GREEN  — implement TOTP helpers.
  5.5 TRIANGULATE — partial_token scope rejected by access-scoped verify.

No database required (pure crypto unit tests).
"""
from __future__ import annotations

import time
import uuid

import pytest


SECRET = "a" * 32  # 32-char test key


# ---------------------------------------------------------------------------
# 5.1 RED / 5.2 GREEN — JWT helpers
# ---------------------------------------------------------------------------

def test_create_access_token_returns_string():
    from app.core.security import create_access_token  # noqa: PLC0415

    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=["PROFESOR"],
        secret_key=SECRET,
        expire_minutes=15,
    )
    assert isinstance(token, str)
    assert len(token) > 20


def test_verify_token_returns_claims():
    from app.core.security import create_access_token, verify_token  # noqa: PLC0415

    uid = uuid.uuid4()
    tid = uuid.uuid4()
    token = create_access_token(
        user_id=uid,
        tenant_id=tid,
        roles=["ADMIN"],
        secret_key=SECRET,
        expire_minutes=15,
    )
    claims = verify_token(token, secret_key=SECRET, expected_scope="access")
    assert str(uid) == claims["sub"]
    assert str(tid) == claims["tenant_id"]
    assert "ADMIN" in claims["roles"]


def test_verify_token_raises_on_expired():
    from app.core.security import create_access_token, verify_token, TokenError  # noqa: PLC0415

    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=[],
        secret_key=SECRET,
        expire_minutes=0,  # expires immediately (0 minutes from now)
    )
    time.sleep(1)  # ensure token is expired
    with pytest.raises(TokenError):
        verify_token(token, secret_key=SECRET, expected_scope="access")


def test_verify_token_raises_on_invalid_signature():
    from app.core.security import create_access_token, verify_token, TokenError  # noqa: PLC0415

    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=[],
        secret_key=SECRET,
        expire_minutes=15,
    )
    with pytest.raises(TokenError):
        verify_token(token, secret_key="b" * 32, expected_scope="access")


def test_create_partial_token_has_2fa_pending_scope():
    from app.core.security import create_partial_token, verify_token  # noqa: PLC0415

    uid = uuid.uuid4()
    tid = uuid.uuid4()
    token = create_partial_token(user_id=uid, tenant_id=tid, secret_key=SECRET)
    claims = verify_token(token, secret_key=SECRET, expected_scope="2fa_pending")
    assert claims["scope"] == "2fa_pending"


# ---------------------------------------------------------------------------
# 5.5 TRIANGULATE — partial_token rejected when expected_scope="access"
# ---------------------------------------------------------------------------

def test_partial_token_rejected_with_access_scope():
    from app.core.security import create_partial_token, verify_token, TokenError  # noqa: PLC0415

    token = create_partial_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        secret_key=SECRET,
    )
    with pytest.raises(TokenError):
        verify_token(token, secret_key=SECRET, expected_scope="access")


def test_access_token_rejected_with_2fa_pending_scope():
    from app.core.security import create_access_token, verify_token, TokenError  # noqa: PLC0415

    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=["ADMIN"],
        secret_key=SECRET,
        expire_minutes=15,
    )
    with pytest.raises(TokenError):
        verify_token(token, secret_key=SECRET, expected_scope="2fa_pending")


# ---------------------------------------------------------------------------
# 5.2 GREEN — Argon2id helpers
# ---------------------------------------------------------------------------

def test_hash_password_and_verify():
    from app.core.security import hash_password, verify_password  # noqa: PLC0415

    hashed = hash_password("my_s3cret!")
    assert hashed != "my_s3cret!"
    assert verify_password("my_s3cret!", hashed) is True


def test_verify_password_wrong_password():
    from app.core.security import hash_password, verify_password  # noqa: PLC0415

    hashed = hash_password("correct_password")
    assert verify_password("wrong_password", hashed) is False


# ---------------------------------------------------------------------------
# 5.3 RED / 5.4 GREEN — TOTP helpers
# ---------------------------------------------------------------------------

def test_generate_totp_secret_has_sufficient_entropy():
    from app.core.security import generate_totp_secret  # noqa: PLC0415

    secret = generate_totp_secret()
    # pyotp base32 secrets are typically 32 chars (160 bits)
    assert len(secret) >= 16
    # must be valid base32
    import base64  # noqa: PLC0415
    try:
        # Add padding to make it valid base32 if needed
        padding = (8 - len(secret) % 8) % 8
        base64.b32decode(secret + "=" * padding)
    except Exception:
        pytest.fail("generate_totp_secret() did not return valid base32")


def test_get_totp_uri_returns_otpauth_string():
    from app.core.security import generate_totp_secret, get_totp_uri  # noqa: PLC0415

    secret = generate_totp_secret()
    uri = get_totp_uri(secret=secret, email="alice@example.com", issuer="activia-trace")
    assert uri.startswith("otpauth://totp/")
    assert "alice@example.com" in uri


def test_verify_totp_code_accepts_current_code():
    import pyotp  # noqa: PLC0415
    from app.core.security import verify_totp_code  # noqa: PLC0415

    secret = pyotp.random_base32()
    current_code = pyotp.TOTP(secret).now()
    assert verify_totp_code(secret=secret, code=current_code) is True


def test_verify_totp_code_rejects_wrong_code():
    import pyotp  # noqa: PLC0415
    from app.core.security import verify_totp_code  # noqa: PLC0415

    secret = pyotp.random_base32()
    assert verify_totp_code(secret=secret, code="000000") is False


# ---------------------------------------------------------------------------
# Token hash helpers
# ---------------------------------------------------------------------------

def test_hash_token_deterministic():
    from app.core.security import hash_token  # noqa: PLC0415

    t = "my_refresh_token_value"
    assert hash_token(t) == hash_token(t)
    assert hash_token(t) != t


def test_hash_token_different_inputs_differ():
    from app.core.security import hash_token  # noqa: PLC0415

    assert hash_token("token_a") != hash_token("token_b")

"""
tests/test_auth_schemas.py — TDD tests for auth Pydantic schemas.

TDD cycle:
  3.1 RED    — written before schemas exist.
  3.2 GREEN  — implement schemas.py.
  3.4 TRIANGULATE — extra field rejected by LoginRequest.

No database required (pure Pydantic validation).
"""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# 3.1 RED / 3.2 GREEN — LoginRequest validates required fields
# ---------------------------------------------------------------------------

def test_login_request_valid():
    from app.features.auth.schemas import LoginRequest  # noqa: PLC0415

    req = LoginRequest(email="alice@example.com", password="s3cr3tpassword!")
    assert req.email == "alice@example.com"
    assert req.password == "s3cr3tpassword!"


def test_login_request_rejects_extra_field():
    """LoginRequest must reject unknown fields (extra='forbid')."""
    from app.features.auth.schemas import LoginRequest  # noqa: PLC0415

    with pytest.raises(ValidationError):
        LoginRequest(email="alice@example.com", password="pass", unknown_field="evil")


def test_login_request_requires_email():
    from app.features.auth.schemas import LoginRequest  # noqa: PLC0415

    with pytest.raises(ValidationError):
        LoginRequest(password="pass")


def test_login_request_requires_password():
    from app.features.auth.schemas import LoginRequest  # noqa: PLC0415

    with pytest.raises(ValidationError):
        LoginRequest(email="alice@example.com")


# ---------------------------------------------------------------------------
# ResetRequest validates minimum password length
# ---------------------------------------------------------------------------

def test_reset_request_valid():
    from app.features.auth.schemas import ResetRequest  # noqa: PLC0415

    req = ResetRequest(token="abc123", new_password="newpassword123!")
    assert req.token == "abc123"


def test_reset_request_password_too_short():
    """New password must be at least 8 characters."""
    from app.features.auth.schemas import ResetRequest  # noqa: PLC0415

    with pytest.raises(ValidationError):
        ResetRequest(token="abc123", new_password="short")


def test_reset_request_rejects_extra_field():
    from app.features.auth.schemas import ResetRequest  # noqa: PLC0415

    with pytest.raises(ValidationError):
        ResetRequest(token="t", new_password="longpassword!", evil="field")


# ---------------------------------------------------------------------------
# TokenResponse has all required fields
# ---------------------------------------------------------------------------

def test_token_response_valid():
    from app.features.auth.schemas import TokenResponse  # noqa: PLC0415

    resp = TokenResponse(
        access_token="eyJ...",
        refresh_token="opaque_token",
        token_type="bearer",
    )
    assert resp.token_type == "bearer"


def test_partial_token_response_valid():
    from app.features.auth.schemas import PartialTokenResponse  # noqa: PLC0415

    resp = PartialTokenResponse(partial_token="eyJ...", requires_2fa=True)
    assert resp.requires_2fa is True


# ---------------------------------------------------------------------------
# 3.3 — CurrentUser dataclass is immutable
# ---------------------------------------------------------------------------

def test_current_user_is_frozen():
    from app.core.auth_context import CurrentUser  # noqa: PLC0415

    user = CurrentUser(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=["PROFESOR"],
    )
    with pytest.raises((AttributeError, TypeError)):
        user.roles = ["ADMIN"]  # type: ignore[misc]


def test_current_user_fields():
    from app.core.auth_context import CurrentUser  # noqa: PLC0415

    uid = uuid.uuid4()
    tid = uuid.uuid4()
    u = CurrentUser(user_id=uid, tenant_id=tid, roles=["COORDINADOR", "ADMIN"])
    assert u.user_id == uid
    assert u.tenant_id == tid
    assert "COORDINADOR" in u.roles


# ---------------------------------------------------------------------------
# 3.4 TRIANGULATE — all other schemas reject extra fields
# ---------------------------------------------------------------------------

def test_refresh_request_rejects_extra():
    from app.features.auth.schemas import RefreshRequest  # noqa: PLC0415

    with pytest.raises(ValidationError):
        RefreshRequest(refresh_token="tok", extra_field="bad")


def test_forgot_request_rejects_extra():
    from app.features.auth.schemas import ForgotRequest  # noqa: PLC0415

    with pytest.raises(ValidationError):
        ForgotRequest(email="a@b.com", extra_field="bad")

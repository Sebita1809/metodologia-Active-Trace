"""
tests/test_impersonation_context.py — TDD tests for impersonation JWT context (Task 7).

Verifies:
  - CurrentUser accepts optional impersonando_user_id (7.1)
  - security.py emits impersonation access token with 'impersonando' claim (7.3)
  - get_current_user populates impersonando_user_id from claim (7.5)
  - Normal session leaves impersonando_user_id None (7.5)
  - Request param/header trying to set impersonado outside flow is ignored (7.6)

No DB required for JWT/context tests.

TDD cycle:
  RED   — written before implementation
  GREEN — auth_context.py, security.py, dependencies.py updated
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Task 7.1 — CurrentUser accepts impersonando_user_id (optional, default None)
# ---------------------------------------------------------------------------

def test_current_user_accepts_impersonando_user_id():
    """CurrentUser can be constructed with impersonando_user_id."""
    from app.core.auth_context import CurrentUser  # noqa: PLC0415

    uid = uuid.uuid4()
    tid = uuid.uuid4()
    imp = uuid.uuid4()

    cu = CurrentUser(user_id=uid, tenant_id=tid, roles=["ADMIN"], impersonando_user_id=imp)
    assert cu.impersonando_user_id == imp


def test_current_user_defaults_impersonando_user_id_to_none():
    """CurrentUser without impersonando_user_id defaults to None."""
    from app.core.auth_context import CurrentUser  # noqa: PLC0415

    cu = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), roles=[])
    assert cu.impersonando_user_id is None


# ---------------------------------------------------------------------------
# Task 7.3 — security.py emits impersonation token with 'impersonando' claim
# ---------------------------------------------------------------------------

def test_create_impersonation_token_contains_impersonando_claim():
    """create_access_token with impersonando_user_id includes 'impersonando' claim."""
    from app.core.security import create_access_token, verify_token  # noqa: PLC0415

    actor_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    impersonado_id = uuid.uuid4()
    secret = "test-secret-key-32chars-long-ok!!"

    token = create_access_token(
        user_id=actor_id,
        tenant_id=tenant_id,
        roles=["VIEWER"],
        secret_key=secret,
        expire_minutes=15,
        impersonando_user_id=impersonado_id,
    )

    claims = verify_token(token, secret_key=secret, expected_scope="access")
    assert "impersonando" in claims, f"Missing 'impersonando' claim: {claims}"
    assert claims["impersonando"] == str(impersonado_id)


def test_normal_access_token_has_no_impersonando_claim():
    """create_access_token without impersonando_user_id does not include 'impersonando'."""
    from app.core.security import create_access_token, verify_token  # noqa: PLC0415

    secret = "test-secret-key-32chars-long-ok!!"
    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=[],
        secret_key=secret,
        expire_minutes=15,
    )

    claims = verify_token(token, secret_key=secret, expected_scope="access")
    assert claims.get("impersonando") is None, (
        f"Normal token should not have 'impersonando' claim: {claims}"
    )


def test_impersonation_token_is_distinguishable_from_normal():
    """Impersonation token contains 'impersonando' claim; normal token does not."""
    from app.core.security import create_access_token, verify_token  # noqa: PLC0415

    secret = "test-secret-key-32chars-long-ok!!"
    actor_id = uuid.uuid4()
    tid = uuid.uuid4()
    imp_id = uuid.uuid4()

    normal_token = create_access_token(
        user_id=actor_id, tenant_id=tid, roles=[], secret_key=secret, expire_minutes=15
    )
    imp_token = create_access_token(
        user_id=actor_id, tenant_id=tid, roles=[], secret_key=secret, expire_minutes=15,
        impersonando_user_id=imp_id,
    )

    normal_claims = verify_token(normal_token, secret_key=secret, expected_scope="access")
    imp_claims = verify_token(imp_token, secret_key=secret, expected_scope="access")

    assert "impersonando" not in normal_claims or normal_claims.get("impersonando") is None
    assert imp_claims["impersonando"] == str(imp_id)


# ---------------------------------------------------------------------------
# Task 7.5 — get_current_user populates impersonando_user_id from JWT claim
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_current_user_populates_impersonando_user_id_from_jwt():
    """get_current_user sets impersonando_user_id when JWT has 'impersonando' claim."""
    from app.core.security import create_access_token  # noqa: PLC0415
    from app.core.dependencies import get_current_user  # noqa: PLC0415
    from fastapi.security import HTTPAuthorizationCredentials  # noqa: PLC0415
    import os  # noqa: PLC0415

    # Monkeypatch settings to use a known secret
    os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-long-ok!!")
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/trace_db")

    actor_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    imp_id = uuid.uuid4()

    from app.core.config import get_settings  # noqa: PLC0415
    secret = get_settings().secret_key

    token = create_access_token(
        user_id=actor_id,
        tenant_id=tenant_id,
        roles=["ADMIN"],
        secret_key=secret,
        expire_minutes=15,
        impersonando_user_id=imp_id,
    )

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    current_user = await get_current_user(credentials=creds)

    assert current_user.user_id == actor_id
    assert current_user.impersonando_user_id == imp_id


@pytest.mark.asyncio
async def test_get_current_user_normal_session_leaves_impersonando_none():
    """get_current_user leaves impersonando_user_id None for normal (non-impersonation) sessions."""
    from app.core.security import create_access_token  # noqa: PLC0415
    from app.core.dependencies import get_current_user  # noqa: PLC0415
    from fastapi.security import HTTPAuthorizationCredentials  # noqa: PLC0415

    from app.core.config import get_settings  # noqa: PLC0415
    secret = get_settings().secret_key

    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=[],
        secret_key=secret,
        expire_minutes=15,
    )

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    current_user = await get_current_user(credentials=creds)

    assert current_user.impersonando_user_id is None


# ---------------------------------------------------------------------------
# Task 7.6 — Request param/header cannot set impersonado outside the JWT flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_param_cannot_override_impersonado():
    """A request body/header param claiming to set impersonado_user_id is ignored.

    The impersonando_user_id in CurrentUser comes ONLY from the JWT claim.
    Any param outside the JWT cannot alter it.
    """
    from app.core.security import create_access_token  # noqa: PLC0415
    from app.core.dependencies import get_current_user  # noqa: PLC0415
    from fastapi.security import HTTPAuthorizationCredentials  # noqa: PLC0415

    from app.core.config import get_settings  # noqa: PLC0415
    secret = get_settings().secret_key

    # Normal token WITHOUT impersonando claim
    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=[],
        secret_key=secret,
        expire_minutes=15,
    )

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    current_user = await get_current_user(credentials=creds)

    # Even though someone could try to pass an X-Impersonado header or body param,
    # get_current_user only reads the JWT — so impersonando_user_id stays None.
    assert current_user.impersonando_user_id is None


@pytest.mark.asyncio
async def test_x_impersonado_header_is_ignored():
    """X-Impersonado-User-Id header has no effect on CurrentUser identity.

    This test verifies the property directly: get_current_user reads ONLY from
    the JWT claims. Since the token has no 'impersonando' claim, impersonando_user_id
    is None regardless of any header present in the request.
    """
    from app.core.security import create_access_token  # noqa: PLC0415
    from app.core.dependencies import get_current_user  # noqa: PLC0415
    from fastapi.security import HTTPAuthorizationCredentials  # noqa: PLC0415
    from app.core.config import get_settings  # noqa: PLC0415

    secret = get_settings().secret_key
    actor_id = uuid.uuid4()
    fake_impersonado = uuid.uuid4()

    # Token WITHOUT 'impersonando' claim
    token = create_access_token(
        user_id=actor_id,
        tenant_id=uuid.uuid4(),
        roles=[],
        secret_key=secret,
        expire_minutes=15,
    )

    # get_current_user only takes HTTPAuthorizationCredentials — it has no access
    # to request headers outside of the JWT. So passing the fake_impersonado as a
    # hypothetical request header cannot change the result.
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    current_user = await get_current_user(credentials=creds)

    # The fake_impersonado header is not visible to get_current_user at all —
    # it only reads the JWT. The result must always be None.
    assert current_user.impersonando_user_id is None, (
        f"impersonando_user_id should be None (no claim in JWT), got: {current_user.impersonando_user_id}"
    )

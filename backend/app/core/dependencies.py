"""
core/dependencies.py — FastAPI dependency-injection helpers.

Implemented: C-01 (foundation-setup), C-03 (auth-jwt-2fa), C-04 (rbac-permisos-finos)

Re-exports:
  require_permission — RBAC guard factory (see app/core/permissions.py)
  PermisoConcedido   — DTO returned by require_permission on access grant
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.database import get_session_factory
from app.core.security import TokenError, verify_token

_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session scoped to the current request.

    Commits on success, rolls back on exception.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    """Extract and verify the JWT Bearer token; return the verified CurrentUser.

    Identity comes ONLY from the JWT — never from request parameters.
    Raises HTTP 401 on any token issue (missing, expired, wrong scope, bad sig).
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from app.core.config import get_settings  # noqa: PLC0415
    secret_key = get_settings().secret_key

    try:
        claims = verify_token(credentials.credentials, secret_key=secret_key, expected_scope="access")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    # Impersonation claim — only set if the token was issued via the impersonation
    # flow. NEVER read from request params, headers, or body (D-06 / CLAUDE.md rule 8).
    impersonando_raw = claims.get("impersonando")
    impersonando_user_id = uuid.UUID(impersonando_raw) if impersonando_raw else None

    return CurrentUser(
        user_id=uuid.UUID(claims["sub"]),
        tenant_id=uuid.UUID(claims["tenant_id"]),
        roles=claims.get("roles", []),
        impersonando_user_id=impersonando_user_id,
    )


# Re-export RBAC guard from permissions module (C-04)
# Import lazily to avoid circular imports at module load time.
# Usage in routers: from app.core.dependencies import require_permission, PermisoConcedido
def require_permission(clave: str, scope: str = "global"):
    """Dependency factory for RBAC guard. See app/core/permissions.py for full docs.

    Usage::

        @router.get("/sensitive")
        async def handler(perm: PermisoConcedido = Depends(require_permission("modulo:accion"))):
            ...

    Fail-closed: missing permission → HTTP 403.
    scope="global" (default): requires alcance global.
    scope="propio": accepts propio or global.
    """
    from app.core.permissions import require_permission as _rp  # noqa: PLC0415
    return _rp(clave, scope)


# Also expose PermisoConcedido for type annotations in routers
from app.core.permissions import PermisoConcedido  # noqa: E402, F401

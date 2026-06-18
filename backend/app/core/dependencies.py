"""FastAPI dependencies for the activia-trace backend.

Implemented in C-01:
    - get_db: provides an async DB session per request.

Implemented in C-02:
    - get_current_tenant: resolves tenant_id from request context.

Implemented in C-03:
    - get_current_user: extracts authenticated user from JWT Bearer token.
    - UserContext: Pydantic model for the authenticated user identity.

Implemented in C-04:
    - require_permission: RBAC guard factory via Permisos matrix.

Implemented in C-05:
    - RequestMetadata: IP and User-Agent extracted from the HTTP request.
    - get_request_metadata: FastAPI dependency to extract IP and User-Agent.
    - Impersonation support in UserContext and get_current_user.
"""

import uuid
from collections.abc import AsyncGenerator

from fastapi import HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.core.security import verify_token
from app.core.tenancy import get_tenant_context


class UserContext(BaseModel):
    """Authenticated user identity extracted from the JWT.

    During impersonation, the actor_id preserves the identity of the
    real user performing the action, while user_id reflects the
    impersonated user (the user being acted upon).
    """

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    roles: list[str]
    is_impersonating: bool = False
    actor_id: uuid.UUID | None = None
    impersonated_user_id: uuid.UUID | None = None


class RequestMetadata(BaseModel):
    """IP address and User-Agent extracted from the HTTP request."""

    ip: str | None = None
    user_agent: str | None = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async DB session for the duration of a request.

    Session is created per-call and closed in ``finally``,
    guaranteeing the connection returns to the pool even on exceptions.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        await session.close()


async def get_current_tenant(request: Request) -> uuid.UUID:
    """Resolve tenant_id from the current request context."""
    return get_tenant_context(request)


async def get_request_metadata(request: Request) -> RequestMetadata:
    """Extract IP and User-Agent from the incoming request.

    IP is resolved from X-Forwarded-For header (if behind proxy)
    or the client host directly.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else None

    user_agent = request.headers.get("User-Agent")
    return RequestMetadata(ip=ip, user_agent=user_agent)


async def get_current_user(request: Request) -> UserContext:
    """Extract authenticated user from JWT Bearer token.

    Expects an ``Authorization: Bearer <token>`` header.
    Returns a :class:`UserContext` with the identity claims.
    Raises 401 if the token is missing, malformed, or invalid.

    Supports impersonation: if the token type is ``"impersonation"``,
    the returned UserContext will have ``is_impersonating=True`` along
    with the original ``actor_id`` and ``impersonated_user_id`` claims.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.removeprefix("Bearer ")
    payload = verify_token(token)

    ctx = UserContext(
        user_id=uuid.UUID(payload["sub"]),
        tenant_id=uuid.UUID(payload["tenant_id"]),
        email=payload.get("email", ""),
        roles=payload.get("roles", []),
    )

    if payload.get("type") == "impersonation":
        ctx.is_impersonating = True
        ctx.actor_id = (
            uuid.UUID(payload["actor_id"])
            if payload.get("actor_id")
            else None
        )
        ctx.impersonated_user_id = (
            uuid.UUID(payload["impersonated_user_id"])
            if payload.get("impersonated_user_id")
            else None
        )

    return ctx


from app.core.permissions import require_permission

"""FastAPI dependencies for the activia-trace backend.

Implemented in C-01:
    - get_db: provides an async DB session per request.

Implemented in C-02:
    - get_current_tenant: resolves tenant_id from request context.

Implemented in C-03:
    - get_current_user: extracts authenticated user from JWT Bearer token.
    - UserContext: Pydantic model for the authenticated user identity.

Reserved slots (to be filled by C-04):
    - require_permission → C-04 (RBAC guard)
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
    """Authenticated user identity extracted from the JWT."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    roles: list[str]


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


async def get_current_user(request: Request) -> UserContext:
    """Extract authenticated user from JWT Bearer token.

    Expects an ``Authorization: Bearer <token>`` header.
    Returns a :class:`UserContext` with the identity claims.
    Raises 401 if the token is missing, malformed, or invalid.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.removeprefix("Bearer ")
    payload = verify_token(token)

    return UserContext(
        user_id=uuid.UUID(payload["sub"]),
        tenant_id=uuid.UUID(payload["tenant_id"]),
        email=payload.get("email", ""),
        roles=payload.get("roles", []),
    )

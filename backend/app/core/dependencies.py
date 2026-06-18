"""FastAPI dependencies for the activia-trace backend.

Implemented in C-01:
    - get_db: provides an async DB session per request.

Implemented in C-02:
    - get_current_tenant: resolves tenant_id from request context.

Reserved slots (to be filled by C-03 / C-04):
    - get_current_user   → C-03 (JWT identity)
    - require_permission → C-04 (RBAC guard)
"""

import uuid
from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.core.tenancy import get_tenant_context


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

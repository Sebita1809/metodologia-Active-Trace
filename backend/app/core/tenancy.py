"""Tenant context resolution.

Resolves tenant_id from:
1. JWT claims (Bearer token in Authorization header)
2. X-Tenant-ID header (development / anonymous endpoints)
3. Default tenant (local development)
"""

import uuid

from fastapi import HTTPException, Request

from app.core.security import verify_token

_DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_tenant_context(request: Request) -> uuid.UUID:
    """Resolve tenant_id from JWT claims or fallback request context.

    Priority:
    1. Valid Bearer JWT → extract ``tenant_id`` from its claims.
    2. ``X-Tenant-ID`` header (used by anonymous endpoints: login, forgot, reset).
    3. Default tenant UUID for local development.

    In the future a ``Tenant`` model lookup by slug/domain may be added here
    for multi-tenant domain-based routing.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ")
        try:
            payload = verify_token(token)
            tenant_id = payload.get("tenant_id")
            if tenant_id:
                return uuid.UUID(tenant_id)
        except HTTPException:
            pass

    tenant_header = request.headers.get("X-Tenant-ID")
    if tenant_header:
        try:
            return uuid.UUID(tenant_header)
        except ValueError:
            pass
    return _DEFAULT_TENANT_ID

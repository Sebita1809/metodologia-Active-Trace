"""Tenant context resolution.

Placeholder implementation for C-02. Resolves tenant_id from:
1. X-Tenant-ID header (development)
2. Default tenant (local development)

C-03 will replace this with real JWT-based resolution.
"""

import uuid

from fastapi import Request

_DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_tenant_context(request: Request) -> uuid.UUID:
    """Resolve tenant_id from request context.

    In development: reads X-Tenant-ID header.
    Falls back to default tenant for local development.
    """
    tenant_header = request.headers.get("X-Tenant-ID")
    if tenant_header:
        try:
            return uuid.UUID(tenant_header)
        except ValueError:
            pass
    return _DEFAULT_TENANT_ID

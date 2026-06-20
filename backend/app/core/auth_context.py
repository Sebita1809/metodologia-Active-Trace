"""
app/core/auth_context.py — Immutable CurrentUser DTO.

This dataclass is the single value produced by get_current_user(). It carries
the verified identity from the JWT — never from request parameters.

Implemented: C-03 (auth-jwt-2fa)
Updated:     C-05 (audit-log) — added impersonando_user_id claim
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CurrentUser:
    """Verified identity extracted from a validated JWT.

    Attributes:
        user_id              — UUID of the authenticated user (from JWT 'sub' claim)
        tenant_id            — UUID of the user's tenant (from JWT 'tenant_id' claim)
        roles                — list of role strings assigned to the user
        impersonando_user_id — UUID of the impersonated user if this is an
                               impersonation session (from JWT 'impersonando' claim).
                               None for normal sessions.
                               ONLY ever set from the JWT — never from request params.
    """

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    roles: list[str]
    impersonando_user_id: uuid.UUID | None = field(default=None)

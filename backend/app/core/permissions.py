"""
core/permissions.py — RBAC guard: require_permission() dependency factory.

Implements:
  - PermisoConcedido(clave, alcance): DTO passed to handlers when access is granted.
  - require_permission(clave, scope="global"): FastAPI dependency factory that:
      1. Resolves the current user via get_current_user (identity from JWT).
      2. Resolves effective permissions from the DB via RbacService.
      3. If the required clave is not present with sufficient alcance → HTTP 403.
      4. If access is granted → returns PermisoConcedido so the handler knows the alcance.

Design decisions (from design.md):
  D-05: fail-closed; 403 (never 401) for missing permission; dependency factory pattern.
  D-04: scope semantics — scope="propio" accepts propio or global; scope="global" requires global.
  D-02: permissions resolved server-side against DB, never from JWT.

Rules:
  - Identidad SIEMPRE from JWT (via get_current_user) — never from request params.
  - Fail-closed: without explicit permission → 403, never passthrough.
  - 401 is reserved for unauthenticated requests (handled by get_current_user).

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db


@dataclass(frozen=True)
class PermisoConcedido:
    """Immutable DTO returned by require_permission when access is granted.

    The handler can inspect `alcance` to decide whether to filter data by owner
    (when alcance == "propio") or return all tenant data (when alcance == "global").

    Attributes:
        clave   — the permission key that was evaluated, e.g. "atrasados:ver"
        alcance — effective scope granted: "global" | "propio"
    """

    clave: str
    alcance: str


def require_permission(clave: str, scope: str = "global"):
    """Return a FastAPI dependency that enforces RBAC for *clave* at *scope*.

    Parameters
    ----------
    clave:
        The permission key the endpoint requires, e.g. "comunicacion:enviar".
    scope:
        Minimum scope required by the endpoint:
        - "global": only users with alcance "global" pass (propio does NOT satisfy).
        - "propio": both "propio" and "global" pass.

    Returns
    -------
    An async dependency callable that:
        - Returns PermisoConcedido(clave, alcance_efectivo) on success.
        - Raises HTTPException(403) if the user lacks the permission with sufficient alcance.

    Fail-closed: any error in resolution → 403 (not passthrough).
    401 is never raised here — that is the responsibility of get_current_user.
    """

    async def _guard(
        current_user: CurrentUser = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
    ) -> PermisoConcedido:
        from app.services.rbac_service import RbacService  # noqa: PLC0415

        ahora = datetime.now(tz=timezone.utc)
        svc = RbacService(session=session)

        try:
            effective = await svc.resolver_permisos_efectivos(
                current_user.user_id,
                current_user.tenant_id,
                ahora,
            )
        except Exception:
            # Fail-closed: any resolver failure → 403
            raise HTTPException(status_code=403, detail="Permission check failed")

        alcance_efectivo = effective.get(clave)

        if alcance_efectivo is None:
            # Permission not granted at all
            raise HTTPException(
                status_code=403,
                detail=f"Permission required: {clave}",
            )

        if scope == "global" and alcance_efectivo != "global":
            # Endpoint requires global but user only has propio
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{clave}' requires global scope",
            )

        # Access granted — return the conceded permission so the handler can act on alcance
        return PermisoConcedido(clave=clave, alcance=alcance_efectivo)

    return _guard

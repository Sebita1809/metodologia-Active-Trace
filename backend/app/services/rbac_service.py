"""
app/services/rbac_service.py — RBAC effective permissions resolver.

RbacService.resolver_permisos_efectivos() computes the effective permission
set for a (user_id, tenant_id) pair at a given point in time, by joining:
  usuario_rol → rol_permiso → permiso

The result is a dict mapping `modulo:accion` → alcance_efectivo ("global" | "propio").
`global` always wins over `propio` when the same key appears in multiple roles.

Design decisions (from design.md):
  D-02: permissions resolved server-side by request, never from JWT
  D-04: alcance_efectivo — global wins over propio; expose to handlers
  D-03: vigencia filtering: ahora ∈ [vigente_desde, vigente_hasta)

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permiso import Permiso
from app.models.rol_permiso import RolPermiso
from app.models.usuario_rol import UsuarioRol


class RbacService:
    """Service that resolves effective permissions for a user in a tenant.

    Parameters
    ----------
    session:
        An open async SQLAlchemy session for the current request.
    """

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def resolver_permisos_efectivos(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        ahora: datetime,
    ) -> dict[str, str]:
        """Compute the union of effective permissions for *user_id* in *tenant_id* at *ahora*.

        Returns
        -------
        dict[str, str]
            Mapping of `modulo:accion` → alcance_efectivo.
            alcance_efectivo is "global" if ANY vigent role grants global for that key;
            "propio" if all vigent roles grant propio.
            Keys not present → no permission (fail-closed).

        The computation:
          1. Find all usuario_rol rows for (user_id, tenant_id) where
             vigente_desde <= ahora AND (vigente_hasta IS NULL OR vigente_hasta > ahora).
          2. JOIN to rol_permiso (scoped to tenant_id).
          3. JOIN to permisos (scoped to tenant_id).
          4. For each clave, take the MAX alcance (global > propio).
        """
        # Single query via join: usuario_rol → rol_permiso → permiso
        # Scope everything to tenant_id so no cross-tenant data ever leaks.
        stmt = (
            select(Permiso.clave, RolPermiso.alcance)
            .join(RolPermiso, and_(
                RolPermiso.permiso_id == Permiso.id,
                RolPermiso.tenant_id == tenant_id,
                RolPermiso.deleted_at.is_(None),
            ))
            .join(UsuarioRol, and_(
                UsuarioRol.rol_id == RolPermiso.rol_id,
                UsuarioRol.tenant_id == tenant_id,
                UsuarioRol.user_id == user_id,
                UsuarioRol.deleted_at.is_(None),
                # Vigencia: desde <= ahora
                UsuarioRol.vigente_desde <= ahora,
                # hasta is None (open-ended) OR hasta > ahora
                or_(
                    UsuarioRol.vigente_hasta.is_(None),
                    UsuarioRol.vigente_hasta > ahora,
                ),
            ))
            .where(Permiso.tenant_id == tenant_id)
            .where(Permiso.deleted_at.is_(None))
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        # Fold: global wins over propio
        effective: dict[str, str] = {}
        for clave, alcance in rows:
            alcance_str = str(alcance)  # handles both enum and plain string
            if clave not in effective:
                effective[clave] = alcance_str
            elif alcance_str == "global":
                # global always wins
                effective[clave] = "global"
            # if current is already "global" and new is "propio" → keep "global"

        return effective

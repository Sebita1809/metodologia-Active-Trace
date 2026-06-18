"""RBAC permission resolution and authorization guards.

Implemented in C-04:
    - resolve_user_permissions: resolves effective permissions for a user.
    - require_permission: FastAPI dependency guard for endpoint authorization.
"""

import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permiso import Permiso
from app.models.rol import Rol
from app.models.rol_permiso import RolPermiso


async def resolve_user_permissions(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    roles: list[str],
    db: AsyncSession,
) -> set[str]:
    """Resolve effective permission codes for a user based on their roles.

    Queries Rol -> RolPermiso -> Permiso to find all permission codes
    for the user's roles within their tenant scope (including global roles).
    """
    if not roles:
        return set()

    # Find Rol records matching the role names, scoped to tenant or global
    stmt = select(Rol.id).where(
        Rol.nombre.in_(roles),
        ((Rol.tenant_id == tenant_id) | (Rol.tenant_id.is_(None))),
    )
    result = await db.execute(stmt)
    role_ids = [row[0] for row in result.all()]

    if not role_ids:
        return set()

    # Find all permission codigos for those roles
    stmt = (
        select(Permiso.codigo)
        .select_from(RolPermiso)
        .join(Permiso, RolPermiso.permiso_id == Permiso.id)
        .where(RolPermiso.rol_id.in_(role_ids))
    )
    result = await db.execute(stmt)
    return {row[0] for row in result.all()}


def require_permission(permiso_codigo: str):
    """FastAPI dependency that verifies the user has a specific permission.

    Usage:
        @router.get("/endpoint")
        async def my_endpoint(
            current_user: UserContext = Depends(get_current_user),
            _: None = Depends(require_permission("calificaciones:importar")),
            db: AsyncSession = Depends(get_db),
        ):
            ...

    Returns 403 if the user lacks the required permission.
    The 401 from get_current_user takes precedence (runs first).
    """
    # Lazy import to avoid circular dependency (dependencies → permissions → dependencies)
    from app.core.dependencies import UserContext, get_current_user, get_db

    async def _dependency(
        current_user: UserContext = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        permissions = await resolve_user_permissions(
            user_id=current_user.user_id,
            tenant_id=current_user.tenant_id,
            roles=current_user.roles,
            db=db,
        )
        if permiso_codigo not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permiso_codigo}",
            )

    return _dependency

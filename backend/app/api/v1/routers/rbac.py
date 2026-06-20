"""
api/v1/routers/rbac.py — RBAC catalog administration endpoints.

Routes:
  GET    /api/rbac/roles                     — list roles
  POST   /api/rbac/roles                     — create role
  GET    /api/rbac/roles/{rol_id}            — get role
  PATCH  /api/rbac/roles/{rol_id}            — update role
  DELETE /api/rbac/roles/{rol_id}            — soft-delete role

  GET    /api/rbac/permisos                  — list permissions
  POST   /api/rbac/permisos                  — create permission
  GET    /api/rbac/permisos/{permiso_id}     — get permission
  PATCH  /api/rbac/permisos/{permiso_id}     — update permission
  DELETE /api/rbac/permisos/{permiso_id}     — soft-delete permission

  GET    /api/rbac/roles/{rol_id}/permisos   — list matrix rows for role
  POST   /api/rbac/roles/{rol_id}/permisos   — assign permission to role
  DELETE /api/rbac/roles/{rol_id}/permisos/{permiso_id} — remove from matrix

  GET    /api/rbac/users/{user_id}/roles     — list user's role assignments
  POST   /api/rbac/users/{user_id}/roles     — assign role to user
  DELETE /api/rbac/users/{user_id}/roles/{assignment_id} — revoke assignment

All endpoints require `rbac:administrar` permission (ADMIN only).
No business logic in this router — all delegated to RbacAdminService.

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.core.permissions import PermisoConcedido, require_permission
from app.schemas.rbac import (
    AssignPermisoToRolRequest,
    AssignRolToUserRequest,
    CreatePermisoRequest,
    CreateRolRequest,
    PermisoResponse,
    RolPermisoResponse,
    RolResponse,
    UpdatePermisoRequest,
    UpdateRolRequest,
    UsuarioRolResponse,
)
from app.services.rbac_admin_service import RbacAdminService

router = APIRouter(tags=["rbac"])

# Guard: all endpoints in this router require rbac:administrar
_require_admin = require_permission("rbac:administrar", scope="global")


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RbacAdminService:
    """Build RbacAdminService scoped to the authenticated user's tenant."""
    return RbacAdminService(session=session, tenant_id=current_user.tenant_id)


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

@router.get("/roles", response_model=list[RolResponse])
async def list_roles(
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> list[RolResponse]:
    roles = await svc.list_roles()
    return [RolResponse.model_validate(r) for r in roles]


@router.post("/roles", response_model=RolResponse, status_code=status.HTTP_201_CREATED)
async def create_rol(
    body: CreateRolRequest,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> RolResponse:
    try:
        rol = await svc.create_rol(nombre=body.nombre, descripcion=body.descripcion)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return RolResponse.model_validate(rol)


@router.get("/roles/{rol_id}", response_model=RolResponse)
async def get_rol(
    rol_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> RolResponse:
    rol = await svc.get_rol(rol_id)
    if rol is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return RolResponse.model_validate(rol)


@router.patch("/roles/{rol_id}", response_model=RolResponse)
async def update_rol(
    rol_id: uuid.UUID,
    body: UpdateRolRequest,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> RolResponse:
    rol = await svc.update_rol(
        rol_id,
        nombre=body.nombre,
        descripcion=body.descripcion,
    )
    if rol is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return RolResponse.model_validate(rol)


@router.delete("/roles/{rol_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_rol(
    rol_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> None:
    deleted = await svc.delete_rol(rol_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Role not found")


# ---------------------------------------------------------------------------
# Permisos
# ---------------------------------------------------------------------------

@router.get("/permisos", response_model=list[PermisoResponse])
async def list_permisos(
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> list[PermisoResponse]:
    permisos = await svc.list_permisos()
    return [PermisoResponse.model_validate(p) for p in permisos]


@router.post("/permisos", response_model=PermisoResponse, status_code=status.HTTP_201_CREATED)
async def create_permiso(
    body: CreatePermisoRequest,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> PermisoResponse:
    try:
        permiso = await svc.create_permiso(
            clave=body.clave,
            modulo=body.modulo,
            accion=body.accion,
            descripcion=body.descripcion,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return PermisoResponse.model_validate(permiso)


@router.get("/permisos/{permiso_id}", response_model=PermisoResponse)
async def get_permiso(
    permiso_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> PermisoResponse:
    permiso = await svc.get_permiso(permiso_id)
    if permiso is None:
        raise HTTPException(status_code=404, detail="Permission not found")
    return PermisoResponse.model_validate(permiso)


@router.patch("/permisos/{permiso_id}", response_model=PermisoResponse)
async def update_permiso(
    permiso_id: uuid.UUID,
    body: UpdatePermisoRequest,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> PermisoResponse:
    permiso = await svc.update_permiso(permiso_id, descripcion=body.descripcion)
    if permiso is None:
        raise HTTPException(status_code=404, detail="Permission not found")
    return PermisoResponse.model_validate(permiso)


@router.delete("/permisos/{permiso_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_permiso(
    permiso_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> None:
    deleted = await svc.delete_permiso(permiso_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Permission not found")


# ---------------------------------------------------------------------------
# Matrix: RolPermiso
# ---------------------------------------------------------------------------

@router.get("/roles/{rol_id}/permisos", response_model=list[RolPermisoResponse])
async def list_rol_permisos(
    rol_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> list[RolPermisoResponse]:
    rows = await svc.list_rol_permisos(rol_id)
    return [RolPermisoResponse.model_validate(r) for r in rows]


@router.post(
    "/roles/{rol_id}/permisos",
    response_model=RolPermisoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_permiso_to_rol(
    rol_id: uuid.UUID,
    body: AssignPermisoToRolRequest,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> RolPermisoResponse:
    try:
        rp = await svc.assign_permiso_to_rol(
            rol_id=rol_id,
            permiso_id=body.permiso_id,
            alcance=body.alcance,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return RolPermisoResponse.model_validate(rp)


@router.delete(
    "/roles/{rol_id}/permisos/{permiso_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_permiso_from_rol(
    rol_id: uuid.UUID,
    permiso_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> None:
    removed = await svc.remove_permiso_from_rol(rol_id=rol_id, permiso_id=permiso_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Assignment not found")


# ---------------------------------------------------------------------------
# UsuarioRol
# ---------------------------------------------------------------------------

@router.get("/users/{user_id}/roles", response_model=list[UsuarioRolResponse])
async def list_user_roles(
    user_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> list[UsuarioRolResponse]:
    assignments = await svc.list_user_roles(user_id)
    return [UsuarioRolResponse.model_validate(a) for a in assignments]


@router.post(
    "/users/{user_id}/roles",
    response_model=UsuarioRolResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_rol_to_user(
    user_id: uuid.UUID,
    body: AssignRolToUserRequest,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> UsuarioRolResponse:
    ur = await svc.assign_rol_to_user(
        user_id=user_id,
        rol_id=body.rol_id,
        vigente_desde=body.vigente_desde,
        vigente_hasta=body.vigente_hasta,
    )
    return UsuarioRolResponse.model_validate(ur)


@router.delete(
    "/users/{user_id}/roles/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def revoke_user_rol(
    user_id: uuid.UUID,
    assignment_id: uuid.UUID,
    _perm: PermisoConcedido = Depends(_require_admin),
    svc: RbacAdminService = Depends(_get_svc),
) -> None:
    revoked = await svc.revoke_user_rol(assignment_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Role assignment not found")

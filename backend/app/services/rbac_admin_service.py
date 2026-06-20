"""
app/services/rbac_admin_service.py — RBAC catalog administration service.

Encapsulates all business logic for managing roles, permisos and the matrix.
Routers delegate to this service; no DB access happens in routers.

Rules enforced:
  - All entities scoped to tenant_id from the authenticated user (never from request body).
  - Soft delete for audit trail.
  - Uniqueness violations surfaced as ValueError (translated to 409 by the router).

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.rol_permiso import RolPermiso, AlcanceEnum
from app.models.usuario_rol import UsuarioRol
from app.repositories.roles import RolRepository
from app.repositories.permisos import PermisoRepository
from app.repositories.rol_permiso import RolPermisoRepository
from app.repositories.usuario_rol import UsuarioRolRepository


class RbacAdminService:
    """CRUD operations for the RBAC catalog.

    All write methods are scoped to *tenant_id* — the identity comes from
    the JWT-verified CurrentUser, never from request body.
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._roles = RolRepository(session=session, tenant_id=tenant_id)
        self._permisos = PermisoRepository(session=session, tenant_id=tenant_id)
        self._rol_perm = RolPermisoRepository(session=session, tenant_id=tenant_id)
        self._usr_rol = UsuarioRolRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------

    async def list_roles(self) -> list[Rol]:
        return await self._roles.list()

    async def get_rol(self, rol_id: uuid.UUID) -> Rol | None:
        return await self._roles.get(rol_id)

    async def create_rol(self, nombre: str, descripcion: str | None = None) -> Rol:
        existing = await self._roles.get_by_nombre(nombre)
        if existing:
            raise ValueError(f"Role '{nombre}' already exists in this tenant")
        rol = Rol(tenant_id=self._tenant_id, nombre=nombre, descripcion=descripcion)
        return await self._roles.create(rol)

    async def update_rol(
        self,
        rol_id: uuid.UUID,
        nombre: str | None = None,
        descripcion: str | None = None,
    ) -> Rol | None:
        data = {}
        if nombre is not None:
            data["nombre"] = nombre
        if descripcion is not None:
            data["descripcion"] = descripcion
        return await self._roles.update(rol_id, **data)

    async def delete_rol(self, rol_id: uuid.UUID) -> bool:
        return await self._roles.soft_delete(rol_id)

    # ------------------------------------------------------------------
    # Permisos
    # ------------------------------------------------------------------

    async def list_permisos(self) -> list[Permiso]:
        return await self._permisos.list()

    async def get_permiso(self, permiso_id: uuid.UUID) -> Permiso | None:
        return await self._permisos.get(permiso_id)

    async def create_permiso(
        self,
        clave: str,
        modulo: str,
        accion: str,
        descripcion: str | None = None,
    ) -> Permiso:
        existing = await self._permisos.get_by_clave(clave)
        if existing:
            raise ValueError(f"Permission '{clave}' already exists in this tenant")
        perm = Permiso(
            tenant_id=self._tenant_id,
            clave=clave,
            modulo=modulo,
            accion=accion,
            descripcion=descripcion,
        )
        return await self._permisos.create(perm)

    async def update_permiso(
        self,
        permiso_id: uuid.UUID,
        descripcion: str | None = None,
    ) -> Permiso | None:
        data = {}
        if descripcion is not None:
            data["descripcion"] = descripcion
        return await self._permisos.update(permiso_id, **data)

    async def delete_permiso(self, permiso_id: uuid.UUID) -> bool:
        return await self._permisos.soft_delete(permiso_id)

    # ------------------------------------------------------------------
    # Matrix: RolPermiso
    # ------------------------------------------------------------------

    async def list_rol_permisos(self, rol_id: uuid.UUID) -> list[RolPermiso]:
        return await self._rol_perm.list_for_rol(rol_id)

    async def assign_permiso_to_rol(
        self,
        rol_id: uuid.UUID,
        permiso_id: uuid.UUID,
        alcance: str = "global",
    ) -> RolPermiso:
        existing = await self._rol_perm.get_by_rol_and_permiso(rol_id, permiso_id)
        if existing:
            raise ValueError("Permission already assigned to this role")
        rp = RolPermiso(
            tenant_id=self._tenant_id,
            rol_id=rol_id,
            permiso_id=permiso_id,
            alcance=AlcanceEnum.global_ if alcance == "global" else AlcanceEnum.propio,
        )
        return await self._rol_perm.create(rp)

    async def remove_permiso_from_rol(
        self,
        rol_id: uuid.UUID,
        permiso_id: uuid.UUID,
    ) -> bool:
        existing = await self._rol_perm.get_by_rol_and_permiso(rol_id, permiso_id)
        if not existing:
            return False
        return await self._rol_perm.soft_delete(existing.id)

    # ------------------------------------------------------------------
    # UsuarioRol
    # ------------------------------------------------------------------

    async def assign_rol_to_user(
        self,
        user_id: uuid.UUID,
        rol_id: uuid.UUID,
        vigente_desde: datetime,
        vigente_hasta: datetime | None = None,
    ) -> UsuarioRol:
        ur = UsuarioRol(
            tenant_id=self._tenant_id,
            user_id=user_id,
            rol_id=rol_id,
            vigente_desde=vigente_desde,
            vigente_hasta=vigente_hasta,
        )
        return await self._usr_rol.create(ur)

    async def list_user_roles(self, user_id: uuid.UUID) -> list[UsuarioRol]:
        return await self._usr_rol.list_for_user(user_id)

    async def revoke_user_rol(self, assignment_id: uuid.UUID) -> bool:
        return await self._usr_rol.soft_delete(assignment_id)

"""
app/schemas/rbac.py — Pydantic v2 DTOs for the RBAC catalog API.

All schemas use `extra='forbid'` (project rule — no undeclared fields accepted).
Request DTOs are prefixed with the verb; Response DTOs with the entity name.

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------

class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# Rol schemas
# ---------------------------------------------------------------------------

class CreateRolRequest(_Base):
    """Body for POST /rbac/roles"""
    nombre: str = Field(min_length=1, max_length=100)
    descripcion: str | None = None


class UpdateRolRequest(_Base):
    """Body for PATCH /rbac/roles/{id}"""
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    descripcion: str | None = None


class RolResponse(_Base):
    """Response DTO for a single Rol."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    nombre: str
    descripcion: str | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Permiso schemas
# ---------------------------------------------------------------------------

class CreatePermisoRequest(_Base):
    """Body for POST /rbac/permisos"""
    clave: str = Field(min_length=3, max_length=100, pattern=r"^\w+:\w+$")
    modulo: str = Field(min_length=1, max_length=50)
    accion: str = Field(min_length=1, max_length=50)
    descripcion: str | None = None


class UpdatePermisoRequest(_Base):
    """Body for PATCH /rbac/permisos/{id}"""
    descripcion: str | None = None


class PermisoResponse(_Base):
    """Response DTO for a single Permiso."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    clave: str
    modulo: str
    accion: str
    descripcion: str | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# RolPermiso (matrix) schemas
# ---------------------------------------------------------------------------

class AssignPermisoToRolRequest(_Base):
    """Body for POST /rbac/roles/{rol_id}/permisos"""
    permiso_id: uuid.UUID
    alcance: Literal["global", "propio"] = "global"


class RolPermisoResponse(_Base):
    """Response DTO for a single RolPermiso matrix row."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    rol_id: uuid.UUID
    permiso_id: uuid.UUID
    alcance: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# UsuarioRol schemas
# ---------------------------------------------------------------------------

class AssignRolToUserRequest(_Base):
    """Body for POST /rbac/users/{user_id}/roles"""
    rol_id: uuid.UUID
    vigente_desde: datetime
    vigente_hasta: datetime | None = None


class UsuarioRolResponse(_Base):
    """Response DTO for a single UsuarioRol assignment."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    rol_id: uuid.UUID
    vigente_desde: datetime
    vigente_hasta: datetime | None
    created_at: datetime
    updated_at: datetime

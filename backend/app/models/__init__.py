"""Model exports for Alembic autogenerate and app-wide imports."""

from app.models.base import BaseModel
from app.models.tenant import Tenant, TenantEstado
from app.models.auth_user import AuthUser
from app.models.refresh_token import RefreshToken
from app.models.password_recovery_token import PasswordRecoveryToken
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.audit_log import AuditLog
from app.models.rol_permiso import RolPermiso
from app.models.domain import (
    Asignacion,
    Carrera,
    Cohorte,
    EntradaPadron,
    Materia,
    UmbralMateria,
    Usuario,
    VersionPadron,
)

__all__ = [
    "Asignacion",
    "BaseModel",
    "Tenant",
    "TenantEstado",
    "AuthUser",
    "RefreshToken",
    "PasswordRecoveryToken",
    "Rol",
    "Permiso",
    "RolPermiso",
    "AuditLog",
    "Carrera",
    "Cohorte",
    "EntradaPadron",
    "Materia",
    "UmbralMateria",
    "Usuario",
    "VersionPadron",
]

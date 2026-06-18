"""Model exports for Alembic autogenerate and app-wide imports."""

from app.models.base import BaseModel
from app.models.tenant import Tenant, TenantEstado

__all__ = [
    "BaseModel",
    "Tenant",
    "TenantEstado",
]

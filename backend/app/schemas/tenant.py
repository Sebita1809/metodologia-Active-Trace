"""Pydantic schemas for Tenant CRUD."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.tenant import TenantEstado


class TenantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str
    codigo: str
    config: Optional[dict] = None


class TenantUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: Optional[str] = None
    codigo: Optional[str] = None
    estado: Optional[TenantEstado] = None
    config: Optional[dict] = None


class TenantResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: UUID
    tenant_id: Optional[UUID] = None
    nombre: str
    codigo: str
    estado: TenantEstado
    config: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

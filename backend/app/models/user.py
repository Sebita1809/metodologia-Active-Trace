"""
app/models/user.py — Minimal User domain entity (auth fields only).

C-03 creates the core auth fields. C-07 (usuarios-y-asignaciones) will
add profile fields (nombre, CUIL, datos fiscales, etc.) via migration 004+.

Implemented: C-03 (auth-jwt-2fa)
"""
from __future__ import annotations

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTenantModel


class User(BaseTenantModel):
    """System user — base entity for authentication.

    Inherits: id (UUID PK), tenant_id (FK), created_at, updated_at, deleted_at.

    Auth fields:
        email         — unique within tenant
        password_hash — Argon2id hash; never plaintext
        is_active     — false = account suspended
    """

    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!s:.8} email={self.email!r} tenant={self.tenant_id!s:.8}>"

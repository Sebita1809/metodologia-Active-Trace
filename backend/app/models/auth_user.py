"""AuthUser model — local user accounts with 2FA support."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AuthUser(BaseModel):
    __tablename__ = "auth_user"
    __mapper_args__ = {"polymorphic_identity": "auth_user"}
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_auth_user_tenant_email"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    totp_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

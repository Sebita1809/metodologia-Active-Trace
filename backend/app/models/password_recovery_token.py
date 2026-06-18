"""PasswordRecoveryToken model — one-time use password reset tokens."""

import uuid
import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class PasswordRecoveryToken(BaseModel):
    __tablename__ = "password_recovery_token"
    __mapper_args__ = {"polymorphic_identity": "password_recovery_token"}

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("auth_user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

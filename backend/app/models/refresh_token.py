"""RefreshToken model — rotating refresh token chain for JWT auth."""

import uuid
import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class RefreshToken(BaseModel):
    __tablename__ = "refresh_token"
    __mapper_args__ = {"polymorphic_identity": "refresh_token"}

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("auth_user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("refresh_token.id", ondelete="SET NULL"), nullable=True
    )

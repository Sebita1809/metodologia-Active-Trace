"""Base ORM model with tenant isolation, soft delete, UUID PKs."""

import re
import uuid
import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core.database import Base


class BaseModel(Base):
    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        name = cls.__name__
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    __mapper_args__ = {"polymorphic_identity": None}

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

"""001_tenant: create tenant table.

Revision ID: 001
Revises:
Create Date: 2026-06-18 10:21:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            UUID,
            sa.ForeignKey("tenant.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column(
            "estado",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'Activo'"),
        ),
        sa.Column("config", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("codigo"),
    )
    op.create_index(op.f("ix_tenant_codigo"), "tenant", ["codigo"])
    op.create_index(op.f("ix_tenant_deleted_at"), "tenant", ["deleted_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_tenant_deleted_at"), table_name="tenant")
    op.drop_index(op.f("ix_tenant_codigo"), table_name="tenant")
    op.drop_table("tenant")

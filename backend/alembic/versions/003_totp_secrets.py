"""003 totp secrets

Revision ID: 003
Revises: 002
Create Date: 2026-06-08

Creates:
  - totp_secrets — encrypted TOTP secrets for 2FA enrollment.

The secret is encrypted with AES-256-GCM (via CryptoService) before
being stored — never in plaintext.

Implemented: C-03 (auth-jwt-2fa)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: str | None = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "totp_secrets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encrypted_secret", sa.Text, nullable=False),
        sa.Column("confirmed", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_totp_tenant_user", "totp_secrets", ["tenant_id", "user_id"])


def downgrade() -> None:
    op.drop_index("ix_totp_tenant_user", table_name="totp_secrets")
    op.drop_table("totp_secrets")

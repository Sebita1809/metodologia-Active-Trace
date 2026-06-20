"""005 audit log

Revision ID: 005
Revises: 004
Create Date: 2026-06-08

Creates the audit_log table with:
  - id, tenant_id, fecha_hora, actor_id, impersonado_id, materia_id,
    accion, detalle (JSONB), filas_afectadas, ip, user_agent
  - Indexes: tenant_id; (tenant_id, fecha_hora); (tenant_id, actor_id)
  - A BEFORE UPDATE OR DELETE trigger that raises EXCEPTION,
    enforcing append-only immutability at the DB level (D-02).

NOTE: Future migrations that need to ALTER audit_log must first disable /
recreate the trigger within that migration.

downgrade() order: drop trigger → drop function → drop table.

Implemented: C-05 (audit-log)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: str | None = "004"
branch_labels = None
depends_on = None

_TRIGGER_FUNC = "audit_log_immutable"
_TRIGGER_NAME = "trg_audit_log_immutable"


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # audit_log table
    # -----------------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "fecha_hora",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("impersonado_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("accion", sa.String(length=100), nullable=False),
        sa.Column("detalle", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "filas_afectadas",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes required by spec and design doc
    op.create_index("ix_audit_log_tenant_id", "audit_log", ["tenant_id"])
    op.create_index(
        "ix_audit_log_tenant_fecha",
        "audit_log",
        ["tenant_id", "fecha_hora"],
    )
    op.create_index(
        "ix_audit_log_tenant_actor",
        "audit_log",
        ["tenant_id", "actor_id"],
    )

    # -----------------------------------------------------------------------
    # Immutability trigger (D-02)
    # Creates a PL/pgSQL function and attaches it as a BEFORE UPDATE OR DELETE
    # trigger so the DB itself rejects any mutation attempt.
    # -----------------------------------------------------------------------
    bind = op.get_bind()

    bind.execute(sa.text(
        f"""
        CREATE OR REPLACE FUNCTION {_TRIGGER_FUNC}()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION
                'audit_log is append-only: UPDATE and DELETE are not allowed';
        END;
        $$;
        """
    ))

    bind.execute(sa.text(
        f"""
        CREATE TRIGGER {_TRIGGER_NAME}
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION {_TRIGGER_FUNC}();
        """
    ))


def downgrade() -> None:
    bind = op.get_bind()

    # 1. Drop trigger first (depends on the function)
    bind.execute(sa.text(
        f"DROP TRIGGER IF EXISTS {_TRIGGER_NAME} ON audit_log"
    ))

    # 2. Drop the trigger function
    bind.execute(sa.text(
        f"DROP FUNCTION IF EXISTS {_TRIGGER_FUNC}()"
    ))

    # 3. Drop indexes then the table
    op.drop_index("ix_audit_log_tenant_actor", table_name="audit_log")
    op.drop_index("ix_audit_log_tenant_fecha", table_name="audit_log")
    op.drop_index("ix_audit_log_tenant_id", table_name="audit_log")
    op.drop_table("audit_log")

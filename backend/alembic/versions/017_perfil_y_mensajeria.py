"""017 perfil y mensajeria interna

Revision ID: 017
Revises: 016
Create Date: 2026-06-18

Adds columns sexo/modalidad_cobro to usuarios and creates the mensajes table.

Changes:
  ALTER TABLE usuarios
    ADD COLUMN sexo            VARCHAR(50) NULL
    ADD COLUMN modalidad_cobro VARCHAR(20) NULL
      CHECK modalidad_cobro IN ('Factura', 'Liquidacion')

  CREATE TABLE mensajes (BaseTenantModel + messaging columns):
    thread_id       — UUID NOT NULL
    remitente_id    — UUID FK usuarios RESTRICT NOT NULL
    destinatario_id — UUID FK usuarios RESTRICT NOT NULL
    asunto          — TEXT NULL
    cuerpo          — TEXT NOT NULL
    leido_at        — TIMESTAMPTZ NULL

  Indexes:
    ix_mensajes_tenant_thread      (tenant_id, thread_id)
    ix_mensajes_tenant_destinatario (tenant_id, destinatario_id)

Downgrade: DROP TABLE mensajes; DROP COLUMNS sexo, modalidad_cobro from usuarios.

Implemented: C-20 (perfil-y-mensajeria-interna)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "017"
down_revision: str | None = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # usuarios: add sexo and modalidad_cobro columns
    # -----------------------------------------------------------------------
    op.add_column("usuarios", sa.Column("sexo", sa.String(50), nullable=True))
    op.add_column(
        "usuarios",
        sa.Column(
            "modalidad_cobro",
            sa.String(20),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_usuarios_modalidad_cobro",
        "usuarios",
        "modalidad_cobro IN ('Factura', 'Liquidacion')",
    )

    # -----------------------------------------------------------------------
    # mensajes table
    # -----------------------------------------------------------------------
    op.create_table(
        "mensajes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("remitente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destinatario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asunto", sa.Text, nullable=True),
        sa.Column("cuerpo", sa.Text, nullable=False),
        sa.Column("leido_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["remitente_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["destinatario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_mensajes_tenant_id", "mensajes", ["tenant_id"])
    op.create_index("ix_mensajes_tenant_thread", "mensajes", ["tenant_id", "thread_id"])
    op.create_index(
        "ix_mensajes_tenant_destinatario",
        "mensajes",
        ["tenant_id", "destinatario_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_mensajes_tenant_destinatario", table_name="mensajes")
    op.drop_index("ix_mensajes_tenant_thread", table_name="mensajes")
    op.drop_index("ix_mensajes_tenant_id", table_name="mensajes")
    op.drop_table("mensajes")

    op.drop_constraint("ck_usuarios_modalidad_cobro", "usuarios", type_="check")
    op.drop_column("usuarios", "modalidad_cobro")
    op.drop_column("usuarios", "sexo")

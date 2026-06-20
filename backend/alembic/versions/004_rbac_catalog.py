"""004 rbac catalog

Revision ID: 004
Revises: 003
Create Date: 2026-06-08

Creates the complete RBAC catalog in a single cohesive migration:
  - roles          — tenant-scoped role catalog
  - permisos       — tenant-scoped permission catalog (modulo:accion)
  - rol_permiso    — N:N matrix: role → permission with alcance (global|propio)
  - usuario_rol    — temporal assignment of a role to a user within a tenant

Also runs the idempotent seed for all existing tenants (via rbac_seed helper).

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: str | None = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # roles
    # -----------------------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "nombre", name="uq_roles_tenant_nombre"),
    )
    op.create_index("ix_roles_tenant_id", "roles", ["tenant_id"])

    # -----------------------------------------------------------------------
    # alcance_enum (PostgreSQL native enum)
    # -----------------------------------------------------------------------
    alcance_enum = postgresql.ENUM("global", "propio", name="alcance_enum")
    alcance_enum.create(op.get_bind())

    # -----------------------------------------------------------------------
    # permisos
    # -----------------------------------------------------------------------
    op.create_table(
        "permisos",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clave", sa.String(length=100), nullable=False),
        sa.Column("modulo", sa.String(length=50), nullable=False),
        sa.Column("accion", sa.String(length=50), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "clave", name="uq_permisos_tenant_clave"),
    )
    op.create_index("ix_permisos_tenant_id", "permisos", ["tenant_id"])
    op.create_index("ix_permisos_tenant_clave", "permisos", ["tenant_id", "clave"])

    # -----------------------------------------------------------------------
    # rol_permiso
    # -----------------------------------------------------------------------
    op.create_table(
        "rol_permiso",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permiso_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "alcance",
            postgresql.ENUM("global", "propio", name="alcance_enum", create_type=False),
            nullable=False,
            server_default="global",
        ),
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
        sa.ForeignKeyConstraint(["rol_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permiso_id"], ["permisos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "rol_id", "permiso_id",
            name="uq_rol_permiso_tenant_rol_permiso",
        ),
    )
    op.create_index("ix_rol_permiso_tenant_id", "rol_permiso", ["tenant_id"])
    op.create_index("ix_rol_permiso_tenant_rol", "rol_permiso", ["tenant_id", "rol_id"])

    # -----------------------------------------------------------------------
    # usuario_rol
    # -----------------------------------------------------------------------
    op.create_table(
        "usuario_rol",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vigente_desde", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vigente_hasta", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rol_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usuario_rol_tenant_user", "usuario_rol", ["tenant_id", "user_id"])

    # -----------------------------------------------------------------------
    # Seed the base matrix for each existing tenant
    # -----------------------------------------------------------------------
    _run_seed_for_all_tenants()


def _run_seed_for_all_tenants() -> None:
    """Apply the idempotent RBAC seed to every existing tenant."""
    bind = op.get_bind()
    result = bind.execute(sa.text("SELECT id FROM tenants WHERE activo = true"))
    tenant_ids = [row[0] for row in result]

    for tenant_id in tenant_ids:
        from app.services.rbac_seed import seed_rbac_for_tenant  # noqa: PLC0415
        seed_rbac_for_tenant(bind, tenant_id)


def downgrade() -> None:
    op.drop_index("ix_usuario_rol_tenant_user", table_name="usuario_rol")
    op.drop_table("usuario_rol")

    op.drop_index("ix_rol_permiso_tenant_rol", table_name="rol_permiso")
    op.drop_index("ix_rol_permiso_tenant_id", table_name="rol_permiso")
    op.drop_table("rol_permiso")

    op.drop_index("ix_permisos_tenant_clave", table_name="permisos")
    op.drop_index("ix_permisos_tenant_id", table_name="permisos")
    op.drop_table("permisos")

    op.drop_index("ix_roles_tenant_id", table_name="roles")
    op.drop_table("roles")

    alcance_enum = postgresql.ENUM("global", "propio", name="alcance_enum")
    alcance_enum.drop(op.get_bind())

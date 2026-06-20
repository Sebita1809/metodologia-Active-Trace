"""006 estructura academica

Revision ID: 006
Revises: 005
Create Date: 2026-06-09

Creates the academic catalog tables:
  - carreras   — academic programs (degrees), unique code per tenant
  - cohortes   — cohorts of a carrera, unique (tenant, carrera, nombre)
  - materias   — course catalog, unique code per tenant

Unique indexes:
  uq_carrera_tenant_codigo         on (tenant_id, codigo) in carreras
  uq_cohorte_tenant_carrera_nombre on (tenant_id, carrera_id, nombre) in cohortes
  uq_materia_tenant_codigo         on (tenant_id, codigo) in materias

Note on permission seed (task 2.3):
  The `estructura:gestionar` permission and its assignment to the ADMIN role
  were already seeded by migration 004 via rbac_seed.py (PERMISSIONS + MATRIX
  constants include this entry). This migration adds a defensive idempotent
  upsert for any tenant that may have been created between migrations — it uses
  ON CONFLICT DO NOTHING, so re-running is safe.

Implemented: C-06 (estructura-academica)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: str | None = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # carreras
    # -----------------------------------------------------------------------
    op.create_table(
        "carreras",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Activa"),
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
        sa.UniqueConstraint("tenant_id", "codigo", name="uq_carrera_tenant_codigo"),
    )
    op.create_index("ix_carreras_tenant_id", "carreras", ["tenant_id"])

    # -----------------------------------------------------------------------
    # cohortes
    # -----------------------------------------------------------------------
    op.create_table(
        "cohortes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("carrera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("anio", sa.Integer, nullable=False),
        sa.Column("vig_desde", sa.Date, nullable=False),
        sa.Column("vig_hasta", sa.Date, nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Activa"),
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
        sa.ForeignKeyConstraint(["carrera_id"], ["carreras.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "carrera_id", "nombre",
            name="uq_cohorte_tenant_carrera_nombre",
        ),
    )
    op.create_index("ix_cohortes_tenant_id", "cohortes", ["tenant_id"])
    op.create_index("ix_cohortes_carrera_id", "cohortes", ["carrera_id"])

    # -----------------------------------------------------------------------
    # materias
    # -----------------------------------------------------------------------
    op.create_table(
        "materias",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Activa"),
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
        sa.UniqueConstraint("tenant_id", "codigo", name="uq_materia_tenant_codigo"),
    )
    op.create_index("ix_materias_tenant_id", "materias", ["tenant_id"])

    # -----------------------------------------------------------------------
    # Task 2.3: Idempotent seed of estructura:gestionar permission for all
    # tenants. Migration 004 already seeded this via rbac_seed.py, but we
    # re-apply ON CONFLICT DO NOTHING for tenants created after migration 004.
    # -----------------------------------------------------------------------
    _seed_estructura_gestionar_for_all_tenants()


def _seed_estructura_gestionar_for_all_tenants() -> None:
    """Idempotently ensure estructura:gestionar is seeded for every tenant."""
    bind = op.get_bind()

    # Fetch all active tenants
    result = bind.execute(sa.text("SELECT id FROM tenants WHERE activo = true"))
    tenant_ids = [row[0] for row in result]

    for tenant_id in tenant_ids:
        tid = str(tenant_id)

        # Ensure the permission row exists
        bind.execute(
            sa.text(
                """
                INSERT INTO permisos (id, tenant_id, clave, modulo, accion, descripcion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tenant_id, 'estructura:gestionar',
                        'estructura', 'gestionar',
                        'Gestionar estructura académica (carreras, cohortes, materias)',
                        now(), now())
                ON CONFLICT (tenant_id, clave) DO NOTHING
                """
            ),
            {"tenant_id": tid},
        )

        # Ensure the matrix row (ADMIN → estructura:gestionar) exists
        bind.execute(
            sa.text(
                """
                INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, alcance, created_at, updated_at)
                SELECT
                    gen_random_uuid(),
                    :tenant_id,
                    r.id,
                    p.id,
                    CAST('global' AS alcance_enum),
                    now(),
                    now()
                FROM roles r, permisos p
                WHERE r.tenant_id = :tenant_id AND r.nombre = 'ADMIN'
                  AND p.tenant_id = :tenant_id AND p.clave  = 'estructura:gestionar'
                ON CONFLICT (tenant_id, rol_id, permiso_id) DO NOTHING
                """
            ),
            {"tenant_id": tid},
        )


def downgrade() -> None:
    op.drop_index("ix_materias_tenant_id", table_name="materias")
    op.drop_table("materias")

    op.drop_index("ix_cohortes_carrera_id", table_name="cohortes")
    op.drop_index("ix_cohortes_tenant_id", table_name="cohortes")
    op.drop_table("cohortes")

    op.drop_index("ix_carreras_tenant_id", table_name="carreras")
    op.drop_table("carreras")

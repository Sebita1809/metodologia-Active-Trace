"""015 programas y fechas academicas

Revision ID: 015
Revises: 014
Create Date: 2026-06-18

Creates tables for F5.3 (ProgramaMateria) and F5.4 (FechaAcademica),
plus RBAC seed for estructura:gestionar (COORDINADOR, ADMIN).

Tables:
  programa_materia:
    BaseTenantModel (id, tenant_id, created_at, updated_at, deleted_at)
    materia_id  — FK → materias.id RESTRICT
    carrera_id  — FK → carreras.id RESTRICT
    cohorte_id  — FK → cohortes.id RESTRICT
    titulo      — TEXT
    referencia_archivo — TEXT

  fecha_academica:
    BaseTenantModel (id, tenant_id, created_at, updated_at, deleted_at)
    materia_id  — FK → materias.id RESTRICT
    cohorte_id  — FK → cohortes.id RESTRICT
    tipo        — VARCHAR(20) CHECK IN ('Parcial','TP','Coloquio','Recuperatorio')
    numero      — INTEGER CHECK >= 1
    periodo     — TEXT nullable
    fecha       — DATE
    titulo      — TEXT

Unique partial indexes (WHERE deleted_at IS NULL):
  uq_programa_materia_combo     (tenant_id, materia_id, carrera_id, cohorte_id)
  uq_fecha_academica_combo      (tenant_id, materia_id, cohorte_id, tipo, numero)

Regular indexes:
  ix_programa_materia_tenant_materia        (tenant_id, materia_id)
  ix_fecha_academica_tenant_materia_cohorte (tenant_id, materia_id, cohorte_id)

RBAC seed (ON CONFLICT DO NOTHING):
  Permission: estructura:gestionar
  Matrix:
    COORDINADOR → estructura:gestionar (global)
    ADMIN       → estructura:gestionar (global)

Implemented: C-17 (programas-y-fechas-academicas)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015"
down_revision: str | None = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # programa_materia table
    # -----------------------------------------------------------------------
    op.create_table(
        "programa_materia",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("carrera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("titulo", sa.Text, nullable=False),
        sa.Column("referencia_archivo", sa.Text, nullable=False),
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
        sa.ForeignKeyConstraint(["materia_id"], ["materias.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["carrera_id"], ["carreras.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohortes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_programa_materia_tenant_id",
        "programa_materia",
        ["tenant_id"],
    )
    op.create_index(
        "ix_programa_materia_tenant_materia",
        "programa_materia",
        ["tenant_id", "materia_id"],
    )

    # Unique partial index: one vivo programa per combo per tenant
    op.execute(
        """
        CREATE UNIQUE INDEX uq_programa_materia_combo
        ON programa_materia (tenant_id, materia_id, carrera_id, cohorte_id)
        WHERE deleted_at IS NULL
        """
    )

    # -----------------------------------------------------------------------
    # fecha_academica table
    # -----------------------------------------------------------------------
    op.create_table(
        "fecha_academica",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("periodo", sa.Text, nullable=True),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("titulo", sa.Text, nullable=False),
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
        sa.ForeignKeyConstraint(["materia_id"], ["materias.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohortes.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "tipo IN ('Parcial','TP','Coloquio','Recuperatorio')",
            name="ck_fecha_academica_tipo_valid",
        ),
        sa.CheckConstraint(
            "numero >= 1",
            name="ck_fecha_academica_numero_positivo",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_fecha_academica_tenant_id",
        "fecha_academica",
        ["tenant_id"],
    )
    op.create_index(
        "ix_fecha_academica_tenant_materia_cohorte",
        "fecha_academica",
        ["tenant_id", "materia_id", "cohorte_id"],
    )

    # Unique partial index: one vivo combo per tenant
    op.execute(
        """
        CREATE UNIQUE INDEX uq_fecha_academica_combo
        ON fecha_academica (tenant_id, materia_id, cohorte_id, tipo, numero)
        WHERE deleted_at IS NULL
        """
    )

    # Seed RBAC permissions
    _seed_estructura_permissions_for_all_tenants()


def _seed_estructura_permissions_for_all_tenants() -> None:
    """Idempotently seed estructura:gestionar for every active tenant.

    Permission matrix:
      - estructura:gestionar → COORDINADOR, ADMIN (global)

    All inserts use ON CONFLICT DO NOTHING so re-running is safe.
    """
    bind = op.get_bind()

    result = bind.execute(sa.text("SELECT id FROM tenants WHERE activo = true"))
    tenant_ids = [row[0] for row in result]

    permiso = (
        "estructura:gestionar",
        "estructura",
        "gestionar",
        "Gestionar programas y fechas académicas",
    )

    role_perm_matrix = {
        "COORDINADOR": [("estructura:gestionar", "global")],
        "ADMIN":       [("estructura:gestionar", "global")],
    }

    for tenant_id in tenant_ids:
        tid = str(tenant_id)

        # 1. Ensure permission row exists
        clave, modulo, accion, descripcion = permiso
        bind.execute(
            sa.text(
                """
                INSERT INTO permisos (id, tenant_id, clave, modulo, accion, descripcion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tenant_id, :clave, :modulo, :accion, :descripcion, now(), now())
                ON CONFLICT (tenant_id, clave) DO NOTHING
                """
            ),
            {
                "tenant_id": tid,
                "clave": clave,
                "modulo": modulo,
                "accion": accion,
                "descripcion": descripcion,
            },
        )

        # 2. Assign permission to roles
        for rol_nombre, perms in role_perm_matrix.items():
            for perm_clave, alcance in perms:
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, alcance, created_at, updated_at)
                        SELECT
                            gen_random_uuid(),
                            :tenant_id,
                            r.id,
                            p.id,
                            CAST(:alcance AS alcance_enum),
                            now(),
                            now()
                        FROM roles r, permisos p
                        WHERE r.tenant_id = :tenant_id AND r.nombre = :rol_nombre
                          AND p.tenant_id = :tenant_id AND p.clave  = :clave
                        ON CONFLICT (tenant_id, rol_id, permiso_id) DO NOTHING
                        """
                    ),
                    {
                        "tenant_id": tid,
                        "rol_nombre": rol_nombre,
                        "clave": perm_clave,
                        "alcance": alcance,
                    },
                )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_fecha_academica_combo")
    op.drop_index("ix_fecha_academica_tenant_materia_cohorte", table_name="fecha_academica")
    op.drop_index("ix_fecha_academica_tenant_id", table_name="fecha_academica")
    op.drop_table("fecha_academica")

    op.execute("DROP INDEX IF EXISTS uq_programa_materia_combo")
    op.drop_index("ix_programa_materia_tenant_materia", table_name="programa_materia")
    op.drop_index("ix_programa_materia_tenant_id", table_name="programa_materia")
    op.drop_table("programa_materia")

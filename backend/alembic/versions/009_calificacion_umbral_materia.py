"""009 calificacion umbral materia

Revision ID: 009
Revises: 008
Create Date: 2026-06-10

Creates the grade tables and seeds RBAC permissions:
  - umbral_materia — per-asignacion approval threshold configuration
  - calificacion   — individual grade records for alumno × activity pairs

Indexes:
  ix_umbral_materia_tenant_id           — standard tenant filter
  ix_umbral_materia_asignacion_id       — filter by asignacion
  uq_umbral_materia_tenant_asignacion   — UNIQUE partial: (tenant,asignacion) WHERE deleted_at IS NULL
  ix_calificacion_tenant_id             — standard tenant filter
  ix_calificacion_entrada_padron_id     — filter by entrada_padron
  ix_calificacion_tenant_entrada_padron — composite filter

Data seed (ON CONFLICT DO NOTHING):
  Permissions: calificaciones:ver, calificaciones:configurar
  (calificaciones:importar already seeded in C-04 rbac_seed)
  Matrix:
    PROFESOR    → calificaciones:ver (propio), calificaciones:configurar (propio)
    COORDINADOR → calificaciones:ver (global), calificaciones:configurar (global)
    ADMIN       → calificaciones:ver (global), calificaciones:configurar (global)

Implemented: C-10 (calificaciones-y-umbral)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: str | None = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # umbral_materia table
    # -----------------------------------------------------------------------
    op.create_table(
        "umbral_materia",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asignacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("umbral_pct", sa.Integer, nullable=False, server_default="60"),
        sa.Column("valores_aprobatorios", postgresql.JSONB, nullable=False),
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
        sa.ForeignKeyConstraint(["asignacion_id"], ["asignaciones.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["materia_id"], ["materias.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_umbral_materia_tenant_id", "umbral_materia", ["tenant_id"])
    op.create_index("ix_umbral_materia_asignacion_id", "umbral_materia", ["asignacion_id"])

    # Partial unique index: one umbral per (tenant, asignacion) while not deleted
    op.create_index(
        "uq_umbral_materia_tenant_asignacion",
        "umbral_materia",
        ["tenant_id", "asignacion_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # -----------------------------------------------------------------------
    # calificacion table
    # -----------------------------------------------------------------------
    op.create_table(
        "calificacion",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entrada_padron_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actividad", sa.String(length=300), nullable=False),
        sa.Column("nota_numerica", sa.Numeric(5, 2), nullable=True),
        sa.Column("nota_textual", sa.String(length=200), nullable=True),
        sa.Column("aprobado", sa.Boolean, nullable=False),
        sa.Column("origen", sa.String(length=20), nullable=False),
        sa.Column("importado_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["entrada_padron_id"], ["entrada_padron.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["materia_id"], ["materias.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_calificacion_tenant_id", "calificacion", ["tenant_id"])
    op.create_index("ix_calificacion_entrada_padron_id", "calificacion", ["entrada_padron_id"])

    # Composite index for common query: tenant + entrada_padron
    op.create_index(
        "ix_calificacion_tenant_entrada_padron",
        "calificacion",
        ["tenant_id", "entrada_padron_id"],
    )

    # Seed calificaciones permissions for all active tenants
    _seed_calificaciones_permissions_for_all_tenants()


def _seed_calificaciones_permissions_for_all_tenants() -> None:
    """Idempotently seed calificaciones:ver and calificaciones:configurar for every active tenant.

    NOTE: calificaciones:importar already exists in the DB from the initial RBAC seed (C-04).
    Only calificaciones:ver and calificaciones:configurar are new in C-10.

    Permissions:
      - calificaciones:ver         → PROFESOR (propio), COORDINADOR (global), ADMIN (global)
      - calificaciones:configurar  → PROFESOR (propio), COORDINADOR (global), ADMIN (global)

    All inserts use ON CONFLICT DO NOTHING so re-running is safe.
    """
    bind = op.get_bind()

    result = bind.execute(sa.text("SELECT id FROM tenants WHERE activo = true"))
    tenant_ids = [row[0] for row in result]

    permisos_a_seed = [
        ("calificaciones:ver",        "calificaciones", "ver",        "Ver calificaciones"),
        ("calificaciones:configurar", "calificaciones", "configurar", "Configurar umbral de calificaciones"),
    ]

    # rol_nombre → list of (permiso_clave, alcance)
    role_perm_matrix = {
        "PROFESOR":    [("calificaciones:ver", "propio"), ("calificaciones:configurar", "propio")],
        "COORDINADOR": [("calificaciones:ver", "global"), ("calificaciones:configurar", "global")],
        "ADMIN":       [("calificaciones:ver", "global"), ("calificaciones:configurar", "global")],
    }

    for tenant_id in tenant_ids:
        tid = str(tenant_id)

        # 1. Ensure permission rows exist
        for clave, modulo, accion, descripcion in permisos_a_seed:
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

        # 2. Assign permissions to roles
        for rol_nombre, perms in role_perm_matrix.items():
            for clave, alcance in perms:
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
                        "clave": clave,
                        "alcance": alcance,
                    },
                )


def downgrade() -> None:
    # Drop indexes and tables in reverse order
    op.drop_index("ix_calificacion_tenant_entrada_padron", table_name="calificacion")
    op.drop_index("ix_calificacion_entrada_padron_id", table_name="calificacion")
    op.drop_index("ix_calificacion_tenant_id", table_name="calificacion")
    op.drop_table("calificacion")

    op.drop_index("uq_umbral_materia_tenant_asignacion", table_name="umbral_materia")
    op.drop_index("ix_umbral_materia_asignacion_id", table_name="umbral_materia")
    op.drop_index("ix_umbral_materia_tenant_id", table_name="umbral_materia")
    op.drop_table("umbral_materia")

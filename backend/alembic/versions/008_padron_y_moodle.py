"""008 padron y moodle

Revision ID: 008
Revises: 007
Create Date: 2026-06-09

Creates the versioned student roster tables and seeds RBAC permissions:
  - version_padron  — padrón version header (one active per tenant×materia×cohorte)
  - entrada_padron  — individual padrón row (PII email encrypted)

Indexes:
  ix_version_padron_tenant_id            — standard tenant filter
  ix_version_padron_materia_id           — filter by materia
  ix_version_padron_cohorte_id           — filter by cohorte
  ix_version_padron_cargado_por          — filter by uploader
  ix_version_padron_tenant_materia_cohorte — composite filter
  uq_version_padron_activa               — UNIQUE partial: (tenant,materia,cohorte) WHERE activa=true AND deleted_at IS NULL
  ix_entrada_padron_tenant_id            — standard tenant filter
  ix_entrada_padron_version_id           — filter by version

Data seed (ON CONFLICT DO NOTHING):
  Permissions: padron:cargar, padron:ver, padron:vaciar
  Matrix:
    PROFESOR    → padron:cargar (propio), padron:ver (propio), padron:vaciar (propio)
    COORDINADOR → padron:cargar (global), padron:ver (global), padron:vaciar (global)
    ADMIN       → padron:cargar (global), padron:ver (global), padron:vaciar (global)

Implemented: C-09 (padron-ingesta-moodle)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: str | None = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # version_padron table
    # -----------------------------------------------------------------------
    op.create_table(
        "version_padron",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cargado_por", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "cargado_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("activa", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("origen", sa.String(length=20), nullable=False),
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
        sa.ForeignKeyConstraint(["cargado_por"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Standard tenant index (from BaseTenantModel pattern)
    op.create_index("ix_version_padron_tenant_id", "version_padron", ["tenant_id"])
    op.create_index("ix_version_padron_materia_id", "version_padron", ["materia_id"])
    op.create_index("ix_version_padron_cohorte_id", "version_padron", ["cohorte_id"])
    op.create_index("ix_version_padron_cargado_por", "version_padron", ["cargado_por"])

    # Composite index for the most common filter: tenant + materia + cohorte
    op.create_index(
        "ix_version_padron_tenant_materia_cohorte",
        "version_padron",
        ["tenant_id", "materia_id", "cohorte_id"],
    )

    # Task 1.5 — unique partial index: only one active version per (tenant, materia, cohorte)
    op.create_index(
        "uq_version_padron_activa",
        "version_padron",
        ["tenant_id", "materia_id", "cohorte_id"],
        unique=True,
        postgresql_where=sa.text("activa = true AND deleted_at IS NULL"),
    )

    # -----------------------------------------------------------------------
    # entrada_padron table
    # -----------------------------------------------------------------------
    op.create_table(
        "entrada_padron",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("apellidos", sa.String(length=200), nullable=False),
        # PII — stored as AES-256-GCM ciphertext
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("comision", sa.String(length=100), nullable=True),
        sa.Column("regional", sa.String(length=100), nullable=True),
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
        sa.ForeignKeyConstraint(["version_id"], ["version_padron.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_entrada_padron_tenant_id", "entrada_padron", ["tenant_id"])
    op.create_index("ix_entrada_padron_version_id", "entrada_padron", ["version_id"])
    op.create_index("ix_entrada_padron_usuario_id", "entrada_padron", ["usuario_id"])

    # Task 8.1 — Seed padron permissions for all active tenants
    _seed_padron_permissions_for_all_tenants()


def _seed_padron_permissions_for_all_tenants() -> None:
    """Idempotently seed padron permissions for every active tenant.

    Permissions:
      - padron:cargar  → PROFESOR (propio), COORDINADOR (global), ADMIN (global)
      - padron:ver     → PROFESOR (propio), COORDINADOR (global), ADMIN (global)
      - padron:vaciar  → PROFESOR (propio), COORDINADOR (global), ADMIN (global)

    All inserts use ON CONFLICT DO NOTHING so re-running is safe.
    """
    bind = op.get_bind()

    result = bind.execute(sa.text("SELECT id FROM tenants WHERE activo = true"))
    tenant_ids = [row[0] for row in result]

    permisos_a_seed = [
        ("padron:cargar", "padron", "cargar", "Cargar padrón de alumnos"),
        ("padron:ver",    "padron", "ver",    "Ver padrón de alumnos"),
        ("padron:vaciar", "padron", "vaciar", "Vaciar padrón de alumnos"),
    ]

    # rol_nombre → list of (permiso_clave, alcance)
    role_perm_matrix = {
        "PROFESOR":    [("padron:cargar", "propio"), ("padron:ver", "propio"), ("padron:vaciar", "propio")],
        "COORDINADOR": [("padron:cargar", "global"), ("padron:ver", "global"), ("padron:vaciar", "global")],
        "ADMIN":       [("padron:cargar", "global"), ("padron:ver", "global"), ("padron:vaciar", "global")],
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
    # Task 1.6 — drop in reverse order (entrada_padron before version_padron)
    op.drop_index("ix_entrada_padron_usuario_id", table_name="entrada_padron")
    op.drop_index("ix_entrada_padron_version_id", table_name="entrada_padron")
    op.drop_index("ix_entrada_padron_tenant_id", table_name="entrada_padron")
    op.drop_table("entrada_padron")

    op.drop_index("uq_version_padron_activa", table_name="version_padron")
    op.drop_index("ix_version_padron_tenant_materia_cohorte", table_name="version_padron")
    op.drop_index("ix_version_padron_cargado_por", table_name="version_padron")
    op.drop_index("ix_version_padron_cohorte_id", table_name="version_padron")
    op.drop_index("ix_version_padron_materia_id", table_name="version_padron")
    op.drop_index("ix_version_padron_tenant_id", table_name="version_padron")
    op.drop_table("version_padron")

"""013 avisos y acknowledgment

Revision ID: 013
Revises: 012
Create Date: 2026-06-18

Creates the notice board tables and seeds RBAC permissions:
  - aviso              — institutional notices with audience segmentation
  - acknowledgment_aviso — user read-confirmation records

CHECK constraints (VARCHAR-based — NOT PG ENUM type):
  alcance   IN ('Global','PorMateria','PorCohorte','PorRol')
  severidad IN ('Info','Advertencia','Critico')

Indexes on aviso:
  ix_aviso_tenant_id         — standard tenant filter
  ix_aviso_tenant_alcance    — filter by (tenant, alcance) for audience queries
  ix_aviso_tenant_materia    — filter by (tenant, materia_id) for PorMateria audience
  ix_aviso_tenant_cohorte    — filter by (tenant, cohorte_id) for PorCohorte audience

Indexes on acknowledgment_aviso:
  ix_ack_aviso_tenant_id      — standard tenant filter
  ix_ack_aviso_tenant_aviso   — filter by (tenant, aviso_id) for counting acks
  uq_ack_aviso_usuario        — UNIQUE (aviso_id, usuario_id) prevents duplicate acks

Data seed (ON CONFLICT DO NOTHING):
  Permissions: avisos:publicar, avisos:ack
  Matrix:
    COORDINADOR  → avisos:publicar (global)
    ADMIN        → avisos:publicar (global)
    ALUMNO       → avisos:ack (global)
    TUTOR        → avisos:ack (global)
    PROFESOR     → avisos:ack (global)
    COORDINADOR  → avisos:ack (global)
    NEXO         → avisos:ack (global)
    ADMIN        → avisos:ack (global)
    FINANZAS     → avisos:ack (global)

Implemented: C-15 (avisos-y-acknowledgment)

NOTE: The orchestrator will rename this file to 013_avisos.py and update
revision="013", down_revision="012" when merging to main.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: str | None = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # aviso table
    # -----------------------------------------------------------------------
    op.create_table(
        "aviso",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alcance", sa.String(length=20), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rol_destino", sa.String(length=50), nullable=True),
        sa.Column(
            "severidad",
            sa.String(length=20),
            nullable=False,
            server_default="Info",
        ),
        sa.Column("titulo", sa.String(length=300), nullable=False),
        sa.Column("cuerpo", sa.String(length=10000), nullable=False),
        sa.Column("inicio_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "orden", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column(
            "activo", sa.Boolean, nullable=False, server_default="true"
        ),
        sa.Column(
            "requiere_ack", sa.Boolean, nullable=False, server_default="false"
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
        sa.ForeignKeyConstraint(["materia_id"], ["materias.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohortes.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "alcance IN ('Global','PorMateria','PorCohorte','PorRol')",
            name="ck_aviso_alcance",
        ),
        sa.CheckConstraint(
            "severidad IN ('Info','Advertencia','Critico')",
            name="ck_aviso_severidad",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_aviso_tenant_id", "aviso", ["tenant_id"])
    op.create_index("ix_aviso_tenant_alcance", "aviso", ["tenant_id", "alcance"])
    op.create_index("ix_aviso_tenant_materia", "aviso", ["tenant_id", "materia_id"])
    op.create_index("ix_aviso_tenant_cohorte", "aviso", ["tenant_id", "cohorte_id"])

    # -----------------------------------------------------------------------
    # acknowledgment_aviso table
    # -----------------------------------------------------------------------
    op.create_table(
        "acknowledgment_aviso",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aviso_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "confirmado_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
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
        sa.ForeignKeyConstraint(["aviso_id"], ["aviso.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("aviso_id", "usuario_id", name="uq_ack_aviso_usuario"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_ack_aviso_tenant_id", "acknowledgment_aviso", ["tenant_id"])
    op.create_index(
        "ix_ack_aviso_tenant_aviso",
        "acknowledgment_aviso",
        ["tenant_id", "aviso_id"],
    )

    # Seed RBAC permissions
    _seed_avisos_permissions_for_all_tenants()


def _seed_avisos_permissions_for_all_tenants() -> None:
    """Idempotently seed avisos:publicar and avisos:ack for every active tenant.

    Permissions:
      - avisos:publicar → COORDINADOR (global), ADMIN (global)
      - avisos:ack      → ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS (global)

    All inserts use ON CONFLICT DO NOTHING so re-running is safe.
    """
    bind = op.get_bind()

    result = bind.execute(sa.text("SELECT id FROM tenants WHERE activo = true"))
    tenant_ids = [row[0] for row in result]

    permisos_a_seed = [
        ("avisos:publicar", "avisos", "publicar", "Publicar avisos institucionales"),
        ("avisos:ack",      "avisos", "ack",      "Acusar recibo de avisos"),
    ]

    # rol_nombre → list of (permiso_clave, alcance)
    role_perm_matrix = {
        "COORDINADOR": [("avisos:publicar", "global"), ("avisos:ack", "global")],
        "ADMIN":       [("avisos:publicar", "global"), ("avisos:ack", "global")],
        "ALUMNO":      [("avisos:ack", "global")],
        "TUTOR":       [("avisos:ack", "global")],
        "PROFESOR":    [("avisos:ack", "global")],
        "NEXO":        [("avisos:ack", "global")],
        "FINANZAS":    [("avisos:ack", "global")],
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
    op.drop_index("ix_ack_aviso_tenant_aviso", table_name="acknowledgment_aviso")
    op.drop_index("ix_ack_aviso_tenant_id", table_name="acknowledgment_aviso")
    op.drop_table("acknowledgment_aviso")

    op.drop_index("ix_aviso_tenant_cohorte", table_name="aviso")
    op.drop_index("ix_aviso_tenant_materia", table_name="aviso")
    op.drop_index("ix_aviso_tenant_alcance", table_name="aviso")
    op.drop_index("ix_aviso_tenant_id", table_name="aviso")
    op.drop_table("aviso")

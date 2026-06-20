"""007 usuarios y asignaciones

Revision ID: 007
Revises: 006
Create Date: 2026-06-09

Creates the person-profile and role-assignment tables:
  - usuarios    — person profiles with encrypted PII
  - asignaciones — role assignments with temporal validity

Indexes:
  uq_usuario_tenant_email_hash  UNIQUE on (tenant_id, email_hash) in usuarios
  ix_usuarios_tenant_estado     on (tenant_id, estado) in usuarios
  ix_asignaciones_tenant_usuario on (tenant_id, usuario_id)
  ix_asignaciones_tenant_materia on (tenant_id, materia_id)
  ix_asignaciones_tenant_responsable on (tenant_id, responsable_id)

Data seed (ON CONFLICT DO NOTHING):
  Permissions: usuarios:gestionar, equipos:asignar, asignaciones:gestionar
  Matrix:
    ADMIN        → usuarios:gestionar, equipos:asignar, asignaciones:gestionar
    COORDINADOR  → equipos:asignar, asignaciones:gestionar

Implemented: C-07 (usuarios-y-asignaciones)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: str | None = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Task 2.2 — usuarios table
    # -----------------------------------------------------------------------
    op.create_table(
        "usuarios",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("apellidos", sa.String(length=200), nullable=False),
        # PII — stored as AES-256-GCM ciphertext
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("email_hash", sa.String(length=64), nullable=False),
        # Optional PII — nullable ciphertexts
        sa.Column("dni", sa.Text, nullable=True),
        sa.Column("cuil", sa.Text, nullable=True),
        sa.Column("cbu", sa.Text, nullable=True),
        sa.Column("alias_cbu", sa.Text, nullable=True),
        # Non-PII optional fields
        sa.Column("banco", sa.String(length=100), nullable=True),
        sa.Column("regional", sa.String(length=100), nullable=True),
        sa.Column("legajo", sa.String(length=50), nullable=True),
        sa.Column("legajo_profesional", sa.String(length=50), nullable=True),
        sa.Column("facturador", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Activo"),
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
    )
    op.create_index("ix_usuarios_tenant_id", "usuarios", ["tenant_id"])

    # Task 2.3 — unique email_hash per tenant + estado index
    op.create_index(
        "uq_usuario_tenant_email_hash",
        "usuarios",
        ["tenant_id", "email_hash"],
        unique=True,
    )
    op.create_index(
        "ix_usuarios_tenant_estado",
        "usuarios",
        ["tenant_id", "estado"],
    )

    # -----------------------------------------------------------------------
    # Task 2.4 — asignaciones table
    # -----------------------------------------------------------------------
    op.create_table(
        "asignaciones",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rol", sa.String(length=30), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("carrera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "comisiones",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("responsable_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("desde", sa.Date, nullable=False),
        sa.Column("hasta", sa.Date, nullable=True),
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
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["materia_id"], ["materias.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["carrera_id"], ["carreras.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohortes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["responsable_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asignaciones_tenant_id", "asignaciones", ["tenant_id"])

    # Task 2.5 — support indexes for common filter queries
    op.create_index(
        "ix_asignaciones_tenant_usuario",
        "asignaciones",
        ["tenant_id", "usuario_id"],
    )
    op.create_index(
        "ix_asignaciones_tenant_materia",
        "asignaciones",
        ["tenant_id", "materia_id"],
    )
    op.create_index(
        "ix_asignaciones_tenant_responsable",
        "asignaciones",
        ["tenant_id", "responsable_id"],
    )

    # Task 2.6 — defensive permission seed for all active tenants
    _seed_usuarios_permissions_for_all_tenants()


def _seed_usuarios_permissions_for_all_tenants() -> None:
    """Idempotently seed usuarios/asignaciones permissions for every active tenant.

    Permissions:
      - usuarios:gestionar  → ADMIN
      - equipos:asignar     → ADMIN, COORDINADOR
      - asignaciones:gestionar → ADMIN, COORDINADOR

    All inserts use ON CONFLICT DO NOTHING so re-running is safe.
    """
    bind = op.get_bind()

    result = bind.execute(sa.text("SELECT id FROM tenants WHERE activo = true"))
    tenant_ids = [row[0] for row in result]

    permisos_a_seed = [
        ("usuarios:gestionar", "usuarios", "gestionar", "Gestionar perfiles de usuario"),
        ("equipos:asignar", "equipos", "asignar", "Asignar docentes a equipos"),
        ("asignaciones:gestionar", "asignaciones", "gestionar", "Gestionar asignaciones de roles"),
    ]

    # Which roles get which permissions
    # rol_nombre → list of permission claves
    role_perm_matrix = {
        "ADMIN": ["usuarios:gestionar", "equipos:asignar", "asignaciones:gestionar"],
        "COORDINADOR": ["equipos:asignar", "asignaciones:gestionar"],
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
        for rol_nombre, claves in role_perm_matrix.items():
            for clave in claves:
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
                        WHERE r.tenant_id = :tenant_id AND r.nombre = :rol_nombre
                          AND p.tenant_id = :tenant_id AND p.clave  = :clave
                        ON CONFLICT (tenant_id, rol_id, permiso_id) DO NOTHING
                        """
                    ),
                    {
                        "tenant_id": tid,
                        "rol_nombre": rol_nombre,
                        "clave": clave,
                    },
                )


def downgrade() -> None:
    op.drop_index("ix_asignaciones_tenant_responsable", table_name="asignaciones")
    op.drop_index("ix_asignaciones_tenant_materia", table_name="asignaciones")
    op.drop_index("ix_asignaciones_tenant_usuario", table_name="asignaciones")
    op.drop_index("ix_asignaciones_tenant_id", table_name="asignaciones")
    op.drop_table("asignaciones")

    op.drop_index("ix_usuarios_tenant_estado", table_name="usuarios")
    op.drop_index("uq_usuario_tenant_email_hash", table_name="usuarios")
    op.drop_index("ix_usuarios_tenant_id", table_name="usuarios")
    op.drop_table("usuarios")

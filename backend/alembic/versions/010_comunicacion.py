"""010 comunicacion

Revision ID: 010
Revises: 009
Create Date: 2026-06-18

Creates the comunicacion table (E21) for C-12 (comunicaciones-cola-worker).

Table: comunicacion
  - Full BaseTenantModel fields (id, tenant_id, created_at, updated_at, deleted_at)
  - enviado_por  FK → usuarios.id (actor who enqueued)
  - materia_id   FK → materias.id
  - destinatario TEXT — AES-256-GCM ciphertext of recipient email (PII cifrada)
  - asunto       VARCHAR(500)
  - cuerpo       VARCHAR(10000)
  - estado       VARCHAR(20) CHECK IN ('Pendiente','Enviando','Enviado','Error','Cancelado')
                 DEFAULT 'Pendiente'
  - lote_id      UUID — groups all messages in one encolar_lote call
  - enviado_at   TIMESTAMPTZ nullable — set when message reaches Enviado
  - aprobado_at  TIMESTAMPTZ nullable — approval timestamp (D-02 flag, orthogonal)
  - aprobado_por UUID nullable FK → usuarios.id — approver identity

Indexes:
  ix_comunicacion_tenant_id           — standard tenant filter
  ix_comunicacion_lote_id             — lote filter
  ix_comunicacion_tenant_lote         — composite: (tenant_id, lote_id) for lote queries
  ix_comunicacion_tenant_estado       — composite: (tenant_id, estado) for state queries

Data seed: communicacion:enviar and comunicacion:aprobar permissions (already in
           rbac_seed.py from C-04, so only matrix updates needed for new roles).
           Permissions were seeded in C-04 migration; this migration ensures
           analisis permisos exist and seeds comunicacion matrix for all tenants.

Rollback: downgrade drops indexes, CHECK constraint, and the table.

Implemented: C-12 (comunicaciones-cola-worker)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: str | None = "009"
branch_labels = None
depends_on = None

_VALID_ESTADOS = ("Pendiente", "Enviando", "Enviado", "Error", "Cancelado")


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # comunicacion table
    # -----------------------------------------------------------------------
    op.create_table(
        "comunicacion",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enviado_por", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        # PII: destinatario is always AES-256-GCM ciphertext — never plaintext email
        sa.Column(
            "destinatario",
            sa.String(1024),
            nullable=False,
            comment="PII cifrada AES-256-GCM (email del alumno destinatario)",
        ),
        sa.Column("asunto", sa.String(500), nullable=False),
        sa.Column("cuerpo", sa.String(10000), nullable=False),
        sa.Column(
            "estado",
            sa.String(20),
            nullable=False,
            server_default="Pendiente",
        ),
        sa.Column("lote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enviado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aprobado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aprobado_por", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["enviado_por"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["materia_id"], ["materias.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["aprobado_por"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "estado IN ('Pendiente','Enviando','Enviado','Error','Cancelado')",
            name="ck_comunicacion_estado_valid",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Standard tenant filter index
    op.create_index("ix_comunicacion_tenant_id", "comunicacion", ["tenant_id"])

    # lote_id index (for per-lote queries)
    op.create_index("ix_comunicacion_lote_id", "comunicacion", ["lote_id"])

    # Composite index: (tenant_id, lote_id) — most common query pattern for approval/tracking
    op.create_index(
        "ix_comunicacion_tenant_lote",
        "comunicacion",
        ["tenant_id", "lote_id"],
    )

    # Composite index: (tenant_id, estado) — worker and filter queries
    op.create_index(
        "ix_comunicacion_tenant_estado",
        "comunicacion",
        ["tenant_id", "estado"],
    )

    # Seed comunicacion permissions for all active tenants
    _seed_comunicacion_permissions_for_all_tenants()


def _seed_comunicacion_permissions_for_all_tenants() -> None:
    """Ensure comunicacion:enviar and comunicacion:aprobar exist and are assigned.

    comunicacion:enviar  → PROFESOR (propio), COORDINADOR (global), ADMIN (global)
    comunicacion:aprobar → COORDINADOR (global), ADMIN (global)

    Uses ON CONFLICT DO NOTHING — safe to re-run.
    """
    bind = op.get_bind()

    result = bind.execute(sa.text("SELECT id FROM tenants WHERE activo = true"))
    tenant_ids = [row[0] for row in result]

    permisos_a_seed = [
        ("comunicacion:enviar",  "comunicacion", "enviar",  "Enviar comunicaciones a alumnos"),
        ("comunicacion:aprobar", "comunicacion", "aprobar", "Aprobar comunicaciones masivas"),
    ]

    role_perm_matrix = {
        "PROFESOR":    [("comunicacion:enviar",  "propio")],
        "COORDINADOR": [("comunicacion:enviar",  "global"), ("comunicacion:aprobar", "global")],
        "ADMIN":       [("comunicacion:enviar",  "global"), ("comunicacion:aprobar", "global")],
    }

    for tenant_id in tenant_ids:
        tid = str(tenant_id)

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
    op.drop_index("ix_comunicacion_tenant_estado", table_name="comunicacion")
    op.drop_index("ix_comunicacion_tenant_lote", table_name="comunicacion")
    op.drop_index("ix_comunicacion_lote_id", table_name="comunicacion")
    op.drop_index("ix_comunicacion_tenant_id", table_name="comunicacion")
    op.drop_table("comunicacion")

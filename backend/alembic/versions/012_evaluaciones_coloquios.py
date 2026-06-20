"""012 evaluaciones coloquios

Revision ID: 012
Revises: 011
Create Date: 2026-06-18

Creates the evaluation scheduling tables and seeds RBAC permissions:
  - evaluacion          — scheduled exam/evaluation per materia × cohorte
  - reserva_evaluacion  — alumno slot reservation
  - resultado_evaluacion — final grade record per alumno × evaluacion

Indexes:
  ix_evaluacion_tenant_id              — standard tenant filter
  ix_evaluacion_materia_id             — filter by materia
  ix_evaluacion_tenant_materia         — composite filter
  ix_reserva_evaluacion_tenant_id      — standard tenant filter
  ix_reserva_evaluacion_evaluacion_id  — filter by evaluacion
  ix_reserva_evaluacion_tenant_eval    — composite filter
  uq_reserva_activa_alumno_eval        — UNIQUE PARTIAL: (evaluacion_id, alumno_id) WHERE estado='Activa'
  ix_resultado_evaluacion_tenant_id    — standard tenant filter
  ix_resultado_evaluacion_evaluacion_id— filter by evaluacion
  uq_resultado_alumno_eval             — UNIQUE: (evaluacion_id, alumno_id) WHERE deleted_at IS NULL

Data seed (ON CONFLICT DO NOTHING):
  Permissions: coloquios:gestionar, coloquios:ver, coloquios:reservar
  Matrix:
    COORDINADOR → coloquios:gestionar (global), coloquios:ver (global)
    ADMIN       → coloquios:gestionar (global), coloquios:ver (global)
    PROFESOR    → coloquios:ver (propio)
    ALUMNO      → coloquios:reservar (propio)

Implemented: C-14 (evaluaciones-y-coloquios)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: str | None = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # evaluacion table
    # -----------------------------------------------------------------------
    op.create_table(
        "evaluacion",
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
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="Activa"),
        sa.Column("instancia", sa.String(length=200), nullable=False),
        sa.Column("dias_disponibles", sa.Integer, nullable=False),
        sa.Column("cupo_por_dia", sa.Integer, nullable=False),
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
        sa.CheckConstraint(
            "tipo IN ('Parcial','TP','Coloquio','Recuperatorio')",
            name="ck_evaluacion_tipo",
        ),
        sa.CheckConstraint(
            "estado IN ('Activa','Cerrada')",
            name="ck_evaluacion_estado",
        ),
        sa.CheckConstraint(
            "dias_disponibles > 0",
            name="ck_evaluacion_dias_disponibles_positive",
        ),
        sa.CheckConstraint(
            "cupo_por_dia > 0",
            name="ck_evaluacion_cupo_por_dia_positive",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["materia_id"], ["materias.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohortes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_evaluacion_tenant_id", "evaluacion", ["tenant_id"])
    op.create_index("ix_evaluacion_materia_id", "evaluacion", ["materia_id"])
    op.create_index(
        "ix_evaluacion_tenant_materia",
        "evaluacion",
        ["tenant_id", "materia_id"],
    )

    # -----------------------------------------------------------------------
    # reserva_evaluacion table
    # -----------------------------------------------------------------------
    op.create_table(
        "reserva_evaluacion",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alumno_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=False),
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
        sa.CheckConstraint(
            "estado IN ('Activa','Cancelada')",
            name="ck_reserva_evaluacion_estado",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["evaluacion_id"], ["evaluacion.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["alumno_id"], ["usuarios.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_reserva_evaluacion_tenant_id", "reserva_evaluacion", ["tenant_id"])
    op.create_index(
        "ix_reserva_evaluacion_evaluacion_id", "reserva_evaluacion", ["evaluacion_id"]
    )
    op.create_index(
        "ix_reserva_evaluacion_tenant_eval",
        "reserva_evaluacion",
        ["tenant_id", "evaluacion_id"],
    )

    # Unique partial index: one active reservation per (evaluacion, alumno)
    op.create_index(
        "uq_reserva_activa_alumno_eval",
        "reserva_evaluacion",
        ["evaluacion_id", "alumno_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'Activa' AND deleted_at IS NULL"),
    )

    # -----------------------------------------------------------------------
    # resultado_evaluacion table
    # -----------------------------------------------------------------------
    op.create_table(
        "resultado_evaluacion",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alumno_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nota_final", sa.String(length=100), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["evaluacion_id"], ["evaluacion.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["alumno_id"], ["usuarios.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_resultado_evaluacion_tenant_id", "resultado_evaluacion", ["tenant_id"]
    )
    op.create_index(
        "ix_resultado_evaluacion_evaluacion_id",
        "resultado_evaluacion",
        ["evaluacion_id"],
    )
    op.create_index(
        "ix_resultado_evaluacion_tenant_eval",
        "resultado_evaluacion",
        ["tenant_id", "evaluacion_id"],
    )

    # Unique partial index: one resultado per (evaluacion, alumno) while not deleted
    op.create_index(
        "uq_resultado_alumno_eval",
        "resultado_evaluacion",
        ["evaluacion_id", "alumno_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Seed RBAC permissions for all active tenants
    _seed_coloquios_permissions_for_all_tenants()


def _seed_coloquios_permissions_for_all_tenants() -> None:
    """Idempotently seed coloquios permissions for every active tenant.

    Permissions:
      - coloquios:gestionar — COORDINADOR (global), ADMIN (global)
      - coloquios:ver       — COORDINADOR (global), ADMIN (global), PROFESOR (propio)
      - coloquios:reservar  — ALUMNO (propio)

    All inserts use ON CONFLICT DO NOTHING so re-running is safe.
    """
    bind = op.get_bind()

    result = bind.execute(sa.text("SELECT id FROM tenants WHERE activo = true"))
    tenant_ids = [row[0] for row in result]

    permisos_a_seed = [
        (
            "coloquios:gestionar",
            "coloquios",
            "gestionar",
            "Gestionar evaluaciones y coloquios",
        ),
        (
            "coloquios:ver",
            "coloquios",
            "ver",
            "Ver evaluaciones y coloquios",
        ),
        (
            "coloquios:reservar",
            "coloquios",
            "reservar",
            "Reservar turno en un coloquio",
        ),
    ]

    # rol_nombre → list of (permiso_clave, alcance)
    role_perm_matrix = {
        "COORDINADOR": [
            ("coloquios:gestionar", "global"),
            ("coloquios:ver", "global"),
        ],
        "ADMIN": [
            ("coloquios:gestionar", "global"),
            ("coloquios:ver", "global"),
        ],
        "PROFESOR": [
            ("coloquios:ver", "propio"),
        ],
        "ALUMNO": [
            ("coloquios:reservar", "propio"),
        ],
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
    # Drop indexes and tables in reverse dependency order
    op.drop_index("uq_resultado_alumno_eval", table_name="resultado_evaluacion")
    op.drop_index(
        "ix_resultado_evaluacion_tenant_eval", table_name="resultado_evaluacion"
    )
    op.drop_index(
        "ix_resultado_evaluacion_evaluacion_id", table_name="resultado_evaluacion"
    )
    op.drop_index(
        "ix_resultado_evaluacion_tenant_id", table_name="resultado_evaluacion"
    )
    op.drop_table("resultado_evaluacion")

    op.drop_index("uq_reserva_activa_alumno_eval", table_name="reserva_evaluacion")
    op.drop_index(
        "ix_reserva_evaluacion_tenant_eval", table_name="reserva_evaluacion"
    )
    op.drop_index(
        "ix_reserva_evaluacion_evaluacion_id", table_name="reserva_evaluacion"
    )
    op.drop_index(
        "ix_reserva_evaluacion_tenant_id", table_name="reserva_evaluacion"
    )
    op.drop_table("reserva_evaluacion")

    op.drop_index("ix_evaluacion_tenant_materia", table_name="evaluacion")
    op.drop_index("ix_evaluacion_materia_id", table_name="evaluacion")
    op.drop_index("ix_evaluacion_tenant_id", table_name="evaluacion")
    op.drop_table("evaluacion")

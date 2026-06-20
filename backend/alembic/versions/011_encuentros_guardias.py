"""011 encuentros_guardias

Revision ID: 011
Revises: 010
Create Date: 2026-06-18

Creates three tables for C-13 (encuentros-y-guardias):

  slot_encuentro     (E9) — recurring or unique meeting slot definition
  instancia_encuentro (E10) — concrete meeting occurrence (one per date)
  guardia            (E11) — tutor office-hours / guard shift record

All tables include full BaseTenantModel columns:
  id, tenant_id, created_at, updated_at, deleted_at

CHECK constraints:
  ck_slot_encuentro_dia_semana_valid  — dia_semana IN (days)
  ck_instancia_encuentro_estado_valid — estado IN (Programado, Realizado, Cancelado)
  ck_guardia_dia_valid               — dia IN (days)
  ck_guardia_estado_valid            — estado IN (Pendiente, Realizada, Cancelada)

Indexes:
  ix_slot_encuentro_tenant_asignacion  — (tenant_id, asignacion_id)
  ix_slot_encuentro_tenant_materia     — (tenant_id, materia_id)
  ix_instancia_encuentro_tenant_slot   — (tenant_id, slot_id)
  ix_guardia_tenant_asignacion         — (tenant_id, asignacion_id)

RBAC seed:
  encuentros:gestionar → PROFESOR (propio), COORDINADOR (global), ADMIN (global)

Rollback: downgrade drops indexes, constraints, and the three tables.

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: str | None = "010"
branch_labels = None
depends_on = None

_DIAS_VALIDOS = (
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
)
_DIAS_CHECK = ", ".join(f"'{d}'" for d in _DIAS_VALIDOS)

_ESTADOS_INSTANCIA = ("Programado", "Realizado", "Cancelado")
_ESTADOS_GUARDIA = ("Pendiente", "Realizada", "Cancelada")


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # slot_encuentro (E9)
    # -----------------------------------------------------------------------
    op.create_table(
        "slot_encuentro",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asignacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("titulo", sa.String(300), nullable=False),
        sa.Column("hora", sa.Time, nullable=True),
        sa.Column(
            "dia_semana",
            sa.String(20),
            nullable=True,
            comment="Day of week for recurrence; NULL in unique mode",
        ),
        sa.Column("fecha_inicio", sa.Date, nullable=True),
        sa.Column(
            "cant_semanas",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="0 = unique mode; > 0 = recur for N weeks",
        ),
        sa.Column(
            "fecha_unica",
            sa.Date,
            nullable=True,
            comment="Specific date for unique-mode slots",
        ),
        sa.Column("meet_url", sa.String(500), nullable=True),
        sa.Column("vig_desde", sa.Date, nullable=True),
        sa.Column("vig_hasta", sa.Date, nullable=True),
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
            ["asignacion_id"], ["asignaciones.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["materia_id"], ["materias.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            f"dia_semana IN ({_DIAS_CHECK})",
            name="ck_slot_encuentro_dia_semana_valid",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_slot_encuentro_tenant_asignacion",
        "slot_encuentro",
        ["tenant_id", "asignacion_id"],
    )
    op.create_index(
        "ix_slot_encuentro_tenant_materia",
        "slot_encuentro",
        ["tenant_id", "materia_id"],
    )

    # -----------------------------------------------------------------------
    # instancia_encuentro (E10)
    # -----------------------------------------------------------------------
    _estados_inst = ", ".join(f"'{e}'" for e in _ESTADOS_INSTANCIA)
    op.create_table(
        "instancia_encuentro",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "slot_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="NULL for unique encounters (RN-13.2)",
        ),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("hora", sa.Time, nullable=False),
        sa.Column("titulo", sa.String(300), nullable=False),
        sa.Column(
            "estado",
            sa.String(20),
            nullable=False,
            server_default="Programado",
        ),
        sa.Column("meet_url", sa.String(500), nullable=True),
        sa.Column(
            "video_url",
            sa.String(500),
            nullable=True,
            comment="Recording URL — set after meeting is realizado",
        ),
        sa.Column("comentario", sa.String(2000), nullable=True),
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
            ["slot_id"], ["slot_encuentro.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["materia_id"], ["materias.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            f"estado IN ({_estados_inst})",
            name="ck_instancia_encuentro_estado_valid",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_instancia_encuentro_tenant_slot",
        "instancia_encuentro",
        ["tenant_id", "slot_id"],
    )

    # -----------------------------------------------------------------------
    # guardia (E11)
    # -----------------------------------------------------------------------
    _estados_guardia = ", ".join(f"'{e}'" for e in _ESTADOS_GUARDIA)
    op.create_table(
        "guardia",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asignacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("carrera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dia", sa.String(20), nullable=False, comment="Day of week"),
        sa.Column(
            "horario",
            sa.String(50),
            nullable=False,
            comment="Free-text time range, e.g. '14:00–14:45'",
        ),
        sa.Column(
            "estado",
            sa.String(20),
            nullable=False,
            server_default="Pendiente",
        ),
        sa.Column("comentarios", sa.String(2000), nullable=True),
        sa.Column(
            "creada_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Server-side creation timestamp",
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
        sa.ForeignKeyConstraint(
            ["asignacion_id"], ["asignaciones.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["materia_id"], ["materias.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["carrera_id"], ["carreras.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohortes.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            f"dia IN ({_DIAS_CHECK})",
            name="ck_guardia_dia_valid",
        ),
        sa.CheckConstraint(
            f"estado IN ({_estados_guardia})",
            name="ck_guardia_estado_valid",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_guardia_tenant_asignacion",
        "guardia",
        ["tenant_id", "asignacion_id"],
    )

    # Seed RBAC permission for encuentros
    _seed_encuentros_permission()


def _seed_encuentros_permission() -> None:
    """Seed encuentros:gestionar permission for all active tenants.

    encuentros:gestionar → PROFESOR (propio), COORDINADOR (global), ADMIN (global)
    Uses ON CONFLICT DO NOTHING — safe to re-run.
    """
    bind = op.get_bind()

    result = bind.execute(sa.text("SELECT id FROM tenants WHERE activo = true"))
    tenant_ids = [row[0] for row in result]

    role_perm_matrix = {
        "PROFESOR":    [("encuentros:gestionar", "propio")],
        "COORDINADOR": [("encuentros:gestionar", "global")],
        "ADMIN":       [("encuentros:gestionar", "global")],
    }

    for tenant_id in tenant_ids:
        tid = str(tenant_id)

        # Ensure the permission exists
        bind.execute(
            sa.text(
                """
                INSERT INTO permisos (id, tenant_id, clave, modulo, accion, descripcion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tenant_id, 'encuentros:gestionar',
                        'encuentros', 'gestionar', 'Gestionar slots y encuentros', now(), now())
                ON CONFLICT (tenant_id, clave) DO NOTHING
                """
            ),
            {"tenant_id": tid},
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
    op.drop_index("ix_guardia_tenant_asignacion", table_name="guardia")
    op.drop_table("guardia")

    op.drop_index("ix_instancia_encuentro_tenant_slot", table_name="instancia_encuentro")
    op.drop_table("instancia_encuentro")

    op.drop_index("ix_slot_encuentro_tenant_materia", table_name="slot_encuentro")
    op.drop_index("ix_slot_encuentro_tenant_asignacion", table_name="slot_encuentro")
    op.drop_table("slot_encuentro")

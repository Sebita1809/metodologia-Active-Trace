"""014 tareas internas

Revision ID: 014
Revises: 013
Create Date: 2026-06-18

Creates the internal task-management tables and seeds RBAC permissions:
  - tarea            — internal task with assignment, delegation and state machine
  - comentario_tarea — append-only comment thread on a tarea

EstadoTarea is VARCHAR + CheckConstraint (NOT PG ENUM) — consistent with
EstadoGuardia (C-13) and EstadoInstanciaEncuentro.

Tables:
  tarea:
    BaseTenantModel (id, tenant_id, created_at, updated_at, deleted_at)
    materia_id   — nullable FK → materias.id RESTRICT
    asignado_a   — FK → usuarios.id RESTRICT
    asignado_por — FK → usuarios.id RESTRICT
    estado       — VARCHAR(20) CHECK IN ('Pendiente','En progreso','Resuelta','Cancelada')
    descripcion  — TEXT
    contexto_id  — nullable UUID (opaque poly-ref, NO FK)

  comentario_tarea:
    BaseTenantModel (id, tenant_id, created_at, updated_at, deleted_at)
    tarea_id   — FK → tarea.id RESTRICT
    autor_id   — FK → usuarios.id RESTRICT
    texto      — TEXT
    creado_at  — TIMESTAMPTZ server_default now()

Indexes:
  ix_tarea_tenant_asignado_a   (tenant_id, asignado_a)
  ix_tarea_tenant_estado       (tenant_id, estado)
  ix_tarea_tenant_asignado_por (tenant_id, asignado_por)
  ix_comentario_tarea_tenant_tarea (tenant_id, tarea_id)

Data seed (ON CONFLICT DO NOTHING):
  Permission: tareas:gestionar
  Matrix:
    PROFESOR     → tareas:gestionar (global)
    COORDINADOR  → tareas:gestionar (global)
    ADMIN        → tareas:gestionar (global)
    TUTOR        → tareas:gestionar (global)

NOTE: TUTOR permission is seeded at 'global' scope; service layer enforces
      fine-grained "only own tasks" scoping for TUTOR role (D8).

Implemented: C-16 (tareas-internas)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: str | None = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # tarea table
    # -----------------------------------------------------------------------
    op.create_table(
        "tarea",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asignado_a", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asignado_por", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "estado",
            sa.String(length=20),
            nullable=False,
            server_default="Pendiente",
        ),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column("contexto_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["asignado_a"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["asignado_por"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "estado IN ('Pendiente','En progreso','Resuelta','Cancelada')",
            name="ck_tarea_estado_valid",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_tarea_tenant_id", "tarea", ["tenant_id"])
    op.create_index("ix_tarea_tenant_asignado_a", "tarea", ["tenant_id", "asignado_a"])
    op.create_index("ix_tarea_tenant_estado", "tarea", ["tenant_id", "estado"])
    op.create_index(
        "ix_tarea_tenant_asignado_por", "tarea", ["tenant_id", "asignado_por"]
    )

    # -----------------------------------------------------------------------
    # comentario_tarea table
    # -----------------------------------------------------------------------
    op.create_table(
        "comentario_tarea",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tarea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("autor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("texto", sa.Text, nullable=False),
        sa.Column(
            "creado_at",
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
        sa.ForeignKeyConstraint(["tarea_id"], ["tarea.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["autor_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_comentario_tarea_tenant_id", "comentario_tarea", ["tenant_id"]
    )
    op.create_index(
        "ix_comentario_tarea_tenant_tarea",
        "comentario_tarea",
        ["tenant_id", "tarea_id"],
    )

    # Seed RBAC permissions
    _seed_tareas_permissions_for_all_tenants()


def _seed_tareas_permissions_for_all_tenants() -> None:
    """Idempotently seed tareas:gestionar for every active tenant.

    Permission matrix:
      - tareas:gestionar → PROFESOR, COORDINADOR, ADMIN, TUTOR (global)

    NOTE: Fine-grained TUTOR scoping (only own tasks) is enforced at the
    service layer (D8), not at RBAC level.

    All inserts use ON CONFLICT DO NOTHING so re-running is safe.
    """
    bind = op.get_bind()

    result = bind.execute(sa.text("SELECT id FROM tenants WHERE activo = true"))
    tenant_ids = [row[0] for row in result]

    permiso = ("tareas:gestionar", "tareas", "gestionar", "Gestionar tareas internas")

    role_perm_matrix = {
        "PROFESOR":    [("tareas:gestionar", "global")],
        "COORDINADOR": [("tareas:gestionar", "global")],
        "ADMIN":       [("tareas:gestionar", "global")],
        "TUTOR":       [("tareas:gestionar", "global")],
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
    op.drop_index("ix_comentario_tarea_tenant_tarea", table_name="comentario_tarea")
    op.drop_index("ix_comentario_tarea_tenant_id", table_name="comentario_tarea")
    op.drop_table("comentario_tarea")

    op.drop_index("ix_tarea_tenant_asignado_por", table_name="tarea")
    op.drop_index("ix_tarea_tenant_estado", table_name="tarea")
    op.drop_index("ix_tarea_tenant_asignado_a", table_name="tarea")
    op.drop_index("ix_tarea_tenant_id", table_name="tarea")
    op.drop_table("tarea")

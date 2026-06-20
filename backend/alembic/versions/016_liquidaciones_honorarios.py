"""016 liquidaciones y honorarios

Revision ID: 016
Revises: 015
Create Date: 2026-06-18

Creates tables for C-18 (liquidaciones-y-honorarios).

Tables:
  salario_base:
    BaseTenantModel (id, tenant_id, created_at, updated_at, deleted_at)
    rol         — VARCHAR(30)
    monto       — Numeric(12,2) CHECK >= 0
    desde       — DATE NOT NULL
    hasta       — DATE NULL

  salario_plus:
    BaseTenantModel
    clave       — VARCHAR(50)
    rol         — VARCHAR(30)
    descripcion — TEXT NULL
    monto       — Numeric(12,2) CHECK >= 0
    desde       — DATE NOT NULL
    hasta       — DATE NULL

  liquidacion:
    BaseTenantModel
    usuario_id          — UUID FK usuarios RESTRICT
    cohorte_id          — UUID FK cohortes RESTRICT
    periodo_mes         — INT CHECK 1..12
    periodo_anio        — INT CHECK >= 2000
    rol                 — VARCHAR(30)
    comisiones          — JSONB
    base_monto          — Numeric(12,2)
    plus_monto          — Numeric(12,2)
    total_monto         — Numeric(12,2)
    desglose            — JSONB NULL
    es_nexo             — BOOL default false
    excluido_por_factura — BOOL default false
    estado              — VARCHAR(20) default 'Abierta' CHECK IN ('Abierta','Cerrada')
    cerrada_at          — TIMESTAMPTZ NULL

  factura:
    BaseTenantModel
    usuario_id          — UUID FK usuarios RESTRICT
    periodo_mes         — INT CHECK 1..12
    periodo_anio        — INT CHECK >= 2000
    detalle             — TEXT
    referencia_archivo  — TEXT NULL
    tamano_kb           — Numeric(12,2) NULL
    monto               — Numeric(12,2) CHECK >= 0
    estado              — VARCHAR(20) default 'Pendiente' CHECK IN ('Pendiente','Abonada')
    abonada_at          — TIMESTAMPTZ NULL

Also:
  - ALTER TABLE materias ADD COLUMN clave_plus VARCHAR(50) NULL
  - RBAC seed: liquidaciones:* and facturas:gestionar for FINANZAS
  - Audit action: LIQUIDACION_CERRAR

Indexes:
  ix_salario_base_tenant_rol             (tenant_id, rol)
  ix_salario_plus_tenant_clave_rol       (tenant_id, clave, rol)
  uq_liquidacion_combo                   partial unique (tenant_id, usuario_id, cohorte_id, periodo_anio, periodo_mes) WHERE deleted_at IS NULL
  ix_liquidacion_periodo                 (tenant_id, cohorte_id, periodo_anio, periodo_mes)
  ix_factura_tenant_usuario_periodo      (tenant_id, usuario_id, periodo_anio, periodo_mes)

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016"
down_revision: str | None = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # salario_base table
    # -----------------------------------------------------------------------
    op.create_table(
        "salario_base",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rol", sa.String(30), nullable=False),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
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
        sa.CheckConstraint("monto >= 0", name="ck_salario_base_monto_positivo"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_salario_base_tenant_id", "salario_base", ["tenant_id"])
    op.create_index("ix_salario_base_tenant_rol", "salario_base", ["tenant_id", "rol"])

    # -----------------------------------------------------------------------
    # salario_plus table
    # -----------------------------------------------------------------------
    op.create_table(
        "salario_plus",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clave", sa.String(50), nullable=False),
        sa.Column("rol", sa.String(30), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
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
        sa.CheckConstraint("monto >= 0", name="ck_salario_plus_monto_positivo"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_salario_plus_tenant_id", "salario_plus", ["tenant_id"])
    op.create_index(
        "ix_salario_plus_tenant_clave_rol",
        "salario_plus",
        ["tenant_id", "clave", "rol"],
    )

    # -----------------------------------------------------------------------
    # liquidacion table
    # -----------------------------------------------------------------------
    op.create_table(
        "liquidacion",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("periodo_mes", sa.Integer, nullable=False),
        sa.Column("periodo_anio", sa.Integer, nullable=False),
        sa.Column("rol", sa.String(30), nullable=False),
        sa.Column("comisiones", postgresql.JSONB, nullable=False),
        sa.Column("base_monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("plus_monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("desglose", postgresql.JSONB, nullable=True),
        sa.Column("es_nexo", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("excluido_por_factura", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("estado", sa.String(20), nullable=False, server_default="Abierta"),
        sa.Column("cerrada_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohortes.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "periodo_mes >= 1 AND periodo_mes <= 12",
            name="ck_liquidacion_mes_valid",
        ),
        sa.CheckConstraint(
            "periodo_anio >= 2000",
            name="ck_liquidacion_anio_valid",
        ),
        sa.CheckConstraint(
            "estado IN ('Abierta','Cerrada')",
            name="ck_liquidacion_estado_valid",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_liquidacion_tenant_id", "liquidacion", ["tenant_id"])
    op.create_index(
        "ix_liquidacion_periodo",
        "liquidacion",
        ["tenant_id", "cohorte_id", "periodo_anio", "periodo_mes"],
    )

    # Unique partial index: one vivo liquidacion per (tenant, usuario, cohorte, periodo)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_liquidacion_combo
        ON liquidacion (tenant_id, usuario_id, cohorte_id, periodo_anio, periodo_mes)
        WHERE deleted_at IS NULL
        """
    )

    # -----------------------------------------------------------------------
    # factura table
    # -----------------------------------------------------------------------
    op.create_table(
        "factura",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("periodo_mes", sa.Integer, nullable=False),
        sa.Column("periodo_anio", sa.Integer, nullable=False),
        sa.Column("detalle", sa.Text, nullable=False),
        sa.Column("referencia_archivo", sa.Text, nullable=True),
        sa.Column("tamano_kb", sa.Numeric(12, 2), nullable=True),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="Pendiente"),
        sa.Column("abonada_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "periodo_mes >= 1 AND periodo_mes <= 12",
            name="ck_factura_mes_valid",
        ),
        sa.CheckConstraint(
            "periodo_anio >= 2000",
            name="ck_factura_anio_valid",
        ),
        sa.CheckConstraint("monto >= 0", name="ck_factura_monto_positivo"),
        sa.CheckConstraint(
            "estado IN ('Pendiente','Abonada')",
            name="ck_factura_estado_valid",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_factura_tenant_id", "factura", ["tenant_id"])
    op.create_index(
        "ix_factura_tenant_usuario_periodo",
        "factura",
        ["tenant_id", "usuario_id", "periodo_anio", "periodo_mes"],
    )

    # -----------------------------------------------------------------------
    # Alter materias: add clave_plus column
    # -----------------------------------------------------------------------
    op.add_column("materias", sa.Column("clave_plus", sa.String(50), nullable=True))

    # -----------------------------------------------------------------------
    # Seed RBAC
    # -----------------------------------------------------------------------
    _seed_liquidaciones_permissions_for_all_tenants()


def _seed_liquidaciones_permissions_for_all_tenants() -> None:
    """Idempotently seed liquidaciones:* and facturas:gestionar for FINANZAS.

    All inserts use ON CONFLICT DO NOTHING so re-running is safe.
    """
    bind = op.get_bind()

    result = bind.execute(sa.text("SELECT id FROM tenants WHERE activo = true"))
    tenant_ids = [row[0] for row in result]

    permisos = [
        ("liquidaciones:ver", "liquidaciones", "ver", "Ver liquidaciones y honorarios"),
        ("liquidaciones:calcular", "liquidaciones", "calcular", "Calcular liquidaciones del período"),
        ("liquidaciones:cerrar", "liquidaciones", "cerrar", "Cerrar período de liquidaciones"),
        (
            "liquidaciones:configurar-salarios",
            "liquidaciones",
            "configurar-salarios",
            "Gestionar grilla salarial (base y plus)",
        ),
        ("facturas:gestionar", "facturas", "gestionar", "Gestionar facturas de docentes facturantes"),
    ]

    role_perm_matrix = {
        "FINANZAS": [
            ("liquidaciones:ver", "global"),
            ("liquidaciones:calcular", "global"),
            ("liquidaciones:cerrar", "global"),
            ("liquidaciones:configurar-salarios", "global"),
            ("facturas:gestionar", "global"),
        ],
    }

    for tenant_id in tenant_ids:
        tid = str(tenant_id)

        # 1. Ensure permission rows exist
        for clave, modulo, accion, descripcion in permisos:
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
    # Drop column clave_plus from materias
    op.drop_column("materias", "clave_plus")

    # Drop factura
    op.drop_index("ix_factura_tenant_usuario_periodo", table_name="factura")
    op.drop_index("ix_factura_tenant_id", table_name="factura")
    op.drop_table("factura")

    # Drop liquidacion
    op.execute("DROP INDEX IF EXISTS uq_liquidacion_combo")
    op.drop_index("ix_liquidacion_periodo", table_name="liquidacion")
    op.drop_index("ix_liquidacion_tenant_id", table_name="liquidacion")
    op.drop_table("liquidacion")

    # Drop salario_plus
    op.drop_index("ix_salario_plus_tenant_clave_rol", table_name="salario_plus")
    op.drop_index("ix_salario_plus_tenant_id", table_name="salario_plus")
    op.drop_table("salario_plus")

    # Drop salario_base
    op.drop_index("ix_salario_base_tenant_rol", table_name="salario_base")
    op.drop_index("ix_salario_base_tenant_id", table_name="salario_base")
    op.drop_table("salario_base")

"""007_padron: create version_padron, entrada_padron + seed padron:importar.

Revision ID: 007
Revises: 006
Create Date: 2026-06-18 12:00:00.000000
"""
from typing import Sequence, Union

import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Seed UUIDs — deterministic, compatible with migration 003
# ---------------------------------------------------------------------------
_ROLES = {
    "ALUMNO":       "a1111111-1111-1111-1111-111111111111",
    "TUTOR":        "a2222222-2222-2222-2222-222222222222",
    "PROFESOR":     "a3333333-3333-3333-3333-333333333333",
    "COORDINADOR":  "a4444444-4444-4444-4444-444444444444",
    "NEXO":         "a5555555-5555-5555-5555-555555555555",
    "ADMIN":        "a6666666-6666-6666-6666-666666666666",
    "FINANZAS":     "a7777777-7777-7777-7777-777777777777",
}

_PERMISOS = [
    ("b0000014-0000-0000-0000-000000000014", "padron:importar", "padron", "importar"),
]

_PERM_BY_CODE: dict[str, str] = {p[1]: p[0] for p in _PERMISOS}


def _rol_uuid(rol_name: str) -> str:
    return _ROLES[rol_name]


def _perm_uuid(code: str) -> str:
    return _PERM_BY_CODE[code]


def _now() -> datetime.datetime:
    """Return current UTC datetime for seed timestamps.

    Uses a fixed timestamp at import time so all seed rows share one value
    per invocation.  Avoids ``sa.text('now()')`` which asyncpg cannot
    convert to a parameter in ``executemany``.
    """
    return datetime.datetime.now(datetime.timezone.utc)


def _rp_id(n: int) -> str:
    """Deterministic UUID for rol_permiso seed rows."""
    return f"c{n:07d}-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------
def upgrade() -> None:
    _seed_ts = _now()

    # ---- version_padron -------------------------------------------------------
    op.create_table('version_padron',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('materia_id', sa.Uuid(), nullable=False),
        sa.Column('cohorte_id', sa.Uuid(), nullable=False),
        sa.Column('activa', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('origen', sa.String(length=20), nullable=False),
        sa.Column('cargado_por', sa.Uuid(), nullable=False),
        sa.Column('cargado_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['materia_id'], ['materia.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['cohorte_id'], ['cohorte.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['cargado_por'], ['usuario.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_version_padron_tenant_id'), 'version_padron', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_version_padron_deleted_at'), 'version_padron', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_version_padron_materia_cohorte_activa'), 'version_padron', ['materia_id', 'cohorte_id', 'activa'], unique=False)
    op.create_index(op.f('ix_version_padron_cargado_por'), 'version_padron', ['cargado_por'], unique=False)

    # ---- entrada_padron -------------------------------------------------------
    op.create_table('entrada_padron',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('version_id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('usuario_id', sa.Uuid(), nullable=True),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('apellidos', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=500), nullable=False),
        sa.Column('comision', sa.String(length=100), nullable=True),
        sa.Column('regional', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['version_id'], ['version_padron.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_entrada_padron_tenant_id'), 'entrada_padron', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_entrada_padron_deleted_at'), 'entrada_padron', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_entrada_padron_version_id'), 'entrada_padron', ['version_id'], unique=False)
    op.create_index(op.f('ix_entrada_padron_email'), 'entrada_padron', ['email'], unique=False)

    # ---- seed: permission -----------------------------------------------------
    permisos_t = table('permiso',
        column('id', sa.Uuid()),
        column('codigo', sa.String()),
        column('modulo', sa.String()),
        column('accion', sa.String()),
        column('descripcion', sa.String()),
        column('tenant_id', sa.Uuid()),
        column('created_at', sa.DateTime(timezone=True)),
        column('updated_at', sa.DateTime(timezone=True)),
        column('deleted_at', sa.DateTime(timezone=True)),
    )
    op.bulk_insert(permisos_t, [
        {
            'id': pid, 'codigo': code, 'modulo': mod, 'accion': act,
            'descripcion': 'Importar padrón de alumnos desde archivo o Moodle',
            'tenant_id': None,
            'created_at': _seed_ts, 'updated_at': _seed_ts, 'deleted_at': None,
        }
        for pid, code, mod, act in _PERMISOS
    ])

    # ---- seed: rol_permiso matrix ---------------------------------------------
    rp_t = table('rol_permiso',
        column('id', sa.Uuid()),
        column('rol_id', sa.Uuid()),
        column('permiso_id', sa.Uuid()),
        column('alcance', sa.String()),
        column('tenant_id', sa.Uuid()),
        column('created_at', sa.DateTime(timezone=True)),
        column('updated_at', sa.DateTime(timezone=True)),
        column('deleted_at', sa.DateTime(timezone=True)),
    )

    # Continue from 003's last rp seed (c0000038)
    idx = 38

    def _next_id():
        nonlocal idx
        idx += 1
        return _rp_id(idx)

    def _rp(rol_name: str, perm_code: str, alcance: str | None = None) -> dict:
        return {
            'id': _next_id(),
            'rol_id': _rol_uuid(rol_name),
            'permiso_id': _perm_uuid(perm_code),
            'alcance': alcance,
            'tenant_id': None,
            'created_at': _seed_ts,
            'updated_at': _seed_ts,
            'deleted_at': None,
        }

    rp_rows = [
        _rp('COORDINADOR', 'padron:importar'),
        _rp('ADMIN', 'padron:importar'),
        _rp('PROFESOR', 'padron:importar', 'propio'),
    ]

    op.bulk_insert(rp_t, rp_rows)


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------
def downgrade() -> None:
    op.execute(sa.text(
        "DELETE FROM rol_permiso "
        "WHERE permiso_id = 'b0000014-0000-0000-0000-000000000014'"
    ))
    op.execute(sa.text(
        "DELETE FROM permiso WHERE codigo = 'padron:importar'"
    ))

    op.drop_index(op.f('ix_entrada_padron_email'), table_name='entrada_padron')
    op.drop_index(op.f('ix_entrada_padron_version_id'), table_name='entrada_padron')
    op.drop_index(op.f('ix_entrada_padron_deleted_at'), table_name='entrada_padron')
    op.drop_index(op.f('ix_entrada_padron_tenant_id'), table_name='entrada_padron')
    op.drop_table('entrada_padron')

    op.drop_index(op.f('ix_version_padron_cargado_por'), table_name='version_padron')
    op.drop_index(op.f('ix_version_padron_materia_cohorte_activa'), table_name='version_padron')
    op.drop_index(op.f('ix_version_padron_deleted_at'), table_name='version_padron')
    op.drop_index(op.f('ix_version_padron_tenant_id'), table_name='version_padron')
    op.drop_table('version_padron')

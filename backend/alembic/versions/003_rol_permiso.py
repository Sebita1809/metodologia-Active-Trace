"""003_rol_permiso: create rol, permiso, rol_permiso tables + seed data.

Revision ID: 003
Revises: 6def229b8d4a
Create Date: 2026-06-18 12:00:00.000000
"""
from typing import Sequence, Union

import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '6def229b8d4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Seed UUIDs — deterministic so rol_permiso references are predictable
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
    ("b0000001-0000-0000-0000-000000000001", "calificaciones:importar", "calificaciones", "importar"),
    ("b0000002-0000-0000-0000-000000000002", "atrasados:ver",           "atrasados",      "ver"),
    ("b0000003-0000-0000-0000-000000000003", "comunicacion:enviar",     "comunicacion",   "enviar"),
    ("b0000004-0000-0000-0000-000000000004", "comunicacion:aprobar",    "comunicacion",   "aprobar"),
    ("b0000005-0000-0000-0000-000000000005", "equipos:asignar",         "equipos",        "asignar"),
    ("b0000006-0000-0000-0000-000000000006", "encuentros:gestionar",    "encuentros",     "gestionar"),
    ("b0000007-0000-0000-0000-000000000007", "encuentros:ver",          "encuentros",     "ver"),
    ("b0000008-0000-0000-0000-000000000008", "guardias:registrar",      "guardias",       "registrar"),
    ("b0000009-0000-0000-0000-000000000009", "tareas:gestionar",        "tareas",         "gestionar"),
    ("b000000a-0000-0000-0000-00000000000a", "avisos:publicar",         "avisos",         "publicar"),
    ("b000000b-0000-0000-0000-00000000000b", "estructura:gestionar",    "estructura",     "gestionar"),
    ("b000000c-0000-0000-0000-00000000000c", "usuarios:gestionar",      "usuarios",       "gestionar"),
    ("b000000d-0000-0000-0000-00000000000d", "auditoria:ver",           "auditoria",      "ver"),
    ("b000000e-0000-0000-0000-00000000000e", "liquidaciones:gestionar",  "liquidaciones",  "gestionar"),
    ("b000000f-0000-0000-0000-00000000000f", "liquidaciones:cerrar",    "liquidaciones",  "cerrar"),
    ("b0000010-0000-0000-0000-000000000010", "facturas:gestionar",      "facturas",       "gestionar"),
    ("b0000011-0000-0000-0000-000000000011", "salarios:gestionar",      "salarios",       "gestionar"),
    ("b0000012-0000-0000-0000-000000000012", "configuracion:gestionar",  "configuracion",  "gestionar"),
    ("b0000013-0000-0000-0000-000000000013", "impersonacion:usar",      "impersonacion",  "usar"),
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

    # ---- rol -----------------------------------------------------------------
    op.create_table('rol',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('descripcion', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'nombre', name='uq_rol_tenant_nombre'),
    )
    op.create_index(op.f('ix_rol_tenant_id'), 'rol', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_rol_deleted_at'), 'rol', ['deleted_at'], unique=False)

    # ---- permiso -------------------------------------------------------------
    op.create_table('permiso',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('codigo', sa.String(length=100), nullable=False),
        sa.Column('modulo', sa.String(length=50), nullable=False),
        sa.Column('accion', sa.String(length=50), nullable=False),
        sa.Column('descripcion', sa.String(length=500), nullable=True),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo'),
    )
    op.create_index(op.f('ix_permiso_tenant_id'), 'permiso', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_permiso_deleted_at'), 'permiso', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_permiso_codigo'), 'permiso', ['codigo'], unique=False)
    op.create_index(op.f('ix_permiso_modulo_accion'), 'permiso', ['modulo', 'accion'], unique=False)

    # ---- rol_permiso ---------------------------------------------------------
    op.create_table('rol_permiso',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('rol_id', sa.Uuid(), nullable=False),
        sa.Column('permiso_id', sa.Uuid(), nullable=False),
        sa.Column('alcance', sa.String(length=50), nullable=True),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['rol_id'], ['rol.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permiso_id'], ['permiso.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rol_id', 'permiso_id', name='uq_rol_permiso'),
    )
    op.create_index(op.f('ix_rol_permiso_tenant_id'), 'rol_permiso', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_rol_permiso_deleted_at'), 'rol_permiso', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_rol_permiso_rol_id'), 'rol_permiso', ['rol_id'], unique=False)
    op.create_index(op.f('ix_rol_permiso_permiso_id'), 'rol_permiso', ['permiso_id'], unique=False)

    # ---- seed: roles ---------------------------------------------------------
    roles_t = table('rol',
        column('id', sa.Uuid()),
        column('tenant_id', sa.Uuid()),
        column('nombre', sa.String()),
        column('descripcion', sa.String()),
        column('created_at', sa.DateTime(timezone=True)),
        column('updated_at', sa.DateTime(timezone=True)),
        column('deleted_at', sa.DateTime(timezone=True)),
    )
    op.bulk_insert(roles_t, [
        {'id': _rol_uuid('ALUMNO'),      'tenant_id': None,  'nombre': 'ALUMNO',      'descripcion': 'Alumno cursante de una carrera',                                                'created_at': _seed_ts, 'updated_at': _seed_ts, 'deleted_at': None},
        {'id': _rol_uuid('TUTOR'),       'tenant_id': None,  'nombre': 'TUTOR',       'descripcion': 'Tutor de cohorte o comisión',                                                    'created_at': _seed_ts, 'updated_at': _seed_ts, 'deleted_at': None},
        {'id': _rol_uuid('PROFESOR'),    'tenant_id': None,  'nombre': 'PROFESOR',    'descripcion': 'Docente a cargo de una comisión',                                                'created_at': _seed_ts, 'updated_at': _seed_ts, 'deleted_at': None},
        {'id': _rol_uuid('COORDINADOR'), 'tenant_id': None,  'nombre': 'COORDINADOR', 'descripcion': 'Coordinador académico de carrera o área',                                        'created_at': _seed_ts, 'updated_at': _seed_ts, 'deleted_at': None},
        {'id': _rol_uuid('NEXO'),        'tenant_id': None,  'nombre': 'NEXO',        'descripcion': 'Enlace institucional entre el tenant y la plataforma',                             'created_at': _seed_ts, 'updated_at': _seed_ts, 'deleted_at': None},
        {'id': _rol_uuid('ADMIN'),       'tenant_id': None,  'nombre': 'ADMIN',       'descripcion': 'Administrador del tenant con acceso a configuración y usuarios',                   'created_at': _seed_ts, 'updated_at': _seed_ts, 'deleted_at': None},
        {'id': _rol_uuid('FINANZAS'),    'tenant_id': None,  'nombre': 'FINANZAS',    'descripcion': 'Gestor de liquidaciones, facturación y salarios del tenant',                       'created_at': _seed_ts, 'updated_at': _seed_ts, 'deleted_at': None},
    ])

    # ---- seed: permissions ---------------------------------------------------
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
    permiso_desc = {
        'calificaciones:importar': 'Importar calificaciones desde Moodle',
        'atrasados:ver':           'Visualizar reporte de alumnos con entregas atrasadas',
        'comunicacion:enviar':     'Enviar comunicaciones a alumnos',
        'comunicacion:aprobar':    'Aprobar comunicaciones pendientes de envío',
        'equipos:asignar':         'Asignar y modificar equipos docentes',
        'encuentros:gestionar':    'Crear, modificar y cancelar encuentros',
        'encuentros:ver':          'Visualizar calendario de encuentros',
        'guardias:registrar':      'Registrar guardias docentes',
        'tareas:gestionar':        'Gestionar tareas y entregas',
        'avisos:publicar':         'Publicar avisos en el mural del curso',
        'estructura:gestionar':    'Gestionar carreras, materias y comisiones',
        'usuarios:gestionar':      'Gestionar usuarios del tenant',
        'auditoria:ver':           'Consultar registros de auditoría',
        'liquidaciones:gestionar': 'Gestionar liquidaciones de honorarios',
        'liquidaciones:cerrar':    'Cerrar y finalizar liquidaciones',
        'facturas:gestionar':      'Gestionar facturación',
        'salarios:gestionar':      'Gestionar salarios docentes',
        'configuracion:gestionar': 'Gestionar configuración general del tenant',
        'impersonacion:usar':      'Actuar en nombre de otro usuario (impersonación)',
    }
    op.bulk_insert(permisos_t, [
        {
            'id': pid, 'codigo': code, 'modulo': mod, 'accion': act,
            'descripcion': permiso_desc.get(code),
            'tenant_id': None,
            'created_at': _seed_ts, 'updated_at': _seed_ts, 'deleted_at': None,
        }
        for pid, code, mod, act in _PERMISOS
    ])

    # ---- seed: rol_permiso matrix --------------------------------------------
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

    idx = 0

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
        # ---- TUTOR -----------------------------------------------------------
        _rp('TUTOR', 'atrasados:ver'),
        _rp('TUTOR', 'encuentros:gestionar'),
        _rp('TUTOR', 'guardias:registrar', 'propio'),

        # ---- PROFESOR --------------------------------------------------------
        _rp('PROFESOR', 'calificaciones:importar', 'propio'),
        _rp('PROFESOR', 'atrasados:ver', 'propio'),
        _rp('PROFESOR', 'comunicacion:enviar', 'propio'),
        _rp('PROFESOR', 'encuentros:gestionar', 'propio'),
        _rp('PROFESOR', 'guardias:registrar', 'propio'),
        _rp('PROFESOR', 'tareas:gestionar', 'propio'),

        # ---- COORDINADOR -----------------------------------------------------
        _rp('COORDINADOR', 'calificaciones:importar'),
        _rp('COORDINADOR', 'atrasados:ver'),
        _rp('COORDINADOR', 'comunicacion:enviar'),
        _rp('COORDINADOR', 'comunicacion:aprobar'),
        _rp('COORDINADOR', 'encuentros:gestionar'),
        _rp('COORDINADOR', 'guardias:registrar'),
        _rp('COORDINADOR', 'tareas:gestionar'),
        _rp('COORDINADOR', 'avisos:publicar'),
        _rp('COORDINADOR', 'equipos:asignar'),
        _rp('COORDINADOR', 'auditoria:ver', 'propio'),

        # ---- ADMIN -----------------------------------------------------------
        _rp('ADMIN', 'calificaciones:importar'),
        _rp('ADMIN', 'atrasados:ver'),
        _rp('ADMIN', 'comunicacion:enviar'),
        _rp('ADMIN', 'comunicacion:aprobar'),
        _rp('ADMIN', 'encuentros:gestionar'),
        _rp('ADMIN', 'guardias:registrar'),
        _rp('ADMIN', 'tareas:gestionar'),
        _rp('ADMIN', 'avisos:publicar'),
        _rp('ADMIN', 'equipos:asignar'),
        _rp('ADMIN', 'estructura:gestionar'),
        _rp('ADMIN', 'usuarios:gestionar'),
        _rp('ADMIN', 'auditoria:ver'),
        _rp('ADMIN', 'configuracion:gestionar'),
        _rp('ADMIN', 'impersonacion:usar'),

        # ---- FINANZAS --------------------------------------------------------
        _rp('FINANZAS', 'auditoria:ver'),
        _rp('FINANZAS', 'salarios:gestionar'),
        _rp('FINANZAS', 'liquidaciones:gestionar'),
        _rp('FINANZAS', 'liquidaciones:cerrar'),
        _rp('FINANZAS', 'facturas:gestionar'),
    ]

    op.bulk_insert(rp_t, rp_rows)


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------
def downgrade() -> None:
    op.drop_index(op.f('ix_rol_permiso_permiso_id'), table_name='rol_permiso')
    op.drop_index(op.f('ix_rol_permiso_rol_id'), table_name='rol_permiso')
    op.drop_index(op.f('ix_rol_permiso_deleted_at'), table_name='rol_permiso')
    op.drop_index(op.f('ix_rol_permiso_tenant_id'), table_name='rol_permiso')
    op.drop_table('rol_permiso')

    op.drop_index(op.f('ix_permiso_modulo_accion'), table_name='permiso')
    op.drop_index(op.f('ix_permiso_codigo'), table_name='permiso')
    op.drop_index(op.f('ix_permiso_deleted_at'), table_name='permiso')
    op.drop_index(op.f('ix_permiso_tenant_id'), table_name='permiso')
    op.drop_table('permiso')

    op.drop_index(op.f('ix_rol_deleted_at'), table_name='rol')
    op.drop_index(op.f('ix_rol_tenant_id'), table_name='rol')
    op.drop_table('rol')

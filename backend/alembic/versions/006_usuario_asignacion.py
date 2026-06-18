"""006_usuario_asignacion: create usuario and asignacion tables.

Revision ID: 006
Revises: 005
Create Date: 2026-06-18 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- usuario -------------------------------------------------------------
    op.create_table('usuario',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('apellidos', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=500), nullable=False),
        sa.Column('email_hash', sa.String(length=64), nullable=False),
        sa.Column('dni', sa.String(length=500), nullable=True),
        sa.Column('cuil', sa.String(length=500), nullable=True),
        sa.Column('cbu', sa.String(length=500), nullable=True),
        sa.Column('alias_cbu', sa.String(length=500), nullable=True),
        sa.Column('banco', sa.String(length=255), nullable=True),
        sa.Column('regional', sa.String(length=255), nullable=True),
        sa.Column('legajo', sa.String(length=100), nullable=True),
        sa.Column('legajo_profesional', sa.String(length=100), nullable=True),
        sa.Column('facturador', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('estado', sa.String(length=20), nullable=False, server_default=sa.text("'Activa'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'email_hash', name='uq_usuario_tenant_email'),
        sa.UniqueConstraint('tenant_id', 'legajo', name='uq_usuario_tenant_legajo'),
    )
    op.create_index(op.f('ix_usuario_tenant_id'), 'usuario', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_usuario_deleted_at'), 'usuario', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_usuario_email_hash'), 'usuario', ['email_hash'], unique=False)

    # ---- asignacion ----------------------------------------------------------
    op.create_table('asignacion',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('usuario_id', sa.Uuid(), nullable=False),
        sa.Column('rol', sa.String(length=100), nullable=False),
        sa.Column('materia_id', sa.Uuid(), nullable=True),
        sa.Column('carrera_id', sa.Uuid(), nullable=True),
        sa.Column('cohorte_id', sa.Uuid(), nullable=True),
        sa.Column('comisiones', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('responsable_id', sa.Uuid(), nullable=True),
        sa.Column('desde', sa.Date(), nullable=False),
        sa.Column('hasta', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['usuario_id'], ['usuario.id'],
            ondelete='RESTRICT', name='fk_asignacion_usuario_id_usuario',
        ),
        sa.ForeignKeyConstraint(
            ['materia_id'], ['materia.id'],
            ondelete='RESTRICT', name='fk_asignacion_materia_id_materia',
        ),
        sa.ForeignKeyConstraint(
            ['carrera_id'], ['carrera.id'],
            ondelete='RESTRICT', name='fk_asignacion_carrera_id_carrera',
        ),
        sa.ForeignKeyConstraint(
            ['cohorte_id'], ['cohorte.id'],
            ondelete='RESTRICT', name='fk_asignacion_cohorte_id_cohorte',
        ),
        sa.ForeignKeyConstraint(
            ['responsable_id'], ['usuario.id'],
            ondelete='SET NULL', name='fk_asignacion_responsable_id_usuario',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_asignacion_tenant_id'), 'asignacion', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_asignacion_deleted_at'), 'asignacion', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_asignacion_tenant_usuario'), 'asignacion', ['tenant_id', 'usuario_id'], unique=False)
    op.create_index(op.f('ix_asignacion_tenant_materia'), 'asignacion', ['tenant_id', 'materia_id'], unique=False)
    op.create_index(op.f('ix_asignacion_tenant_vigencia'), 'asignacion', ['tenant_id', 'desde', 'hasta'], unique=False)

    # ---- Task 1.2: permissions already seeded in migration 003 --------------
    # Both `usuarios:gestionar` (b000000c-0000-0000-0000-00000000000c) and
    # `equipos:asignar` (b0000005-0000-0000-0000-000000000005) were already
    # created in migration 003 with their correct role assignments:
    #   - ADMIN → both permissions
    #   - COORDINADOR → equipos:asignar
    # No additional seed data is needed.


def downgrade() -> None:
    op.drop_index(op.f('ix_asignacion_tenant_vigencia'), table_name='asignacion')
    op.drop_index(op.f('ix_asignacion_tenant_materia'), table_name='asignacion')
    op.drop_index(op.f('ix_asignacion_tenant_usuario'), table_name='asignacion')
    op.drop_index(op.f('ix_asignacion_deleted_at'), table_name='asignacion')
    op.drop_index(op.f('ix_asignacion_tenant_id'), table_name='asignacion')
    op.drop_table('asignacion')

    op.drop_index(op.f('ix_usuario_email_hash'), table_name='usuario')
    op.drop_index(op.f('ix_usuario_deleted_at'), table_name='usuario')
    op.drop_index(op.f('ix_usuario_tenant_id'), table_name='usuario')
    op.drop_table('usuario')

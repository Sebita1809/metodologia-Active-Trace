"""005_carrera_cohorte_materia: create academic structure tables.

Revision ID: 005
Revises: 981efb7b4070
Create Date: 2026-06-18 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '981efb7b4070'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- carrera -------------------------------------------------------------
    op.create_table('carrera',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('codigo', sa.String(length=50), nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=False, server_default=sa.text("'Activa'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'codigo', name='uq_carrera_tenant_codigo'),
    )
    op.create_index(op.f('ix_carrera_tenant_id'), 'carrera', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_carrera_deleted_at'), 'carrera', ['deleted_at'], unique=False)

    # ---- cohorte -------------------------------------------------------------
    op.create_table('cohorte',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('carrera_id', sa.Uuid(), nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('anio', sa.Integer(), nullable=False),
        sa.Column('vig_desde', sa.Date(), nullable=False),
        sa.Column('vig_hasta', sa.Date(), nullable=True),
        sa.Column('estado', sa.String(length=20), nullable=False, server_default=sa.text("'Activa'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['carrera_id'], ['carrera.id'],
            ondelete='CASCADE', name='fk_cohorte_carrera_id_carrera',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'carrera_id', 'nombre', name='uq_cohorte_tenant_carrera_nombre'),
    )
    op.create_index(op.f('ix_cohorte_tenant_id'), 'cohorte', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_cohorte_carrera_id'), 'cohorte', ['carrera_id'], unique=False)
    op.create_index(op.f('ix_cohorte_deleted_at'), 'cohorte', ['deleted_at'], unique=False)

    # ---- materia -------------------------------------------------------------
    op.create_table('materia',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('codigo', sa.String(length=50), nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=False, server_default=sa.text("'Activa'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'codigo', name='uq_materia_tenant_codigo'),
    )
    op.create_index(op.f('ix_materia_tenant_id'), 'materia', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_materia_deleted_at'), 'materia', ['deleted_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_materia_deleted_at'), table_name='materia')
    op.drop_index(op.f('ix_materia_tenant_id'), table_name='materia')
    op.drop_table('materia')

    op.drop_index(op.f('ix_cohorte_deleted_at'), table_name='cohorte')
    op.drop_index(op.f('ix_cohorte_carrera_id'), table_name='cohorte')
    op.drop_index(op.f('ix_cohorte_tenant_id'), table_name='cohorte')
    op.drop_table('cohorte')

    op.drop_index(op.f('ix_carrera_deleted_at'), table_name='carrera')
    op.drop_index(op.f('ix_carrera_tenant_id'), table_name='carrera')
    op.drop_table('carrera')

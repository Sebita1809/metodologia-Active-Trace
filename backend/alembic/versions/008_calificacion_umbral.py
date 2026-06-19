"""008_calificacion_umbral: create calificacion + umbral_materia tables.

Revision ID: 008
Revises: 007
Create Date: 2026-06-19 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- umbral_materia ------------------------------------------------------
    # Table does not exist in DB yet (model exists in code but was never migrated)
    op.create_table('umbral_materia',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('asignacion_id', sa.Uuid(), nullable=False),
        sa.Column('materia_id', sa.Uuid(), nullable=False),
        sa.Column('umbral_pct', sa.Integer(), nullable=False, server_default=sa.text('60')),
        sa.Column('valores_aprobatorios', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asignacion_id'], ['asignacion.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['materia_id'], ['materia.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_umbral_materia_tenant_id'), 'umbral_materia', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_umbral_materia_deleted_at'), 'umbral_materia', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_umbral_materia_asignacion_id'), 'umbral_materia', ['asignacion_id'], unique=False)

    # ---- calificacion --------------------------------------------------------
    op.create_table('calificacion',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('entrada_padron_id', sa.Uuid(), nullable=False),
        sa.Column('materia_id', sa.Uuid(), nullable=False),
        sa.Column('actividad', sa.String(length=255), nullable=False),
        sa.Column('nota_numerica', sa.Numeric(5, 2), nullable=True),
        sa.Column('nota_textual', sa.String(length=100), nullable=True),
        sa.Column('origen', sa.Enum('Importado', 'Manual', name='origencalificacion'), nullable=False),
        sa.Column('importado_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entrada_padron_id'], ['entrada_padron.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['materia_id'], ['materia.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_calificacion_tenant_id'), 'calificacion', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_calificacion_deleted_at'), 'calificacion', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_calificacion_entrada_padron_id'), 'calificacion', ['entrada_padron_id'], unique=False)
    op.create_index(op.f('ix_calificacion_materia_id'), 'calificacion', ['materia_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_calificacion_materia_id'), table_name='calificacion')
    op.drop_index(op.f('ix_calificacion_entrada_padron_id'), table_name='calificacion')
    op.drop_index(op.f('ix_calificacion_deleted_at'), table_name='calificacion')
    op.drop_index(op.f('ix_calificacion_tenant_id'), table_name='calificacion')
    op.drop_table('calificacion')
    op.execute(sa.text("DROP TYPE IF EXISTS origencalificacion"))

    op.drop_index(op.f('ix_umbral_materia_asignacion_id'), table_name='umbral_materia')
    op.drop_index(op.f('ix_umbral_materia_deleted_at'), table_name='umbral_materia')
    op.drop_index(op.f('ix_umbral_materia_tenant_id'), table_name='umbral_materia')
    op.drop_table('umbral_materia')

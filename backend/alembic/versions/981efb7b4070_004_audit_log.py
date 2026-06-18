"""004_audit_log

Revision ID: 981efb7b4070
Revises: 003
Create Date: 2026-06-18 15:37:28.866191
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '981efb7b4070'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('audit_log',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('fecha_hora', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('actor_id', sa.Uuid(), nullable=False),
        sa.Column('impersonado_id', sa.Uuid(), nullable=True),
        sa.Column('materia_id', sa.Uuid(), nullable=True),
        sa.Column('accion', sa.String(length=50), nullable=False),
        sa.Column('detalle', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('filas_afectadas', sa.Integer(), nullable=True),
        sa.Column('ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_log_tenant_id'), 'audit_log', ['tenant_id'], unique=False)
    op.create_index('ix_audit_log_tenant_fecha', 'audit_log', ['tenant_id', 'created_at'], unique=False)
    op.create_index('ix_audit_log_actor', 'audit_log', ['actor_id'], unique=False)
    op.create_index('ix_audit_log_accion', 'audit_log', ['accion'], unique=False)
    op.create_index(op.f('ix_audit_log_deleted_at'), 'audit_log', ['deleted_at'], unique=False)

    # Append-only enforcement trigger (separate statements for asyncpg compat)
    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION reject_audit_modify()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only: modifications and deletions are prohibited';
        END;
        $$ LANGUAGE plpgsql
    """))
    op.execute(sa.text("""
        CREATE TRIGGER trg_audit_log_append_only
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW
            EXECUTE FUNCTION reject_audit_modify()
    """))


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_audit_log_append_only ON audit_log"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS reject_audit_modify"))

    op.drop_index(op.f('ix_audit_log_deleted_at'), table_name='audit_log')
    op.drop_index('ix_audit_log_accion', table_name='audit_log')
    op.drop_index('ix_audit_log_actor', table_name='audit_log')
    op.drop_index('ix_audit_log_tenant_fecha', table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_tenant_id'), table_name='audit_log')
    op.drop_table('audit_log')

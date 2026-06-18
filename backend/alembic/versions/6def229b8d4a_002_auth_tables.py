"""002_auth_tables

Revision ID: 6def229b8d4a
Revises: 001
Create Date: 2026-06-18 11:47:37.525988
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6def229b8d4a'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('auth_user',
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('totp_secret', sa.Text(), nullable=True),
    sa.Column('totp_enabled', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'email', name='uq_auth_user_tenant_email')
    )
    op.create_index(op.f('ix_auth_user_deleted_at'), 'auth_user', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_auth_user_email'), 'auth_user', ['email'], unique=False)
    op.create_index(op.f('ix_auth_user_tenant_id'), 'auth_user', ['tenant_id'], unique=False)

    op.create_table('password_recovery_token',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=255), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['auth_user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_password_recovery_token_deleted_at'), 'password_recovery_token', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_password_recovery_token_tenant_id'), 'password_recovery_token', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_password_recovery_token_token_hash'), 'password_recovery_token', ['token_hash'], unique=False)
    op.create_index(op.f('ix_password_recovery_token_user_id'), 'password_recovery_token', ['user_id'], unique=False)

    op.create_table('refresh_token',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=255), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('replaced_by', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['replaced_by'], ['refresh_token.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['auth_user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_refresh_token_deleted_at'), 'refresh_token', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_refresh_token_tenant_id'), 'refresh_token', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_refresh_token_token_hash'), 'refresh_token', ['token_hash'], unique=False)
    op.create_index(op.f('ix_refresh_token_user_id'), 'refresh_token', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_refresh_token_user_id'), table_name='refresh_token')
    op.drop_index(op.f('ix_refresh_token_token_hash'), table_name='refresh_token')
    op.drop_index(op.f('ix_refresh_token_tenant_id'), table_name='refresh_token')
    op.drop_index(op.f('ix_refresh_token_deleted_at'), table_name='refresh_token')
    op.drop_table('refresh_token')

    op.drop_index(op.f('ix_password_recovery_token_user_id'), table_name='password_recovery_token')
    op.drop_index(op.f('ix_password_recovery_token_token_hash'), table_name='password_recovery_token')
    op.drop_index(op.f('ix_password_recovery_token_tenant_id'), table_name='password_recovery_token')
    op.drop_index(op.f('ix_password_recovery_token_deleted_at'), table_name='password_recovery_token')
    op.drop_table('password_recovery_token')

    op.drop_index(op.f('ix_auth_user_tenant_id'), table_name='auth_user')
    op.drop_index(op.f('ix_auth_user_email'), table_name='auth_user')
    op.drop_index(op.f('ix_auth_user_deleted_at'), table_name='auth_user')
    op.drop_table('auth_user')

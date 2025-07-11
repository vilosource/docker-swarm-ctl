"""Add wizard framework and setup_pending status

Revision ID: wizard_framework_001
Revises: 9c4d3dece253
Create Date: 2025-07-10 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'wizard_framework_001'
down_revision = '9c4d3dece253'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create wizard_instances table
    op.create_table('wizard_instances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('wizard_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('current_step', sa.Integer(), nullable=True, default=0),
        sa.Column('total_steps', sa.Integer(), nullable=False),
        sa.Column('state', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, default='in_progress'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index('idx_wizard_instances_user_id', 'wizard_instances', ['user_id'])
    op.create_index('idx_wizard_instances_resource', 'wizard_instances', ['resource_id', 'resource_type'])
    op.create_index('idx_wizard_instances_status', 'wizard_instances', ['status'])
    
    # Add setup_pending to host_status enum
    # Note: PostgreSQL doesn't support ALTER TYPE directly in all versions
    # So we need to be careful with enum updates
    op.execute("ALTER TYPE host_status ADD VALUE IF NOT EXISTS 'setup_pending' AFTER 'pending'")


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_wizard_instances_status', table_name='wizard_instances')
    op.drop_index('idx_wizard_instances_resource', table_name='wizard_instances')
    op.drop_index('idx_wizard_instances_user_id', table_name='wizard_instances')
    
    # Drop wizard_instances table
    op.drop_table('wizard_instances')
    
    # Note: Removing enum values in PostgreSQL is complex and usually not done
    # Instead, we'd typically just stop using the value in the application
    # For a complete downgrade, you'd need to:
    # 1. Update all rows using 'setup_pending' to another status
    # 2. Create a new enum without 'setup_pending'
    # 3. Alter the column to use the new enum
    # 4. Drop the old enum
    pass
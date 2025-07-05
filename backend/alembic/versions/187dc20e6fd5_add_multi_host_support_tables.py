"""Add multi-host support tables

Revision ID: 187dc20e6fd5
Revises: 
Create Date: 2025-07-05 15:28:25.461589

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '187dc20e6fd5'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create docker_hosts table
    op.create_table(
        'docker_hosts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('host_type', sa.String(50), nullable=False),
        sa.Column('connection_type', sa.String(50), nullable=False),
        sa.Column('host_url', sa.String(500), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_default', sa.Boolean(), nullable=True, default=False),
        sa.Column('swarm_id', sa.String(255), nullable=True),
        sa.Column('cluster_name', sa.String(255), nullable=True),
        sa.Column('is_leader', sa.Boolean(), nullable=True, default=False),
        sa.Column('status', sa.String(50), nullable=True, default='pending'),
        sa.Column('last_health_check', sa.DateTime(), nullable=True),
        sa.Column('docker_version', sa.String(50), nullable=True),
        sa.Column('api_version', sa.String(50), nullable=True),
        sa.Column('os_type', sa.String(50), nullable=True),
        sa.Column('architecture', sa.String(50), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    )
    
    # Create indexes for docker_hosts
    op.create_index('idx_hosts_status', 'docker_hosts', ['status', 'is_active'])
    op.create_index('idx_hosts_swarm', 'docker_hosts', ['swarm_id', 'host_type'])
    
    # Create host_credentials table
    op.create_table(
        'host_credentials',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('host_id', sa.UUID(), nullable=False),
        sa.Column('credential_type', sa.String(50), nullable=False),
        sa.Column('encrypted_value', sa.Text(), nullable=False),
        sa.Column('credential_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['host_id'], ['docker_hosts.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('host_id', 'credential_type')
    )
    
    # Create user_host_permissions table
    op.create_table(
        'user_host_permissions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('host_id', sa.UUID(), nullable=False),
        sa.Column('permission_level', sa.String(50), nullable=False),
        sa.Column('granted_by', sa.UUID(), nullable=True),
        sa.Column('granted_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['host_id'], ['docker_hosts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ),
        sa.UniqueConstraint('user_id', 'host_id')
    )
    
    # Create index for user_host_permissions
    op.create_index('idx_user_hosts', 'user_host_permissions', ['user_id', 'permission_level'])
    
    # Create host_tags table
    op.create_table(
        'host_tags',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('host_id', sa.UUID(), nullable=False),
        sa.Column('tag_name', sa.String(100), nullable=False),
        sa.Column('tag_value', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['host_id'], ['docker_hosts.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('host_id', 'tag_name')
    )
    
    # Create index for host_tags
    op.create_index('idx_tags_name', 'host_tags', ['tag_name', 'tag_value'])
    
    # Create host_connection_stats table
    op.create_table(
        'host_connection_stats',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('host_id', sa.UUID(), nullable=False),
        sa.Column('active_connections', sa.Integer(), nullable=True, default=0),
        sa.Column('total_connections', sa.BigInteger(), nullable=True, default=0),
        sa.Column('failed_connections', sa.BigInteger(), nullable=True, default=0),
        sa.Column('avg_response_time_ms', sa.Float(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_error_at', sa.DateTime(), nullable=True),
        sa.Column('measured_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['host_id'], ['docker_hosts.id'], ondelete='CASCADE'),
    )
    
    # Create index for host_connection_stats
    op.create_index('idx_stats_host_time', 'host_connection_stats', ['host_id', 'measured_at'])
    
    # Add host_id to audit_logs table
    op.add_column('audit_logs', sa.Column('host_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_audit_logs_host_id', 'audit_logs', 'docker_hosts', ['host_id'], ['id'])


def downgrade() -> None:
    # Remove host_id from audit_logs
    op.drop_constraint('fk_audit_logs_host_id', 'audit_logs', type_='foreignkey')
    op.drop_column('audit_logs', 'host_id')
    
    # Drop tables in reverse order
    op.drop_index('idx_stats_host_time', table_name='host_connection_stats')
    op.drop_table('host_connection_stats')
    
    op.drop_index('idx_tags_name', table_name='host_tags')
    op.drop_table('host_tags')
    
    op.drop_index('idx_user_hosts', table_name='user_host_permissions')
    op.drop_table('user_host_permissions')
    
    op.drop_table('host_credentials')
    
    op.drop_index('idx_hosts_swarm', table_name='docker_hosts')
    op.drop_index('idx_hosts_status', table_name='docker_hosts')
    op.drop_table('docker_hosts')
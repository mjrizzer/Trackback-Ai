"""Session revocation and Supabase Data API isolation.

Revision ID: 0002
"""

from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

TABLES = (
    'organizations',
    'users',
    'suppliers',
    'material_lots',
    'production_batches',
    'batch_material_usage',
    'inspections',
    'shipments',
    'shipment_items',
    'customers',
    'incidents',
    'investigations',
    'evidence_documents',
    'evidence_findings',
    'agent_runs',
    'agent_tool_calls',
    'investigation_events',
    'action_proposals',
    'approvals',
    'audit_logs',
)


def upgrade():
    op.add_column(
        'users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column(
        'action_proposals',
        sa.Column('revision_history', sa.JSON(), nullable=False, server_default='[]'),
    )
    op.add_column(
        'investigations', sa.Column('attempt', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column(
        'agent_runs', sa.Column('attempt', sa.Integer(), nullable=False, server_default='1')
    )
    op.execute('UPDATE investigations SET attempt = 1')
    if op.get_bind().dialect.name == 'postgresql':
        # No permissive policy: browser/Data API roles cannot read these backend-owned tables.
        # Backend uses its private Postgres connection, never a browser service-role key.
        for table in TABLES:
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        for role in ('anon', 'authenticated'):
            for table in TABLES:
                op.execute(
                    f'DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = \'{role}\') THEN REVOKE ALL ON TABLE "{table}" FROM {role}; END IF; END $$'
                )


def downgrade():
    op.drop_column('agent_runs', 'attempt')
    op.drop_column('investigations', 'attempt')
    op.drop_column('action_proposals', 'revision_history')
    op.drop_column('users', 'token_version')
    # Deliberately preserve RLS and revoked grants: rollback must not expose data.

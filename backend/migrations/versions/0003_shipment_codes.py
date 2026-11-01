"""Prevent duplicate shipment codes without rebuilding populated SQLite tables."""

from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('uq_shipments_org_code', 'shipments', ['org_id', 'code'], unique=True)


def downgrade():
    op.drop_index('uq_shipments_org_code', table_name='shipments')

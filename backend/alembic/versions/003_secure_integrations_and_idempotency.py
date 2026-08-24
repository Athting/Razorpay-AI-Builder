"""Secure integrations and idempotent provider events.

Revision ID: 003_secure_integrations
Revises: 002_multi_tenant_foundation
"""
from alembic import op
import sqlalchemy as sa

revision = "003_secure_integrations"
down_revision = "002_multi_tenant_foundation"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("organizations", sa.Column("razorpay_oauth_config", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    op.add_column("payment_events", sa.Column("provider_event_id", sa.String(120), nullable=True))
    op.add_column("payment_events", sa.Column("provider_payment_id", sa.String(120), nullable=True))
    op.create_index("ix_payment_events_provider_payment_id", "payment_events", ["provider_payment_id"])
    # A partial unique index allows multiple legacy/no-ID events while making
    # incoming provider event IDs idempotent.
    op.execute("CREATE UNIQUE INDEX uq_payment_event_provider_event ON payment_events(organization_id, provider_event_id) WHERE provider_event_id IS NOT NULL")

def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_payment_event_provider_event")
    op.drop_index("ix_payment_events_provider_payment_id", table_name="payment_events")
    op.drop_column("payment_events", "provider_payment_id")
    op.drop_column("payment_events", "provider_event_id")
    op.drop_column("organizations", "razorpay_oauth_config")

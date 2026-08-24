"""Workspace OAuth credentials and idempotent provider event fields.

Revision ID: 004_workspace_events
Revises: 003_secure_integrations
"""
from alembic import op
import sqlalchemy as sa

revision = "004_workspace_events"
down_revision = "003_secure_integrations"
branch_labels = None
depends_on = None

def upgrade():
    # Kept defensive because a prior interrupted local migration may have made
    # part of this schema already. Fresh deployments receive it from 003.
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS razorpay_oauth_config JSON NOT NULL DEFAULT '{}'::json")
    op.execute("ALTER TABLE payment_events ADD COLUMN IF NOT EXISTS provider_event_id VARCHAR(120)")
    op.execute("ALTER TABLE payment_events ADD COLUMN IF NOT EXISTS provider_payment_id VARCHAR(120)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_payment_events_provider_payment_id ON payment_events(provider_payment_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_payment_event_provider_event ON payment_events(organization_id, provider_event_id) WHERE provider_event_id IS NOT NULL")

def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_payment_event_provider_event")
    op.execute("DROP INDEX IF EXISTS ix_payment_events_provider_payment_id")
    op.drop_column("payment_events", "provider_payment_id")
    op.drop_column("payment_events", "provider_event_id")
    op.drop_column("organizations", "razorpay_oauth_config")

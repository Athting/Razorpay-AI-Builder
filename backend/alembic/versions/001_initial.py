"""Initial schema — all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-08-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # customers
    op.create_table(
        'customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True, unique=True),
        sa.Column('segment', sa.Enum('consumer', 'smb', 'enterprise', name='customersegment'), nullable=False, server_default='consumer'),
        sa.Column('risk_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('dnd_opt_out', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('channel_opts', postgresql.JSON(), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False, server_default=''),
        sa.Column('hashed_password', sa.String(255), nullable=True),
        sa.Column('photo_url', sa.String(1000), nullable=True),
        sa.Column('role', sa.Enum('admin', 'agent', 'viewer', name='userrole'), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
    )

    # payment_events
    op.create_table(
        'payment_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('source', sa.String(50), nullable=False, server_default='mock'),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('decline_code', sa.String(20), nullable=True),
        sa.Column('gateway_message', sa.String(500), nullable=True),
        sa.Column('raw_payload_json', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # cases
    op.create_table(
        'cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('payment_event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('payment_events.id'), nullable=True),
        sa.Column('type', sa.Enum('subscription_failure', 'invoice_overdue', 'checkout_abandoned', name='casetype'), nullable=False),
        sa.Column('status', sa.Enum('open', 'in_progress', 'recovered', 'escalated', 'written_off', 'human_pending', name='casestatus'), nullable=False, server_default='open'),
        sa.Column('amount_at_risk', sa.Integer(), nullable=False),
        sa.Column('opened_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('recovered_amount', sa.Integer(), nullable=False, server_default='0'),
    )

    # diagnoses
    op.create_table(
        'diagnoses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('root_cause', sa.String(100), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('model_version', sa.String(50), nullable=False),
        sa.Column('reasoning_text', sa.String(2000), nullable=False, server_default=''),
        sa.Column('suggested_channel', sa.String(20), nullable=False, server_default='email'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # interventions
    op.create_table(
        'interventions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('action_type', sa.Enum('retry_payment', 'send_reminder', 'send_offer', 'escalate_to_human', 'write_off', 'generate_payment_link', name='actiontype'), nullable=False),
        sa.Column('channel', sa.Enum('whatsapp', 'sms', 'email', 'voice', 'system', name='channel'), nullable=False),
        sa.Column('payload', postgresql.JSON(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('result', sa.Enum('pending', 'sent', 'delivered', 'failed', 'responded', name='interventionresult'), nullable=False, server_default='pending'),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('approved_by_human', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('expected_recovery_prob', sa.Float(), nullable=True),
        sa.Column('reasoning', sa.String(2000), nullable=True),
    )

    # outcomes
    op.create_table(
        'outcomes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('intervention_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interventions.id'), nullable=True),
        sa.Column('outcome', sa.Enum('paid', 'promised', 'ignored', 'disputed', 'opted_out', name='outcometype'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('promised_date', sa.Date(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
    )

    # audit_log
    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id'), nullable=True),
        sa.Column('actor', sa.Enum('system', 'model', 'human', name='auditactor'), nullable=False),
        sa.Column('action', sa.String(200), nullable=False),
        sa.Column('reasoning', sa.String(4000), nullable=False, server_default=''),
        sa.Column('policy_version', sa.String(20), nullable=False, server_default='v1.0'),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('prev_hash', sa.String(64), nullable=False),
        sa.Column('hash', sa.String(64), nullable=False),
    )

    # stopping_rules
    op.create_table(
        'stopping_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('cooldown_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('quiet_hours_start', sa.Integer(), nullable=False, server_default='21'),
        sa.Column('quiet_hours_end', sa.Integer(), nullable=False, server_default='9'),
        sa.Column('applies_to', sa.Enum('subscription_failure', 'invoice_overdue', 'checkout_abandoned', 'all', name='ruleappliesto'), nullable=False, server_default='all'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Indexes for query performance
    op.create_index('ix_cases_customer_id', 'cases', ['customer_id'])
    op.create_index('ix_cases_status', 'cases', ['status'])
    op.create_index('ix_diagnoses_case_id', 'diagnoses', ['case_id'])
    op.create_index('ix_interventions_case_id', 'interventions', ['case_id'])
    op.create_index('ix_audit_log_case_id', 'audit_log', ['case_id'])
    op.create_index('ix_audit_log_timestamp', 'audit_log', ['timestamp'])


def downgrade() -> None:
    op.drop_table('stopping_rules')
    op.drop_table('audit_log')
    op.drop_table('outcomes')
    op.drop_table('interventions')
    op.drop_table('diagnoses')
    op.drop_table('cases')
    op.drop_table('payment_events')
    op.drop_table('users')
    op.drop_table('customers')
    # Drop enums
    for enum_name in ['customersegment', 'userrole', 'casetype', 'casestatus',
                      'actiontype', 'channel', 'interventionresult', 'outcometype',
                      'auditactor', 'ruleappliesto']:
        op.execute(f'DROP TYPE IF EXISTS {enum_name}')

"""Schedule transactional outbox and delivery receipts.
Revision ID: 0006_schedule_observers
Revises: 0005_scheduling
"""
from alembic import op
import sqlalchemy as sa
revision = "0006_schedule_observers"
down_revision = "0005_scheduling"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("schedule_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(36), nullable=False, unique=True),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("schedule_delivery_receipt",
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))

def downgrade():
    op.drop_table("schedule_delivery_receipt")
    op.drop_table("schedule_outbox")

"""Add KRS state machine, optimistic versioning, audit log and notifications.

Revision ID: 0004_krs_state_machine
Revises: 0003_krs_module
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_krs_state_machine"
down_revision = "0003_krs_module"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("krs", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("krs", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("krs", sa.Column("revision_note", sa.Text(), nullable=True))
    op.add_column("krs", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                                    server_default=sa.text("CURRENT_TIMESTAMP")))
    op.add_column("krs", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    op.create_table(
        "krs_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("krs_id", sa.Integer(), sa.ForeignKey("krs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_role", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.String(30), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=False),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_krs_log_krs_id", "krs_log", ["krs_id"])

    op.create_table(
        "krs_notification",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("krs_id", sa.Integer(), sa.ForeignKey("krs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_nim", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_krs_notification_krs_id", "krs_notification", ["krs_id"])


def downgrade():
    op.drop_index("ix_krs_notification_krs_id", table_name="krs_notification")
    op.drop_table("krs_notification")
    op.drop_index("ix_krs_log_krs_id", table_name="krs_log")
    op.drop_table("krs_log")
    op.drop_column("krs", "version")
    op.drop_column("krs", "updated_at")
    op.drop_column("krs", "revision_note")
    op.drop_column("krs", "approved_at")
    op.drop_column("krs", "submitted_at")

"""Add counter table for safe NIM generation.

Revision ID: 0002_nim_counter
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_nim_counter"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nim_counter",
        sa.Column("tahun", sa.Integer(), nullable=False),
        sa.Column("kode_prodi", sa.String(length=3), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("tahun", "kode_prodi", name="pk_nim_counter"),
        sa.CheckConstraint("last_number >= 0 AND last_number <= 9999", name="ck_nim_counter_range"),
    )


def downgrade():
    op.drop_table("nim_counter")

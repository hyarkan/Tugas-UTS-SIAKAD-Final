"""Create PMB tables

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

status_enum = sa.Enum("pending", "approve", "rejected", name="status_pmb", create_constraint=True)

def upgrade():
    op.create_table(
        "program_studi",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kode", sa.String(length=3), nullable=False),
        sa.Column("nama", sa.String(length=100), nullable=False),
        sa.Column("fakultas", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("kode", name="uq_program_studi_kode"),
    )
    op.create_table(
        "jalur_masuk",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nama", sa.String(length=50), nullable=False),
        sa.UniqueConstraint("nama", name="uq_jalur_masuk_nama"),
    )
    op.create_table(
        "calon_mahasiswa",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nama_lengkap", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("phone", sa.String(length=15), nullable=False),
        sa.Column("tanggal_lahir", sa.Date(), nullable=False),
        sa.Column("alamat", sa.String(length=300), nullable=False),
        sa.Column("program_studi_id", sa.Integer(), sa.ForeignKey("program_studi.id"), nullable=False),
        sa.Column("jalur_masuk_id", sa.Integer(), sa.ForeignKey("jalur_masuk.id"), nullable=False),
        sa.Column("status", status_enum, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("approve_at", sa.DateTime(), nullable=True),
        sa.Column("nim", sa.String(length=20), nullable=True),
        sa.UniqueConstraint("nim", name="uq_calon_mahasiswa_nim"),
    )
    op.create_index("ix_calon_mahasiswa_email", "calon_mahasiswa", ["email"], unique=True)

def downgrade():
    op.drop_index("ix_calon_mahasiswa_email", table_name="calon_mahasiswa")
    op.drop_table("calon_mahasiswa")
    op.drop_table("jalur_masuk")
    op.drop_table("program_studi")

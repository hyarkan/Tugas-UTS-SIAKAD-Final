"""Add KRS module schema.

Revision ID: 0003_krs_module
Revises: 0002_nim_counter
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_krs_module"
down_revision = "0002_nim_counter"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "matakuliah",
        sa.Column("kode_mk", sa.String(20), nullable=False),
        sa.Column("nama", sa.String(150), nullable=False),
        sa.Column("sks", sa.Integer(), nullable=False),
        sa.Column("hari", sa.Integer(), nullable=False),
        sa.Column("jam_mulai", sa.Time(), nullable=False),
        sa.Column("jam_selesai", sa.Time(), nullable=False),
        sa.PrimaryKeyConstraint("kode_mk"),
        sa.CheckConstraint("sks >= 1 AND sks <= 4", name="ck_matakuliah_sks_range"),
        sa.CheckConstraint("hari >= 1 AND hari <= 6", name="ck_matakuliah_hari_range"),
        sa.CheckConstraint("jam_mulai < jam_selesai", name="ck_matakuliah_valid_time"),
    )
    op.create_table(
        "skala_nilai",
        sa.Column("nilai", sa.String(2), nullable=False),
        sa.Column("bobot", sa.Integer(), nullable=False),
        sa.Column("lulus", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("nilai"),
        sa.UniqueConstraint("bobot", name="uq_skala_nilai_bobot"),
        sa.CheckConstraint("bobot >= 0 AND bobot <= 4", name="ck_skala_nilai_bobot"),
    )
    op.create_table(
        "krs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nim", sa.String(20), nullable=False),
        sa.Column("semester", sa.String(5), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("dosen_pa_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["nim"], ["calon_mahasiswa.nim"], ondelete="RESTRICT"),
        sa.UniqueConstraint("nim", "semester", name="uq_krs_nim_semester"),
        sa.CheckConstraint("status IN ('draft','submitted','approved','revision')", name="ck_krs_status"),
    )
    op.create_table(
        "krs_detail",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("krs_id", sa.Integer(), nullable=False),
        sa.Column("kode_mk", sa.String(20), nullable=False),
        sa.Column("nilai", sa.String(2), nullable=True),
        sa.ForeignKeyConstraint(["krs_id"], ["krs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["kode_mk"], ["matakuliah.kode_mk"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["nilai"], ["skala_nilai.nilai"], ondelete="RESTRICT"),
        sa.UniqueConstraint("krs_id", "kode_mk", name="uq_krs_detail_krs_mk"),
    )
    op.create_table(
        "prerequisite",
        sa.Column("kode_mk", sa.String(20), nullable=False),
        sa.Column("kode_prasyarat", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(["kode_mk"], ["matakuliah.kode_mk"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["kode_prasyarat"], ["matakuliah.kode_mk"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("kode_mk", "kode_prasyarat"),
        sa.CheckConstraint("kode_mk <> kode_prasyarat", name="ck_prerequisite_not_self"),
    )


def downgrade():
    op.drop_table("prerequisite")
    op.drop_table("krs_detail")
    op.drop_table("krs")
    op.drop_table("skala_nilai")
    op.drop_table("matakuliah")

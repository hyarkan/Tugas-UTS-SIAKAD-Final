"""Add scheduling domain and optional KRS class link.
Revision ID: 0005_scheduling
Revises: 0004_krs_state_machine
"""
from alembic import op
import sqlalchemy as sa
revision = "0005_scheduling"
down_revision = "0004_krs_state_machine"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("ruangan", sa.Column("kode", sa.String(20), primary_key=True), sa.Column("kapasitas", sa.Integer(), nullable=False), sa.CheckConstraint("kapasitas > 0", name="ck_ruangan_kapasitas"))
    op.create_table("dosen", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("nidn", sa.String(20), nullable=False, unique=True), sa.Column("nama", sa.String(150), nullable=False))
    op.create_table("kelas", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("kode_mk", sa.String(20), sa.ForeignKey("matakuliah.kode_mk", ondelete="RESTRICT"), nullable=False), sa.Column("nama", sa.String(30), nullable=False), sa.Column("kuota", sa.Integer(), nullable=False), sa.Column("semester", sa.String(5), nullable=False), sa.CheckConstraint("kuota > 0", name="ck_kelas_kuota"), sa.UniqueConstraint("kode_mk", "nama", "semester", name="uq_kelas_parallel"))
    op.create_table("jadwal", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("kelas_id", sa.Integer(), sa.ForeignKey("kelas.id", ondelete="RESTRICT"), nullable=False), sa.Column("hari", sa.Integer(), nullable=False), sa.Column("jam_mulai", sa.Time(), nullable=False), sa.Column("jam_selesai", sa.Time(), nullable=False), sa.Column("ruangan_kode", sa.String(20), sa.ForeignKey("ruangan.kode", ondelete="RESTRICT"), nullable=False), sa.Column("dosen_id", sa.Integer(), sa.ForeignKey("dosen.id", ondelete="RESTRICT"), nullable=False), sa.CheckConstraint("hari BETWEEN 1 AND 6", name="ck_jadwal_hari"), sa.CheckConstraint("jam_mulai < jam_selesai", name="ck_jadwal_jam"))
    op.create_index("ix_jadwal_hari_ruangan", "jadwal", ["hari", "ruangan_kode"])
    op.create_index("ix_jadwal_hari_dosen", "jadwal", ["hari", "dosen_id"])
    with op.batch_alter_table("krs_detail") as batch:
        batch.add_column(sa.Column("kelas_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_krs_detail_kelas", "kelas", ["kelas_id"], ["id"], ondelete="RESTRICT")
    # Kolom legacy matakuliah.hari/jam tetap ada untuk kompatibilitas Minggu 5-6.

def downgrade():
    with op.batch_alter_table("krs_detail") as batch:
        batch.drop_constraint("fk_krs_detail_kelas", type_="foreignkey")
        batch.drop_column("kelas_id")
    op.drop_index("ix_jadwal_hari_dosen", table_name="jadwal")
    op.drop_index("ix_jadwal_hari_ruangan", table_name="jadwal")
    op.drop_table("jadwal")
    op.drop_table("kelas")
    op.drop_table("dosen")
    op.drop_table("ruangan")

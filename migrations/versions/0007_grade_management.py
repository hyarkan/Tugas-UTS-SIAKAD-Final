"""Week 9: Decimal scale, explicit passing, and atomic grade history.
Revision ID: 0007_grade_management
Revises: 0006_schedule_observers
"""
from alembic import op
import sqlalchemy as sa
revision = "0007_grade_management"
down_revision = "0006_schedule_observers"
branch_labels = None
depends_on = None

def upgrade():
    # Week 8 already has the nullable FK and 'lulus' column.
    with op.batch_alter_table("skala_nilai") as batch:
        batch.alter_column("bobot", existing_type=sa.Integer(), type_=sa.Numeric(3, 2), existing_nullable=False)
    op.create_table("grade_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("grade_id", sa.Integer(), sa.ForeignKey("krs_detail.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("old_value", sa.String(2)),
        sa.Column("new_value", sa.String(2), sa.ForeignKey("skala_nilai.nilai"), nullable=False),
        sa.Column("changed_by", sa.Integer(), sa.ForeignKey("dosen.id"), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text()))
    op.create_index("ix_grade_history_grade_date", "grade_history", ["grade_id", "changed_at"])
    op.execute("""CREATE VIEW v_grade_history AS
        SELECT gh.id, gh.grade_id, k.nim, kd.kode_mk, gh.old_value,
               gh.new_value, gh.changed_by, d.nama AS dosen_nama,
               gh.changed_at, gh.reason
        FROM grade_history gh JOIN krs_detail kd ON kd.id = gh.grade_id
        JOIN krs k ON k.id = kd.krs_id JOIN dosen d ON d.id = gh.changed_by""")

def downgrade():
    op.execute("DROP VIEW IF EXISTS v_grade_history")
    op.drop_index("ix_grade_history_grade_date", table_name="grade_history")
    op.drop_table("grade_history")
    with op.batch_alter_table("skala_nilai") as batch:
        batch.alter_column("bobot", existing_type=sa.Numeric(3, 2), type_=sa.Integer(), existing_nullable=False)

"""Minggu 12 - presensi QR; Revision ID: 0010_attendance_qr; Revises: 0009_finance_spp."""
from alembic import op
import sqlalchemy as sa
revision='0010_attendance_qr'
down_revision='0009_finance_spp'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('attendance_session',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('schedule_id',sa.Integer(),sa.ForeignKey('jadwal.id',ondelete='RESTRICT'),nullable=False),sa.Column('session_date',sa.Date(),nullable=False),sa.Column('starts_at',sa.DateTime(),nullable=False),sa.Column('ends_at',sa.DateTime(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False),sa.UniqueConstraint('schedule_id','session_date',name='uq_attendance_session_day'))
    op.create_table('attendance_qr',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('session_id',sa.Integer(),sa.ForeignKey('attendance_session.id',ondelete='CASCADE'),nullable=False),sa.Column('jti',sa.String(64),nullable=False,unique=True),sa.Column('issued_at',sa.DateTime(),nullable=False),sa.Column('expires_at',sa.DateTime(),nullable=False))
    op.create_table('attendance_record',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('session_id',sa.Integer(),sa.ForeignKey('attendance_session.id',ondelete='CASCADE'),nullable=False),sa.Column('nim',sa.String(20),sa.ForeignKey('calon_mahasiswa.nim',ondelete='RESTRICT'),nullable=False),sa.Column('scanned_at',sa.DateTime(),nullable=False),sa.Column('status',sa.String(12),nullable=False),sa.UniqueConstraint('session_id','nim',name='uq_attendance_once'),sa.CheckConstraint("status IN ('hadir','terlambat')",name='ck_attendance_status'))
    op.create_index('ix_attendance_nim','attendance_record',['nim'])

def downgrade():
    op.drop_index('ix_attendance_nim',table_name='attendance_record')
    op.drop_table('attendance_record')
    op.drop_table('attendance_qr')
    op.drop_table('attendance_session')

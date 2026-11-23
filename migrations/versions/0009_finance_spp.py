"""Week 11 finance module.
Revision ID: 0009_finance_spp
Revises: 0008_grade_audit_trigger
"""
from alembic import op
import sqlalchemy as sa
revision='0009_finance_spp'
down_revision='0008_grade_audit_trigger'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('payment_method',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('code',sa.String(30),nullable=False,unique=True),sa.Column('name',sa.String(100),nullable=False))
    op.create_table('billing',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('nim',sa.String(20),sa.ForeignKey('calon_mahasiswa.nim'),nullable=False),sa.Column('semester',sa.String(5),nullable=False),sa.Column('total',sa.Numeric(15,2),nullable=False),sa.Column('paid_amount',sa.Numeric(15,2),server_default='0',nullable=False),sa.Column('penalty',sa.Numeric(15,2),server_default='0',nullable=False),sa.Column('status',sa.String(12),server_default='unpaid',nullable=False),sa.Column('due_date',sa.Date(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False),sa.UniqueConstraint('nim','semester',name='uq_billing_student_semester'),sa.CheckConstraint("status IN ('unpaid','partial','paid','overdue')",name='ck_billing_status'),sa.CheckConstraint('total >= 0 AND paid_amount >= 0 AND penalty >= 0',name='ck_billing_amount'))
    op.create_index('ix_billing_nim','billing',['nim']);op.create_index('ix_billing_semester','billing',['semester'])
    op.create_table('payment',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('billing_id',sa.Integer(),sa.ForeignKey('billing.id'),nullable=False),sa.Column('method_id',sa.Integer(),sa.ForeignKey('payment_method.id'),nullable=False),sa.Column('amount',sa.Numeric(15,2),nullable=False),sa.Column('transaction_id',sa.String(120),unique=True),sa.Column('source',sa.String(20),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False),sa.CheckConstraint('amount > 0',name='ck_payment_positive'))
    op.create_index('ix_payment_billing_id','payment',['billing_id'])
    op.create_table('finance_notification',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('billing_id',sa.Integer(),sa.ForeignKey('billing.id'),nullable=False),sa.Column('kind',sa.String(20),nullable=False),sa.Column('recipient',sa.String(254),nullable=False),sa.Column('subject',sa.String(150),nullable=False),sa.Column('body',sa.Text(),nullable=False),sa.Column('sent_at',sa.DateTime()),sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_finance_notification_billing_id','finance_notification',['billing_id'])

def downgrade():
    op.drop_index('ix_finance_notification_billing_id',table_name='finance_notification');op.drop_table('finance_notification')
    op.drop_index('ix_payment_billing_id',table_name='payment');op.drop_table('payment')
    op.drop_index('ix_billing_semester',table_name='billing');op.drop_index('ix_billing_nim',table_name='billing');op.drop_table('billing');op.drop_table('payment_method')

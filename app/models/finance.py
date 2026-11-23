from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, Numeric, UniqueConstraint, CheckConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class PaymentMethod(Base):
    __tablename__ = 'payment_method'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

class Billing(Base):
    __tablename__ = 'billing'
    __table_args__ = (UniqueConstraint('nim','semester',name='uq_billing_student_semester'), CheckConstraint("status IN ('unpaid','partial','paid','overdue')",name='ck_billing_status'), CheckConstraint('total >= 0 AND paid_amount >= 0 AND penalty >= 0',name='ck_billing_amount'))
    id: Mapped[int] = mapped_column(primary_key=True)
    nim: Mapped[str] = mapped_column(String(20), ForeignKey('calon_mahasiswa.nim'),nullable=False,index=True)
    semester: Mapped[str] = mapped_column(String(5),nullable=False,index=True)
    total: Mapped[Decimal] = mapped_column(Numeric(15,2),nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(15,2),nullable=False,default=Decimal('0'),server_default='0')
    penalty: Mapped[Decimal] = mapped_column(Numeric(15,2),nullable=False,default=Decimal('0'),server_default='0')
    status: Mapped[str] = mapped_column(String(12),nullable=False,default='unpaid',server_default='unpaid')
    due_date: Mapped[date] = mapped_column(Date,nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime,default=lambda:datetime.now(timezone.utc),nullable=False)

class Payment(Base):
    __tablename__ = 'payment'
    __table_args__ = (CheckConstraint('amount > 0',name='ck_payment_positive'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    billing_id: Mapped[int] = mapped_column(ForeignKey('billing.id'),nullable=False,index=True)
    method_id: Mapped[int] = mapped_column(ForeignKey('payment_method.id'),nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15,2),nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(String(120),unique=True,nullable=True)
    source: Mapped[str] = mapped_column(String(20),nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime,default=lambda:datetime.now(timezone.utc),nullable=False)

class FinanceNotification(Base):
    __tablename__ = 'finance_notification'
    id: Mapped[int] = mapped_column(primary_key=True)
    billing_id: Mapped[int] = mapped_column(ForeignKey('billing.id'),nullable=False,index=True)
    kind: Mapped[str] = mapped_column(String(20),nullable=False)
    recipient: Mapped[str] = mapped_column(String(254),nullable=False)
    subject: Mapped[str] = mapped_column(String(150),nullable=False)
    body: Mapped[str] = mapped_column(Text,nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime,nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime,default=lambda:datetime.now(timezone.utc),nullable=False)

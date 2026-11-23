"""Append-only grade change history; same transaction as KRSDetail.nilai."""
from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class GradeHistory(Base):
    __tablename__ = "grade_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    grade_id: Mapped[int] = mapped_column(ForeignKey("krs_detail.id", ondelete="RESTRICT"), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(2), nullable=True)
    new_value: Mapped[str] = mapped_column(String(2), ForeignKey("skala_nilai.nilai"), nullable=False)
    changed_by: Mapped[int] = mapped_column(ForeignKey("dosen.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (Index("ix_grade_history_grade_date", "grade_id", "changed_at"),)

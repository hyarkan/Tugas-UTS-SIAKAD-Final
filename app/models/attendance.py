"""Presensi per pertemuan (Minggu 12)."""
from datetime import datetime, date
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class AttendanceSession(Base):
    __tablename__ = "attendance_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("jadwal.id", ondelete="RESTRICT"), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    __table_args__ = (UniqueConstraint("schedule_id", "session_date", name="uq_attendance_session_day"),)

class AttendanceQR(Base):
    __tablename__ = "attendance_qr"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("attendance_session.id", ondelete="CASCADE"), nullable=False)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

class AttendanceRecord(Base):
    __tablename__ = "attendance_record"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("attendance_session.id", ondelete="CASCADE"), nullable=False)
    nim: Mapped[str] = mapped_column(String(20), ForeignKey("calon_mahasiswa.nim", ondelete="RESTRICT"), nullable=False)
    scanned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    __table_args__ = (UniqueConstraint("session_id", "nim", name="uq_attendance_once"), CheckConstraint("status IN ('hadir','terlambat')", name="ck_attendance_status"), Index("ix_attendance_nim", "nim"))

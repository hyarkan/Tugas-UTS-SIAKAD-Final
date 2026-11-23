import enum
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class StatusPMB(str, enum.Enum):
    pending = "pending"
    approve = "approve"
    rejected = "rejected"

class CalonMahasiswa(Base):
    __tablename__ = "calon_mahasiswa"

    id: Mapped[int] = mapped_column(primary_key=True)
    nama_lengkap: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(15), nullable=False)
    tanggal_lahir: Mapped[date] = mapped_column(Date, nullable=False)
    alamat: Mapped[str] = mapped_column(String(300), nullable=False)
    program_studi_id: Mapped[int] = mapped_column(ForeignKey("program_studi.id"), nullable=False)
    jalur_masuk_id: Mapped[int] = mapped_column(ForeignKey("jalur_masuk.id"), nullable=False)
    status: Mapped[StatusPMB] = mapped_column(
        Enum(StatusPMB, name="status_pmb", create_constraint=True),
        nullable=False,
        default=StatusPMB.pending,
        server_default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    approve_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    nim: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)

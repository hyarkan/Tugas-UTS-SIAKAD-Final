from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NIMCounter(Base):
    """Counter nomor urut NIM untuk setiap kombinasi tahun dan kode prodi."""

    __tablename__ = "nim_counter"
    __table_args__ = (
        CheckConstraint(
            "last_number >= 0 AND last_number <= 9999",
            name="ck_nim_counter_range",
        ),
    )

    tahun: Mapped[int] = mapped_column(Integer, primary_key=True)
    kode_prodi: Mapped[str] = mapped_column(String(3), primary_key=True)
    last_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

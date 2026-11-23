"""Domain penjadwalan Minggu 7."""
from datetime import time
from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class Ruangan(Base):
    __tablename__ = "ruangan"
    kode: Mapped[str] = mapped_column(String(20), primary_key=True)
    kapasitas: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (CheckConstraint("kapasitas > 0", name="ck_ruangan_kapasitas"),)

class Dosen(Base):
    __tablename__ = "dosen"
    id: Mapped[int] = mapped_column(primary_key=True)
    nidn: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nama: Mapped[str] = mapped_column(String(150), nullable=False)

class Kelas(Base):
    __tablename__ = "kelas"
    id: Mapped[int] = mapped_column(primary_key=True)
    kode_mk: Mapped[str] = mapped_column(String(20), ForeignKey("matakuliah.kode_mk", ondelete="RESTRICT"), nullable=False)
    nama: Mapped[str] = mapped_column(String(30), nullable=False)
    kuota: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[str] = mapped_column(String(5), nullable=False)
    jadwal: Mapped[list["Jadwal"]] = relationship(back_populates="kelas")
    __table_args__ = (CheckConstraint("kuota > 0", name="ck_kelas_kuota"), UniqueConstraint("kode_mk", "nama", "semester", name="uq_kelas_parallel"))

class Jadwal(Base):
    __tablename__ = "jadwal"
    id: Mapped[int] = mapped_column(primary_key=True)
    kelas_id: Mapped[int] = mapped_column(ForeignKey("kelas.id", ondelete="RESTRICT"), nullable=False)
    hari: Mapped[int] = mapped_column(Integer, nullable=False)
    jam_mulai: Mapped[time] = mapped_column(Time, nullable=False)
    jam_selesai: Mapped[time] = mapped_column(Time, nullable=False)
    ruangan_kode: Mapped[str] = mapped_column(String(20), ForeignKey("ruangan.kode", ondelete="RESTRICT"), nullable=False)
    dosen_id: Mapped[int] = mapped_column(ForeignKey("dosen.id", ondelete="RESTRICT"), nullable=False)
    kelas: Mapped[Kelas] = relationship(back_populates="jadwal")
    ruangan: Mapped[Ruangan] = relationship()
    dosen: Mapped[Dosen] = relationship()
    __table_args__ = (
        CheckConstraint("hari BETWEEN 1 AND 6", name="ck_jadwal_hari"),
        CheckConstraint("jam_mulai < jam_selesai", name="ck_jadwal_jam"),
        Index("ix_jadwal_hari_ruangan", "hari", "ruangan_kode"),
        Index("ix_jadwal_hari_dosen", "hari", "dosen_id"),
    )

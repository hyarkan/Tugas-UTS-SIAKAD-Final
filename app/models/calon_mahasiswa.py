# ==================================================
# MODEL PMB — ENTITAS CALON MAHASISWA
# ==================================================
# Enum dan tipe tanggal dipakai untuk memberi bentuk data status, tanggal lahir, dan waktu proses.
# SQLAlchemy menyediakan tipe kolom serta foreign key; Mapped dan mapped_column menghubungkan atribut Python ke kolom database.
# Base adalah declarative base bersama yang mengumpulkan metadata model untuk ORM dan migrasi.
import enum
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

# StatusPMB membatasi nilai status ke tiga keadaan yang digunakan proses PMB.
# Mewarisi str membuat nilai enum dapat berinteraksi dengan string, sedangkan enum.Enum menyediakan pilihan status terkontrol.
class StatusPMB(str, enum.Enum):
    pending = "pending"
    approve = "approve"
    rejected = "rejected"

# >>> FOKUS PRESENTASI UTS <<<
# CalonMahasiswa adalah model ORM untuk tabel pendaftar PMB.
# Class ini menjadi representasi kode dari entitas dan atribut inti pada Class Diagram.
class CalonMahasiswa(Base):
    __tablename__ = "calon_mahasiswa"

    # Primary key mengidentifikasi setiap pendaftar secara unik; SQLAlchemy menentukan tipe integer berdasarkan anotasinya.
    id: Mapped[int] = mapped_column(primary_key=True)
    # Nama pendaftar wajib diisi dan dibatasi panjangnya di database.
    nama_lengkap: Mapped[str] = mapped_column(String(150), nullable=False)
    # Email dibatasi panjangnya, wajib diisi, dibuat unik, dan diberi index untuk membantu pencarian.
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    # Nomor telepon disimpan sebagai teks agar awalan nol atau tanda plus tidak hilang.
    phone: Mapped[str] = mapped_column(String(15), nullable=False)
    # Tanggal lahir dipetakan sebagai tipe Date sehingga nilai tanggal tidak diperlakukan sebagai teks bebas.
    tanggal_lahir: Mapped[date] = mapped_column(Date, nullable=False)
    # Alamat dibatasi panjangnya dan wajib tersedia sesuai aturan kolom database.
    alamat: Mapped[str] = mapped_column(String(300), nullable=False)
    # Foreign key menghubungkan pendaftar ke program studi yang sudah terdaftar.
    # Hubungan ini merepresentasikan relasi satu ProgramStudi ke banyak CalonMahasiswa pada diagram.
    program_studi_id: Mapped[int] = mapped_column(ForeignKey("program_studi.id"), nullable=False)
    # Foreign key kedua menghubungkan pendaftar dengan jalur masuk dan menjaga integritas referensinya.
    jalur_masuk_id: Mapped[int] = mapped_column(ForeignKey("jalur_masuk.id"), nullable=False)
    # Kolom status menggunakan enum database agar nilai tersimpan mengikuti StatusPMB.
    # nullable=False mewajibkan status; default berlaku pada sisi ORM, sedangkan server_default menjadi nilai bawaan database.
    status: Mapped[StatusPMB] = mapped_column(
        Enum(StatusPMB, name="status_pmb", create_constraint=True),
        nullable=False,
        default=StatusPMB.pending,
        server_default="pending",
    )
    # Waktu pembuatan diisi oleh database saat record dibuat; approve_at baru diisi ketika proses persetujuan terjadi.
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    # Nilai None menandakan pendaftar belum disetujui dan karena itu belum memiliki waktu approval.
    approve_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # NIM belum tersedia sebelum approval; unique menjaga NIM yang sudah terbit agar tidak ganda.
    nim: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)

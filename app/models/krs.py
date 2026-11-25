# ==================================================
# MODEL KRS — STATUS, ENTITAS, DAN RELASI AKADEMIK
# ==================================================
# Decimal dipakai untuk bobot nilai; enum dan tipe waktu membentuk nilai domain pada model.
# SQLAlchemy menyediakan tipe kolom, constraint, tabel asosiasi, dan relationship ORM.
# Mapped serta mapped_column memetakan atribut bertipe Python ke kolom database.
# Base menjadi deklarasi metadata bersama seluruh model.
from decimal import Decimal
from decimal import Decimal
import enum
from datetime import datetime, time, timezone
from sqlalchemy import (CheckConstraint, ForeignKey, Integer, String, Numeric, Time,
                        UniqueConstraint, Table, Column, DateTime, Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


# >>> FOKUS PRESENTASI UTS <<<
# KRSStatus mendefinisikan empat status yang dipakai dalam alur pengajuan dan persetujuan KRS.
class KRSStatus(str, enum.Enum):
    # draft berarti KRS masih dapat disusun oleh mahasiswa.
    draft = "draft"
    # submitted menandakan KRS telah diajukan untuk diperiksa.
    submitted = "submitted"
    # approved menandakan KRS telah disetujui dosen PA.
    approved = "approved"
    # revision menandakan KRS dikembalikan untuk diperbaiki.
    revision = "revision"


# Tabel asosiasi ini merepresentasikan relasi many-to-many antara mata kuliah dan mata kuliah prasyarat.
# Kedua kolomnya menunjuk ke tabel matakuliah; satu baris berarti satu pasangan mata kuliah-prasyarat.
prerequisite = Table(
    "prerequisite", Base.metadata,
    # Kolom pertama adalah mata kuliah yang memiliki prasyarat; CASCADE menghapus pasangan asosiasi saat mata kuliah terkait dihapus.
    Column("kode_mk", String(20), ForeignKey("matakuliah.kode_mk", ondelete="CASCADE"), primary_key=True),
    # Kolom kedua menunjuk mata kuliah yang menjadi prasyarat; bersama kolom pertama membentuk composite primary key.
    Column("kode_prasyarat", String(20), ForeignKey("matakuliah.kode_mk", ondelete="CASCADE"), primary_key=True),
    # Constraint ini mencegah mata kuliah menjadi prasyarat bagi dirinya sendiri.
    CheckConstraint("kode_mk <> kode_prasyarat", name="ck_prerequisite_not_self"),
)


# >>> FOKUS PRESENTASI UTS <<<
# MataKuliah menyimpan katalog mata kuliah beserta SKS dan informasi jadwal yang dipakai validator KRS.
class MataKuliah(Base):
    __tablename__ = "matakuliah"
    # Constraint database menjaga rentang SKS, nomor hari, dan urutan jam meskipun data tidak masuk melalui API.
    __table_args__ = (
        # SKS per mata kuliah dibatasi antara satu sampai empat.
        CheckConstraint("sks >= 1 AND sks <= 4", name="ck_matakuliah_sks_range"),
        # Hari menggunakan rentang Senin sampai Sabtu sesuai keterangan pada field hari.
        CheckConstraint("hari >= 1 AND hari <= 6", name="ck_matakuliah_hari_range"),
        # Waktu mulai harus lebih awal daripada waktu selesai.
        CheckConstraint("jam_mulai < jam_selesai", name="ck_matakuliah_valid_time"),
    )
    # kode_mk menjadi identitas utama katalog mata kuliah.
    kode_mk: Mapped[str] = mapped_column(String(20), primary_key=True)
    # Nama mata kuliah wajib tersedia dan dibatasi panjangnya.
    nama: Mapped[str] = mapped_column(String(150), nullable=False)
    # Nilai SKS digunakan dalam perhitungan beban studi dan validasi batas maksimal KRS.
    sks: Mapped[int] = mapped_column(Integer, nullable=False)
    # Hari disimpan sebagai angka; metadata kolom menjelaskan rentang Senin sampai Sabtu.
    hari: Mapped[int] = mapped_column(Integer, nullable=False, comment="1=Senin sampai 6=Sabtu")
    # Jam mulai dan selesai menyediakan interval untuk pemeriksaan bentrok jadwal.
    jam_mulai: Mapped[time] = mapped_column(Time, nullable=False)
    jam_selesai: Mapped[time] = mapped_column(Time, nullable=False)
    # Relasi self-referential many-to-many menghubungkan sebuah mata kuliah ke daftar prasyaratnya.
    # primaryjoin dan secondaryjoin membedakan sisi mata kuliah tujuan dan sisi mata kuliah prasyarat pada tabel asosiasi.
    prasyarat: Mapped[list["MataKuliah"]] = relationship(
        "MataKuliah", secondary=prerequisite,
        primaryjoin=kode_mk == prerequisite.c.kode_mk,
        secondaryjoin=kode_mk == prerequisite.c.kode_prasyarat,
        # Backref menyediakan arah relasi sebaliknya: mata kuliah yang membutuhkan mata kuliah ini sebagai prasyarat.
        backref="dibutuhkan_oleh",
    )


# >>> FOKUS PRESENTASI UTS <<<
# KRS mewakili satu rencana studi seorang mahasiswa pada satu semester.
class KRS(Base):
    __tablename__ = "krs"
    # Constraint unik mencegah dua KRS untuk mahasiswa dan semester yang sama; check constraint membatasi status tersimpan.
    __table_args__ = (
        # Pasangan NIM-semester menjadi aturan keunikan satu KRS per mahasiswa per semester.
        UniqueConstraint("nim", "semester", name="uq_krs_nim_semester"),
        # Status di database dibatasi pada empat nilai yang dikenali sistem.
        CheckConstraint("status IN ('draft','submitted','approved','revision')", name="ck_krs_status"),
    )
    # Primary key mengidentifikasi record KRS.
    id: Mapped[int] = mapped_column(primary_key=True)
    # NIM menjadi foreign key ke identitas mahasiswa yang diterbitkan melalui PMB; RESTRICT menjaga referensi tetap ada.
    nim: Mapped[str] = mapped_column(String(20), ForeignKey("calon_mahasiswa.nim", ondelete="RESTRICT"), nullable=False)
    # Semester disimpan dalam format yang dijelaskan oleh metadata kolom: YYYY1 atau YYYY2.
    semester: Mapped[str] = mapped_column(String(5), nullable=False, comment="YYYY1=ganjil, YYYY2=genap")
    # Status disimpan sebagai String dengan nilai awal draft; pilihan nilainya juga dibatasi oleh constraint di atas.
    # Field ini bukan kolom SQLAlchemy Enum, meskipun nilainya mengikuti KRSStatus.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=KRSStatus.draft.value, server_default="draft")
    # ID dosen PA boleh kosong; pada model ini field tersebut Integer biasa tanpa foreign key ke tabel dosen.
    dosen_pa_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Waktu submit dan approval opsional karena baru terisi ketika tahap alur tersebut terjadi.
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Catatan revisi menyimpan arahan teks untuk mahasiswa saat KRS dikembalikan.
    revision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Waktu pembaruan menggunakan zona waktu UTC dan membantu merekam perubahan terakhir.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    # Kolom version dipakai SQLAlchemy untuk mendeteksi perubahan bersamaan yang memakai versi lama.
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    # Satu KRS memiliki banyak detail; cascade dan delete-orphan menghapus detail ORM saat detail dilepas atau induknya dihapus.
    details: Mapped[list["KRSDetail"]] = relationship(back_populates="krs", cascade="all, delete-orphan")

    # Konfigurasi ini menetapkan version sebagai kolom optimistic versioning untuk objek KRS.
    __mapper_args__ = {"version_id_col": version}

    # Tabel ini menentukan transisi status yang sah berdasarkan status asal dan peran aktor.
    ALLOWED_TRANSITIONS = {
        # Mahasiswa dapat mengajukan KRS dari draft menjadi submitted.
        (KRSStatus.draft.value, "mahasiswa"): {KRSStatus.submitted.value},
        # Dosen PA dapat menyetujui atau meminta revisi dari status submitted.
        (KRSStatus.submitted.value, "dosen_pa"): {KRSStatus.approved.value, KRSStatus.revision.value},
        # Setelah revisi, mahasiswa dapat mengajukan kembali KRS.
        (KRSStatus.revision.value, "mahasiswa"): {KRSStatus.submitted.value},
        # Sistem juga dapat mengembalikan KRS submitted menjadi revision pada alur perubahan jadwal.
        (KRSStatus.submitted.value, "sistem"): {KRSStatus.revision.value},
        # KRS approved juga dapat direvisi oleh sistem pada alur perubahan jadwal yang terdampak.
        (KRSStatus.approved.value, "sistem"): {KRSStatus.revision.value},
    }

    # Memeriksa pasangan status-aktor sebelum status diubah.
    def check_transition(self, target: str, actor_role: str) -> None:
        # Import lokal menghindari kebutuhan mengambil exception service saat modul model pertama kali dimuat.
        from app.services.krs_service import KRSForbidden, TransitionError
        # Pencarian pertama memeriksa apakah target diizinkan untuk status dan peran aktor yang tepat.
        allowed = self.ALLOWED_TRANSITIONS.get((self.status, actor_role), set())
        # Jika target termasuk transisi yang diizinkan, tidak ada error yang perlu dilempar.
        if target in allowed:
            return
        # Kumpulan ini membantu membedakan transisi yang sah bagi peran lain dari transisi yang tidak dikenal sama sekali.
        allowed_for_any_actor = set().union(*(
            targets for (source, _role), targets in self.ALLOWED_TRANSITIONS.items()
            if source == self.status
        )) if any(source == self.status for source, _role in self.ALLOWED_TRANSITIONS) else set()
        # Target yang sah bagi peran lain tetapi bukan aktor ini ditolak sebagai masalah otorisasi.
        if target in allowed_for_any_actor:
            raise KRSForbidden("Peran Anda tidak berwenang melakukan transisi status KRS ini.")
        # Jika target tidak sah bagi status asal mana pun, sistem melaporkan transisi yang tidak valid.
        raise TransitionError(f"Transisi status KRS tidak diizinkan: {self.status} → {target}.")

    # Method ini menerapkan transisi hanya setelah aturan status dan peran lolos pemeriksaan.
    def transition(self, target: str, actor_role: str) -> None:
        # Validasi dipanggil kembali agar perubahan status tidak melewati aturan transisi.
        self.check_transition(target, actor_role)
        # Status baru ditetapkan setelah pemeriksaan berhasil.
        self.status = target
        # Waktu pembaruan disegarkan setiap kali transisi dilakukan.
        self.updated_at = datetime.now(timezone.utc)


# KRSDetail merepresentasikan satu mata kuliah yang tercatat dalam sebuah KRS.
class KRSDetail(Base):
    __tablename__ = "krs_detail"
    # Constraint ini mencegah mata kuliah yang sama dimasukkan dua kali ke satu KRS.
    __table_args__ = (UniqueConstraint("krs_id", "kode_mk", name="uq_krs_detail_krs_mk"),)
    # Primary key mengidentifikasi setiap detail pengambilan mata kuliah.
    id: Mapped[int] = mapped_column(primary_key=True)
    # Foreign key menghubungkan detail ke KRS induk; CASCADE mengikuti penghapusan KRS.
    krs_id: Mapped[int] = mapped_column(ForeignKey("krs.id", ondelete="CASCADE"), nullable=False)
    # Foreign key menunjuk ke katalog MataKuliah dan RESTRICT mencegah penghapusan mata kuliah yang sedang dipakai.
    kode_mk: Mapped[str] = mapped_column(String(20), ForeignKey("matakuliah.kode_mk", ondelete="RESTRICT"), nullable=False)
    # Kelas bersifat opsional dan merujuk ke model Kelas pada modul penjadwalan.
    kelas_id: Mapped[int | None] = mapped_column(ForeignKey("kelas.id", ondelete="RESTRICT"), nullable=True)
    # Nilai opsional merujuk ke SkalaNilai agar nilai yang dicatat mengikuti katalog nilai.
    nilai: Mapped[str | None] = mapped_column(String(2), ForeignKey("skala_nilai.nilai", ondelete="RESTRICT"), nullable=True)
    # Relasi balik menghubungkan detail ke objek KRS melalui atribut details.
    krs: Mapped[KRS] = relationship(back_populates="details")
    # Relasi ORM ini menyediakan akses dari detail ke objek MataKuliah terkait.
    mata_kuliah: Mapped[MataKuliah] = relationship()


# SkalaNilai menyimpan kode nilai beserta bobot dan indikator kelulusannya.
class SkalaNilai(Base):
    __tablename__ = "skala_nilai"
    # Kode nilai menjadi primary key yang dirujuk oleh KRSDetail.nilai.
    nilai: Mapped[str] = mapped_column(String(2), primary_key=True)
    # Bobot numerik disimpan dengan presisi desimal dan harus unik.
    bobot: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False, unique=True)
    # lulus menandai apakah nilai memenuhi syarat kelulusan prasyarat.
    lulus: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="0")
    # Check constraint menjaga bobot nilai tetap berada pada rentang 0 sampai 4.
    __table_args__ = (CheckConstraint("bobot >= 0 AND bobot <= 4", name="ck_skala_nilai_bobot"),)


# KRSLog menyimpan jejak tindakan dan perubahan status KRS.
class KRSLog(Base):
    __tablename__ = "krs_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Foreign key menghubungkan log dengan KRS; index membantu pencarian riwayat berdasarkan KRS.
    krs_id: Mapped[int] = mapped_column(ForeignKey("krs.id", ondelete="CASCADE"), nullable=False, index=True)
    # Role dan ID aktor mencatat siapa yang melakukan tindakan.
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(30), nullable=False)
    # Action dan pasangan status asal/tujuan menjelaskan perubahan yang dicatat.
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    from_status: Mapped[str] = mapped_column(String(20), nullable=False)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    # Note dapat menyimpan keterangan tambahan, misalnya alasan revisi.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Waktu UTC mencatat kapan entri riwayat dibuat.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


# KRSNotification menyimpan pesan untuk penerima terkait KRS.
class KRSNotification(Base):
    __tablename__ = "krs_notification"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Foreign key mengaitkan notifikasi dengan KRS dan index mendukung pencarian berdasarkan induknya.
    krs_id: Mapped[int] = mapped_column(ForeignKey("krs.id", ondelete="CASCADE"), nullable=False, index=True)
    # NIM menentukan mahasiswa penerima notifikasi.
    recipient_nim: Mapped[str] = mapped_column(String(20), nullable=False)
    # Isi pesan disimpan sebagai teks.
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # Notifikasi baru secara default belum dibaca.
    is_read: Mapped[bool] = mapped_column(default=False, server_default="0", nullable=False)
    # Waktu UTC mencatat kapan notifikasi dibuat.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

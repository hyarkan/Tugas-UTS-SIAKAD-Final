# ==================================================
# VALIDATOR KRS - CHAIN OF RESPONSIBILITY
# ==================================================
# dataclass membangkitkan constructor untuk objek data; ABC dan abstractmethod mendefinisikan kontrak validator.
from dataclasses import dataclass
from abc import ABC, abstractmethod
# select dan exists menyusun query validasi, sedangkan Session menjadi sesi ORM yang menjalankan query.
from sqlalchemy import select, exists, and_
from sqlalchemy.orm import Session
# Model dan tabel asosiasi ini menyediakan data KRS, katalog mata kuliah, nilai, serta relasi prasyarat.
from app.models import KRS, KRSDetail, MataKuliah, SkalaNilai, prerequisite

# Batas maksimum SKS untuk satu KRS mengikuti aturan akademik yang dipakai validator.
MAX_SKS = 24


# ValidationResult dibuat immutable agar hasil pemeriksaan tidak berubah setelah validator mengembalikannya.
@dataclass(frozen=True)
# Objek hasil ini menyatukan indikator lulus/gagal dengan pesan yang dapat diteruskan ke API.
class ValidationResult:
    # oke menandakan aturan terpenuhi; False berarti proses validasi perlu dihentikan atau dicatat sebagai error.
    oke: bool
    # Pesan bersifat opsional untuk hasil yang berhasil dan menjelaskan alasan ketika validasi gagal.
    message: str = ""


# KRSContext adalah dataclass yang membawa seluruh data yang dibutuhkan validator tanpa banyak parameter terpisah.
@dataclass
# Konteks ini mutable karena merupakan wadah data proses, bukan hasil validasi yang perlu dibekukan.
class KRSContext:
    # NIM dan semester mengidentifikasi pemilik serta periode akademik yang sedang diperiksa.
    nim: str
    semester: str
    # Daftar ini berisi mata kuliah yang sudah ada dan menjadi pembanding untuk aturan tambah mata kuliah.
    existing_courses: list[MataKuliah]
    # Mata kuliah baru adalah item yang sedang diminta untuk dimasukkan ke KRS.
    new_course: MataKuliah
    # Session dipakai validator prasyarat untuk memeriksa riwayat nilai pada database.
    session: Session
    # ID KRS opsional sebagai konteks tambahan ketika KRS sudah terbentuk.
    krs_id: int | None = None


# >>> FOKUS PRESENTASI UTS <<<
# Validator adalah abstract base class yang menetapkan kontrak bersama untuk setiap pemeriksaan KRS.
class Validator(ABC):
    # Constructor menyiapkan tautan ke validator berikutnya; None berarti rantai belum diteruskan.
    def __init__(self):
        # Atribut ini menyimpan penerus dalam Chain of Responsibility.
        self.next_validator: Validator | None = None

    # set_next menghubungkan validator saat chain dirakit dan mengembalikan penerus agar pemanggilan dapat dirangkai.
    def set_next(self, validator: "Validator") -> "Validator":
        self.next_validator = validator
        return validator

    # validate menjalankan pemeriksaan saat ini lalu meneruskan konteks ke validator selanjutnya bila perlu.
    def validate(self, context: KRSContext) -> ValidationResult:
        # Pemanggilan self.check bersifat polymorphic: implementasi subclass yang dijalankan.
        result = self.check(context)
        # Fail-fast berlaku jika aturan gagal atau ini validator terakhir; hasil pertama itu langsung dikembalikan.
        if not result.oke or self.next_validator is None:
            return result
        # Jika pemeriksaan lolos dan ada penerus, validasi berlanjut secara rekursif ke node berikutnya.
        return self.next_validator.validate(context)

    # abstractmethod mewajibkan subclass menyediakan aturan check sendiri dan mencegah base class dipakai sebagai validator konkret.
    @abstractmethod
    # Setiap implementasi check menerima konteks yang sama dan mengembalikan ValidationResult.
    def check(self, context: KRSContext) -> ValidationResult:
        # Jika kontrak tidak diturunkan dengan implementasi konkret, pemanggilan ini menandai method sebagai belum tersedia.
        raise NotImplementedError


# >>> FOKUS PRESENTASI UTS <<<
# DuplicateValidator memiliki satu tanggung jawab: menolak mata kuliah yang kodenya sudah ada di KRS.
class DuplicateValidator(Validator):
    # Override check mengisi kontrak abstrak dari Validator untuk aturan duplikasi.
    def check(self, context):
        # any berhenti ketika menemukan kode yang sama; pemeriksaan ini memakai konteks tanpa query database tambahan.
        if any(course.kode_mk == context.new_course.kode_mk for course in context.existing_courses):
            # Hasil gagal membawa nama mata kuliah agar pesan dapat menjelaskan duplikasi kepada pengguna.
            return ValidationResult(False, f"Mata kuliah {context.new_course.nama} sudah ada di KRS.")
        # Jika tidak ditemukan kecocokan, validator mengembalikan hasil sukses untuk diteruskan ke validator berikutnya.
        return ValidationResult(True)


# >>> FOKUS PRESENTASI UTS <<<
# SKSValidator memeriksa total beban setelah mata kuliah baru ditambahkan.
class SKSValidator(Validator):
    # check menghitung SKS seluruh mata kuliah yang sudah dipilih ditambah mata kuliah baru.
    def check(self, context):
        # Sum mengakumulasi SKS existing_courses, lalu menambahkan SKS mata kuliah yang sedang diuji.
        total = sum(course.sks for course in context.existing_courses) + context.new_course.sks
        # Total yang tepat 24 masih diizinkan; hanya nilai yang lebih besar yang ditolak.
        if total > MAX_SKS:
            # Pesan menyertakan total aktual dan batas maksimum agar mudah dipahami mahasiswa.
            return ValidationResult(False, f"Total SKS {total} melebihi batas maksimal {MAX_SKS} SKS.")
        # Bila beban masih dalam batas, chain boleh melanjutkan pemeriksaan.
        return ValidationResult(True)


# >>> FOKUS PRESENTASI UTS <<<
# PrerequisiteValidator mendelegasikan pencarian prasyarat yang belum lulus ke query database.
class PrerequisiteValidator(Validator):
    # check menyerahkan session dan identitas periode/mahasiswa ke helper query.
    def check(self, context):
        # Helper mengembalikan daftar prasyarat yang belum terbukti lulus pada semester sebelumnya.
        missing = get_unfulfilled_prerequisites(
            context.session, context.nim, context.semester, context.new_course.kode_mk
        )
        # Daftar yang tidak kosong berarti ada aturan prasyarat yang belum terpenuhi.
        if missing:
            # Semua nama yang belum terpenuhi dirangkai menjadi satu pesan kegagalan.
            return ValidationResult(False, "Prasyarat tidak terpenuhi: " + ", ".join(missing) + ".")
        # Tanpa prasyarat yang tertinggal, hasil pemeriksaan dinyatakan berhasil.
        return ValidationResult(True)


# >>> FOKUS PRESENTASI UTS <<<
# ConflictValidator membandingkan jadwal mata kuliah baru dengan setiap mata kuliah dalam KRS.
class ConflictValidator(Validator):
    # Pemeriksaan dilakukan satu per satu terhadap jadwal yang sudah dipilih.
    def check(self, context):
        # Dua jadwal hanya dapat bertabrakan jika berada pada hari yang sama dan interval waktunya tumpang tindih.
        for current in context.existing_courses:
            overlaps = (
                # Syarat pertama memastikan hari perkuliahan sama.
                current.hari == context.new_course.hari
                # Syarat kedua mengecek waktu mulai jadwal lama sebelum waktu selesai jadwal baru.
                and current.jam_mulai < context.new_course.jam_selesai
                # Syarat ketiga mengecek waktu mulai jadwal baru sebelum waktu selesai jadwal lama.
                # Perbandingan ketat ini membolehkan dua jadwal yang hanya bersinggungan tepat di batas waktu.
                and context.new_course.jam_mulai < current.jam_selesai
            )
            # Saat menemukan bentrok pertama, validator langsung mengembalikan hasil gagal.
            if overlaps:
                # Hasil menyertakan nama kedua mata kuliah yang jadwalnya bertabrakan.
                return ValidationResult(
                    False,
                    f"Jadwal bentrok antara {context.new_course.nama} dan {current.nama}.",
                )
        # Jika seluruh jadwal selesai diperiksa tanpa tumpang tindih, hasilnya sukses.
        return ValidationResult(True)


# build_chain merangkai validator dalam urutan Duplicate, SKS, Prerequisite, lalu Conflict.
def build_chain() -> Validator:
    # Docstring asli dipertahankan: urutan ini mendahulukan pemeriksaan murah sebelum query atau perbandingan lain.
    """Urutan dipilih: duplicate (murah), SKS, prasyarat, lalu konflik."""
    # Duplicate menjadi kepala rantai dan pemeriksaan pertama.
    duplicate = DuplicateValidator()
    # set_next menghubungkan node berurutan; return penerus memungkinkan rangkaian chain dalam satu ekspresi.
    duplicate.set_next(SKSValidator()).set_next(PrerequisiteValidator()).set_next(ConflictValidator())
    # Kepala rantai dikembalikan untuk dipakai KRSManager saat proses tambah mata kuliah.
    return duplicate


# Helper ini menyusun query untuk menemukan prasyarat yang belum terbukti lulus pada semester sebelumnya.
def get_unfulfilled_prerequisites(session: Session, nim: str, semester: str, kode_mk: str) -> list[str]:
    # Docstring asli menyebut penggunaan NOT EXISTS untuk mencari prasyarat yang belum lulus.
    """NOT EXISTS: daftar prasyarat yang belum terbukti lulus pada semester sebelumnya."""
    # Subquery EXISTS menguji keberadaan riwayat nilai lulus bagi setiap kode prasyarat yang ditautkan oleh query luar.
    passed_grade = exists(
        # Query hanya perlu membuktikan ada setidaknya satu baris yang cocok.
        select(1)
        # Riwayat yang diperiksa berasal dari detail KRS.
        .select_from(KRSDetail)
        # Join menghubungkan detail nilai dengan KRS pemiliknya.
        .join(KRS, KRS.id == KRSDetail.krs_id)
        # Join berikutnya mengambil bobot dan indikator kelulusan dari SkalaNilai.
        .join(SkalaNilai, SkalaNilai.nilai == KRSDetail.nilai)
        # Semua syarat harus cocok: mahasiswa sama, semester sebelumnya, mata kuliah yang merupakan prasyarat, lulus, dan bobot minimal dua.
        .where(
            # NIM membatasi pemeriksaan pada mahasiswa yang sedang mengisi KRS.
            KRS.nim == nim,
            # Format semester YYYY1/YYYY2 dibandingkan untuk memastikan riwayat terjadi sebelum semester berjalan.
            KRS.semester < semester,
            # Kode prasyarat diambil dari sisi prerequisite pada tabel asosiasi.
            KRSDetail.kode_mk == prerequisite.c.kode_prasyarat,
            # Indikator lulus harus bernilai True.
            SkalaNilai.lulus.is_(True),
            # Bobot minimal 2 menjadi syarat tambahan sesuai aturan kelulusan pada query ini.
            SkalaNilai.bobot >= 2,
        )
    )
    # Query luar memilih nama mata kuliah prasyarat untuk kode mata kuliah yang sedang divalidasi.
    stmt = (
        # Nama dipilih agar hasil kegagalan dapat ditampilkan sebagai pesan yang mudah dibaca.
        select(MataKuliah.nama)
        # Tabel asosiasi menjadi sumber daftar prasyarat.
        .select_from(prerequisite)
        # Join mengambil nama untuk setiap kode prasyarat.
        .join(MataKuliah, MataKuliah.kode_mk == prerequisite.c.kode_prasyarat)
        # Filter memilih hanya pasangan prasyarat milik mata kuliah yang diminta.
        .where(prerequisite.c.kode_mk == kode_mk)
        # NOT EXISTS menyisakan prasyarat yang tidak memiliki bukti kelulusan yang cocok.
        .where(~passed_grade)
        # Pengurutan membuat daftar hasil konsisten berdasarkan nama mata kuliah.
        .order_by(MataKuliah.nama)
    )
    # Hasil scalar query diubah menjadi list[str] untuk dipakai PrerequisiteValidator.
    return list(session.scalars(stmt).all())

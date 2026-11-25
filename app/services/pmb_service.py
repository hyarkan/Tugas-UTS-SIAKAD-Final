# ==================================================
# SERVICE PMB — ATURAN BISNIS DAN AKSES DATA
# ==================================================
# datetime dan timezone membantu menyimpan waktu approval; re dipakai pada pembuatan NIM yang dibahas di kelompok berikutnya.
from datetime import datetime, timezone
import re

# SQLAlchemy select/func menyusun query, sedangkan exception ORM membantu menangani kegagalan constraint/transaksi.
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
# Session adalah unit kerja ORM yang digunakan service untuk membaca dan menyimpan data.
from sqlalchemy.orm import Session

# Model PMB, referensi, dan counter dipakai service; NIMCounter serta exception NIM digunakan pada bagian yang dibahas berikutnya.
from app.models import (
    CalonMahasiswa, JalurMasuk, NIMCounter, ProgramStudi, StatusPMB
)
# RegisterRequest memastikan payload yang diterima service sesuai kontrak validasi registrasi.
from app.schemas.register import RegisterRequest


# Exception khusus membedakan kegagalan bisnis agar router dapat mengubahnya menjadi respons HTTP yang tepat.
class EmailAlreadyRegistered(Exception):
    pass


class InvalidReference(Exception):
    pass


class CandidateNotFound(Exception):
    pass


class InvalidNIMData(Exception):
    pass


class CandidateStateConflict(Exception):
    pass


class NIMSequenceExhausted(Exception):
    pass


# >>> FOKUS PRESENTASI UTS <<<
# Fungsi ini menjalankan registrasi di lapisan service: memeriksa aturan bisnis, membentuk objek ORM, lalu menyimpannya.
def register_candidate(db: Session, payload: RegisterRequest) -> CalonMahasiswa:
    # Query hanya mengambil ID yang cocok, sehingga service cukup mengetahui apakah email tersebut sudah ada.
    if db.scalar(select(CalonMahasiswa.id).where(CalonMahasiswa.email == str(payload.email))):
        # Pemeriksaan awal memberi error bisnis yang spesifik; unique constraint model tetap menjadi perlindungan database.
        raise EmailAlreadyRegistered

    # ID program studi harus merujuk ke record yang benar-benar tersedia, bukan sekadar bernilai positif.
    if db.get(ProgramStudi, payload.program_studi_id) is None:
        # Tanpa referensi program studi yang valid, proses registrasi dihentikan sebelum objek disimpan.
        raise InvalidReference("Program studi tidak ditemukan.")
    # Jalur masuk diperiksa terpisah karena merupakan referensi database lain yang wajib valid.
    if db.get(JalurMasuk, payload.jalur_masuk_id) is None:
        # Kegagalan referensi ini diteruskan ke router untuk dipetakan sebagai HTTP 400.
        raise InvalidReference("Jalur masuk tidak ditemukan.")

    # Objek ORM dibangun dari field request yang telah lolos validasi schema dan pemeriksaan referensi.
    candidate = CalonMahasiswa(
        nama_lengkap=payload.nama_lengkap,
        email=str(payload.email),
        phone=payload.phone,
        tanggal_lahir=payload.tanggal_lahir,
        alamat=payload.alamat,
        program_studi_id=payload.program_studi_id,
        jalur_masuk_id=payload.jalur_masuk_id,
        # Status awal pending menandakan pendaftar belum disetujui dan belum mendapat NIM.
        status=StatusPMB.pending,
    )
    # add menandai objek untuk disimpan pada transaksi session; perubahan belum permanen sebelum commit.
    db.add(candidate)
    # Blok transaksi menangani kegagalan constraint yang dapat terjadi saat database menyimpan data.
    try:
        # commit meminta database menyimpan perubahan registrasi secara permanen.
        db.commit()
        # refresh membaca ulang record agar nilai yang dibuat database, seperti ID dan created_at, tersedia pada objek.
        db.refresh(candidate)
    # Jika constraint database menolak data, transaksi dibatalkan sebelum error diterjemahkan.
    except IntegrityError as exc:
        # rollback membatalkan perubahan transaksi yang gagal agar session dapat digunakan kembali dengan konsisten.
        db.rollback()
        # Service membedakan benturan email/unique dari pelanggaran referensi berdasarkan detail error database.
        if "email" in str(exc).lower() or "unique" in str(exc).lower():
            # Benturan unique email di database menjadi exception bisnis yang sama dengan pemeriksaan awal.
            raise EmailAlreadyRegistered from exc
        # IntegrityError lain dipetakan ke kegagalan referensi dan tetap menyertakan penyebab aslinya.
        raise InvalidReference("Referensi data tidak valid.") from exc
    # Objek yang sudah tersimpan dikembalikan ke router untuk membentuk response API.
    return candidate


# ==================================================
# SERVICE PMB — PEMBUATAN NIM
# ==================================================
# >>> FOKUS PRESENTASI UTS <<<
# Fungsi ini menaikkan counter yang sesuai dan membentuk NIM.
# Fungsi tidak melakukan commit sendiri; transaksinya dikendalikan pemanggil.
def generate_nim(db: Session, candidate: CalonMahasiswa, tahun: int) -> str:
    """Naikkan counter dalam transaksi milik pemanggil; fungsi ini tidak commit."""
    # Program studi pendaftar menentukan kode yang menjadi bagian NIM dan kunci counter.
    program = db.get(ProgramStudi, candidate.program_studi_id)
    # Referensi program studi yang tidak ditemukan membuat pembuatan NIM tidak dapat dilanjutkan.
    if program is None:
        raise InvalidNIMData("Program studi tidak ditemukan.")
    # Kode prodi harus tepat tiga digit agar sesuai format NIM YYYYKKKNNNN.
    if not re.fullmatch(r"\d{3}", program.kode or ""):
        raise InvalidNIMData("Kode program studi harus terdiri dari tepat 3 digit angka.")

    # Counter dicari berdasarkan tahun dan kode prodi.
    # with_for_update meminta row lock pada database yang mendukungnya;
    # implementasi backend menentukan perilaku penguncian sebenarnya.
    stmt = (
        select(NIMCounter)
        .where(
            NIMCounter.tahun == tahun,
            NIMCounter.kode_prodi == program.kode,
        )
        .with_for_update()
    )
    counter = db.scalar(stmt)
    # Jika pasangan tahun-prodi belum memiliki counter, buat mulai dari nol.
    if counter is None:
        counter = NIMCounter(tahun=tahun, kode_prodi=program.kode, last_number=0)
        db.add(counter)
        # flush mengirim perubahan ke database di dalam transaksi yang sama,
        # tanpa melakukan commit.
        db.flush()

    # Nomor baru adalah nomor terakhir ditambah satu.
    next_number = counter.last_number + 1
    # Maksimal 9999 karena segmen urut NIM memiliki empat digit.
    if next_number > 9999:
        raise NIMSequenceExhausted("Nomor urut NIM untuk tahun dan program studi ini sudah mencapai 9999.")

    # Counter diperbarui dalam transaksi yang sama dengan approval.
    counter.last_number = next_number
    db.flush()
    # Format hasil: tahun empat digit + kode prodi tiga digit + urutan empat digit.
    return f"{tahun:04d}{program.kode}{next_number:04d}"


# ==================================================
# SERVICE PMB — APPROVAL DAN TRANSAKSI
# ==================================================
# >>> FOKUS PRESENTASI UTS <<<
# Fungsi ini mengatur approval sebagai satu alur transaksi:
# memeriksa pendaftar dan status, menerbitkan NIM, lalu menyimpan hasilnya.
def approve_candidate(db: Session, candidate_id: int) -> CalonMahasiswa:
    # SQLite tidak mendukung SELECT FOR UPDATE. BEGIN IMMEDIATE mengambil
    # write reservation sebelum pembacaan sehingga approve bersamaan terserialisasi.
    # Pemilihan mekanisme awal transaksi bergantung pada dialect database.
    if db.get_bind().dialect.name == "sqlite":
        # SQLite tidak mendukung SELECT FOR UPDATE. BEGIN IMMEDIATE mengambil
        # write reservation sebelum pembacaan sehingga approve bersamaan terserialisasi.
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")

    # Cari pendaftar berdasarkan ID. SELECT FOR UPDATE meminta penguncian baris
    # pada database yang mendukungnya; SQLite memakai mekanisme BEGIN IMMEDIATE di atas.
    candidate = db.scalar(
        select(CalonMahasiswa)
        .where(CalonMahasiswa.id == candidate_id)
        .with_for_update()
    )
    # Jika pendaftar tidak ada, transaksi dibatalkan sebelum error bisnis dilempar.
    if candidate is None:
        db.rollback()
        raise CandidateNotFound("Pendaftar tidak ditemukan.")

    # >>> FOKUS PRESENTASI UTS <<<
    if candidate.status == StatusPMB.approve:
        # Idempotent: kembalikan NIM yang sudah ada tanpa menyentuh counter.
        # Commit di jalur ini mengakhiri transaksi pembacaan sebelum objek dikembalikan.
        db.commit()
        return candidate

    # Pendaftar yang telah ditolak tidak boleh melewati alur approval.
    if candidate.status == StatusPMB.rejected:
        db.rollback()
        raise CandidateStateConflict("Pendaftar yang sudah rejected tidak dapat di-approve.")

    # Waktu approval diambil dalam zona waktu UTC, lalu informasi zona dihilangkan
    # agar nilai yang disimpan berupa datetime tanpa tzinfo.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Tahun dari waktu approval dipakai sebagai segmen pertama dan bagian kunci counter.
    year = now.year

    # Retry membantu menghadapi benturan UNIQUE saat pembuatan counter pertama
    # pada database multi-worker. SQLite diserialisasi oleh BEGIN IMMEDIATE.
    # Komentar asli berikut menjelaskan retry ketika terjadi benturan saat counter dibuat.
    for attempt in range(3):
        try:
            # Fungsi ini memperbarui counter dan mengembalikan NIM dalam transaksi yang sama.
            nim = generate_nim(db, candidate, year)
            # NIM, status approve, dan waktu approval disiapkan sebelum satu commit.
            candidate.nim = nim
            candidate.status = StatusPMB.approve
            candidate.approve_at = now
            # Commit menyimpan perubahan counter dan calon mahasiswa sebagai satu transaksi.
            db.commit()
            # Refresh mengambil nilai terbaru dari database setelah commit.
            db.refresh(candidate)
            return candidate
        # Percobaan ulang hanya berlaku untuk IntegrityError atau OperationalError.
        except (IntegrityError, OperationalError):
            # Gagal menyimpan berarti transaksi percobaan ini dibatalkan.
            db.rollback()
            # Sesudah tiga percobaan, error terakhir diteruskan ke pemanggil.
            if attempt == 2:
                raise
            # SQLite memulai ulang transaksi tulis sebelum percobaan berikutnya.
            if db.get_bind().dialect.name == "sqlite":
                db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            # Baca ulang objek setelah rollback agar percobaan berikutnya memakai data terbaru.
            candidate = db.scalar(
                select(CalonMahasiswa)
                .where(CalonMahasiswa.id == candidate_id)
                .with_for_update()
            )
            # Pendaftar mungkin tidak lagi tersedia setelah transaksi dimulai ulang.
            if candidate is None:
                raise CandidateNotFound("Pendaftar tidak ditemukan.")
            # Permintaan lain mungkin sudah menyelesaikan approval; kembalikan hasil itu,
            # bukan menerbitkan NIM tambahan.
            if candidate.status == StatusPMB.approve:
                db.commit()
                return candidate
    # Pengaman jika loop selesai tanpa berhasil mengembalikan hasil atau melempar error.
    raise RuntimeError("Gagal membuat NIM setelah percobaan ulang.")


# ==================================================
# SERVICE PMB — PENOLAKAN PENDAFTARAN
# ==================================================
# Fungsi penolakan memastikan hanya pendaftar yang masih pending yang dapat ditolak.
def reject_candidate(db: Session, candidate_id: int) -> CalonMahasiswa:
    # Pada SQLite, transaksi dimulai dengan reservasi tulis sebelum membaca status untuk menghindari perubahan bersamaan yang tidak terserialisasi.
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    # Pencarian menggunakan ID dan meminta row lock pada database yang mendukung SELECT FOR UPDATE.
    candidate = db.scalar(
        select(CalonMahasiswa)
        .where(CalonMahasiswa.id == candidate_id)
        .with_for_update()
    )
    # Jika ID tidak ditemukan, service mengembalikan exception bisnis yang akan menjadi HTTP 404.
    if candidate is None:
        raise CandidateNotFound("Pendaftar tidak ditemukan.")
    # Penolakan hanya sah dari status pending; status lain menghasilkan konflik bisnis.
    if candidate.status != StatusPMB.pending:
        raise CandidateStateConflict("Hanya pendaftar berstatus pending yang dapat ditolak.")
    # Setelah pemeriksaan lolos, status diubah menjadi rejected pada objek ORM.
    candidate.status = StatusPMB.rejected
    # commit menyimpan perubahan status ke database.
    db.commit()
    # refresh memastikan objek yang dikembalikan mencerminkan data terbaru database.
    db.refresh(candidate)
    # Objek hasil perubahan dikembalikan ke router untuk diserialisasi sebagai response.
    return candidate


# ==================================================
# SERVICE PMB — PEMERIKSAAN STATUS
# ==================================================
# Fungsi ini membaca pendaftar berdasarkan primary key tanpa mengubah record.
def get_candidate_status(db: Session, candidate_id: int) -> CalonMahasiswa:
    # db.get menggunakan jenis model dan ID primary key untuk mengambil objek.
    candidate = db.get(CalonMahasiswa, candidate_id)
    # Pendaftar yang tidak ditemukan diterjemahkan menjadi exception khusus.
    if candidate is None:
        raise CandidateNotFound("Pendaftar tidak ditemukan.")
    # Jika ditemukan, objek dikembalikan untuk dipetakan ke schema response oleh router.
    return candidate


# ==================================================
# SERVICE PMB — STATISTIK PENDAFTARAN
# ==================================================
# Query statistik mengagregasi jumlah pendaftar untuk response endpoint /stats.
def get_pmb_stats(db: Session) -> dict:
    # COUNT menghitung seluruh pendaftar; nilai 0 menjadi hasil jika query mengembalikan None.
    total = db.scalar(select(func.count(CalonMahasiswa.id))) or 0
    # Pengelompokan ini menghitung jumlah data untuk setiap status PMB.
    status_rows = db.execute(
        select(CalonMahasiswa.status, func.count(CalonMahasiswa.id))
        .group_by(CalonMahasiswa.status)
    ).all()
    # Baris query diubah menjadi dictionary status-ke-jumlah agar sesuai kontrak response.
    status_counts = {status.value: count for status, count in status_rows}
    # Loop memastikan setiap nilai enum muncul, termasuk status yang saat ini belum memiliki pendaftar.
    for item in StatusPMB:
        status_counts.setdefault(item.value, 0)

    # Outer join mempertahankan program studi yang belum memiliki pendaftar agar statistiknya tetap menampilkan jumlah nol.
    prodi_rows = db.execute(
        select(ProgramStudi.nama, func.count(CalonMahasiswa.id))
        .outerjoin(CalonMahasiswa, CalonMahasiswa.program_studi_id == ProgramStudi.id)
        .group_by(ProgramStudi.id, ProgramStudi.nama)
        .order_by(ProgramStudi.nama)
    ).all()
    # Agregasi jalur masuk memakai pola serupa dan tetap menampilkan referensi tanpa pendaftar.
    jalur_rows = db.execute(
        select(JalurMasuk.nama, func.count(CalonMahasiswa.id))
        .outerjoin(CalonMahasiswa, CalonMahasiswa.jalur_masuk_id == JalurMasuk.id)
        .group_by(JalurMasuk.id, JalurMasuk.nama)
        .order_by(JalurMasuk.nama)
    ).all()

    # Hasil dikembalikan sebagai dictionary yang field-nya sesuai dengan StatsResponse.
    return {
        "total_pendaftar": total,
        "berdasarkan_status": status_counts,
        "berdasarkan_program_studi": [
            # Setiap baris hasil query dikonversi menjadi item nama dan jumlah untuk program studi.
            {"nama": nama, "jumlah": jumlah} for nama, jumlah in prodi_rows
        ],
        "berdasarkan_jalur_masuk": [
            # Jalur masuk dikembalikan dalam bentuk item nama dan jumlah yang sama.
            {"nama": nama, "jumlah": jumlah} for nama, jumlah in jalur_rows
        ],
    }

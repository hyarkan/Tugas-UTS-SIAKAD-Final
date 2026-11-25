# ==================================================
# SERVICE KRS - MANAGER, STATE, VERSION, DAN TRANSAKSI
# ==================================================
# datetime/timezone mencatat waktu UTC; SQLAlchemy menyusun query, menangani session ORM, dan menyediakan eager loading.
# StaleDataError menandai optimistic-version conflict; model dan validator memisahkan data akademik dari aturan validasi.
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.exc import StaleDataError
# KRSManager bekerja dengan model KRS, detail, mata kuliah, log, notifikasi, serta rantai validator.
from app.models import KRS, KRSDetail, KRSStatus, MataKuliah, KRSLog, KRSNotification
from app.services.krs_validators import KRSContext, build_chain


# KRSError adalah exception dasar dengan status HTTP default untuk error bisnis KRS.
class KRSError(Exception):
    # Router membaca status_code ini saat menerjemahkan error service menjadi HTTP response.
    status_code = 400

# KRSForbidden mewakili tindakan yang tidak diizinkan, misalnya identitas mahasiswa atau dosen tidak cocok.
class KRSForbidden(KRSError):
    status_code = 403

# TransitionError menunjukkan permintaan perpindahan state yang tidak dapat dilakukan.
class TransitionError(KRSError):
    status_code = 409

# KRSStateConflict memperinci konflik state/version dan mewarisi status HTTP 409 dari TransitionError.
class KRSStateConflict(TransitionError):
    pass

# StudentNotFound menandai NIM yang tidak ditemukan atau belum memiliki identitas mahasiswa aktif untuk KRS.
class StudentNotFound(KRSError):
    status_code = 404

# CourseNotFound menunjukkan mata kuliah atau detail pengambilan tidak tersedia.
class CourseNotFound(KRSError):
    status_code = 404

# KRSNotFound digunakan ketika record KRS yang diminta tidak ditemukan.
class KRSNotFound(KRSError):
    status_code = 404

# KRSValidationError menandai kegagalan aturan isi atau input bisnis KRS.
class KRSValidationError(KRSError):
    status_code = 400


# >>> FOKUS PRESENTASI UTS <<<
# KRSManager menjadi service yang mengoordinasikan model, database, validator, transaksi, dan alur bisnis KRS.
class KRSManager:
    # Dokumentasi class merangkum peran manager dalam transaksi dan otorisasi bisnis KRS.
    """Service KRS; transaksi dan otorisasi bisnis dikelola di lapisan service."""
    # Constructor menerima session database, semester kerja, dan chain opsional untuk memudahkan penggunaan atau pengujian.
    def __init__(self, db: Session, semester: str, validator_chain=None):
        # Session ORM dipakai oleh method manager untuk query dan mutasi database.
        self.db = db
        # Semester disimpan agar seluruh query manager konsisten pada periode ini.
        self.semester = semester
        # Chain yang diberikan digunakan apa adanya; jika tidak diberikan, manager membangun urutan validator default.
        self.validator_chain = validator_chain or build_chain()

    # Mengunci atau membuat KRS agar operasi mutasi bekerja pada satu record mahasiswa dan semester.
    def _lock_krs(self, nim: str, create: bool = False) -> KRS:
        # SQLite tidak memiliki SELECT FOR UPDATE. BEGIN IMMEDIATE menserialisasi writer.
        # Pilihan penguncian bergantung pada dialect database; komentar asli di bawah menjelaskan jalur khusus SQLite.
        if self.db.get_bind().dialect.name == "sqlite":
            self.db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        # Query menargetkan pasangan NIM-semester dan meminta row lock pada database yang mendukung SELECT FOR UPDATE.
        stmt = select(KRS).where(KRS.nim == nim, KRS.semester == self.semester).with_for_update()
        # scalar mengambil satu objek KRS atau None jika belum ada.
        krs = self.db.scalar(stmt)
        # Jika KRS belum ada, service memeriksa apakah NIM tersebut berasal dari mahasiswa yang sudah terdaftar.
        if krs is None:
            # Import lokal menjaga dependensi model mahasiswa tetap berada di jalur yang membutuhkan pengecekan ini.
            from app.models import CalonMahasiswa
            # Pencarian menggunakan NIM, bukan ID calon, karena KRS dimiliki mahasiswa yang sudah memiliki NIM.
            if self.db.scalar(select(CalonMahasiswa.id).where(CalonMahasiswa.nim == nim)) is None:
                # StudentNotFound menandai NIM yang tidak ditemukan; keberadaan NIM menjadi penanda mahasiswa yang sudah di-approve.
                raise StudentNotFound("NIM tidak ditemukan atau mahasiswa belum di-approve.")
            # KRS yang tidak ada hanya dibuat jika pemanggil secara eksplisit meminta create=True.
            if not create:
                # Operasi yang hanya membaca atau mengubah KRS yang ada tidak membuat record secara diam-diam.
                raise KRSNotFound("KRS untuk NIM dan semester tersebut tidak ditemukan.")
            # KRS baru dimulai dalam status draft untuk semester dan mahasiswa tersebut.
            krs = KRS(nim=nim, semester=self.semester, status=KRSStatus.draft.value)
            # add memasukkan objek baru ke unit kerja session; belum berarti transaksi sudah commit.
            self.db.add(krs)
            # flush mengirim INSERT agar ID KRS tersedia dalam transaksi tanpa commit lebih awal.
            self.db.flush()
        # KRS hasil pencarian atau pembuatan dikembalikan kepada pemanggil.
        return krs

    # Aturan ini membatasi perubahan isi KRS hanya pada draft atau revision.
    def _ensure_editable(self, krs: KRS) -> None:
        # Status submitted/approved tidak dapat diedit langsung melalui operasi isi KRS biasa.
        if krs.status not in (KRSStatus.draft.value, KRSStatus.revision.value):
            raise KRSStateConflict("Isi KRS terkunci. Perubahan hanya diizinkan pada status draft atau revision.")

    # Menyusun konteks yang dibutuhkan validator untuk membandingkan mata kuliah baru dengan isi KRS.
    def _context(self, krs: KRS, course: MataKuliah) -> KRSContext:
        # Query mengambil semua mata kuliah pada detail KRS, diurutkan agar konteks stabil.
        existing = list(self.db.scalars(
            select(MataKuliah).join(KRSDetail, KRSDetail.kode_mk == MataKuliah.kode_mk)
            .where(KRSDetail.krs_id == krs.id).order_by(MataKuliah.kode_mk)
        ).all())
        # Context membawa identitas, semester, mata kuliah existing/baru, session, dan ID KRS ke validator.
        return KRSContext(krs.nim, krs.semester, existing, course, self.db, krs.id)

    # >>> FOKUS PRESENTASI UTS <<<
    # add_course menangani pemeriksaan kelayakan, validasi chain, dan penyimpanan satu detail mata kuliah.
    def add_course(self, nim: str, kode_mk: str) -> KRSDetail:
        # Blok try memastikan kegagalan selama mutasi ditangani dengan rollback yang sesuai.
        try:
            # Pemeriksaan tunggakan menggunakan layanan keuangan dan diimpor lokal pada saat diperlukan.
            from app.services.finance import has_arrears
            # Jika terdapat tunggakan, penambahan mata kuliah dihentikan sebelum KRS dimutasi.
            if has_arrears(self.db, nim, self.semester):
                raise KRSForbidden("Pengisian KRS diblokir: terdapat tagihan SPP belum lunas atau tunggakan.")
            # KRS dicari atau dibuat sebagai draft setelah prasyarat keuangan lolos.
            krs = self._lock_krs(nim, create=True)
            # Manager memastikan status KRS masih dapat diedit sebelum isi diubah.
            self._ensure_editable(krs)
            # Katalog mata kuliah dicari berdasarkan kode yang dikirim pemanggil.
            course = self.db.get(MataKuliah, kode_mk)
            # Kode yang tidak ditemukan menghasilkan error bisnis CourseNotFound.
            if course is None:
                raise CourseNotFound(f"Mata kuliah {kode_mk} tidak ditemukan.")
            # Chain menjalankan validator dalam urutan yang dirakit; kegagalan pertama dikembalikan secara fail-fast.
            result = self.validator_chain.validate(self._context(krs, course))
            # Hasil gagal dari chain diterjemahkan menjadi error validasi untuk router.
            if not result.oke:
                raise KRSValidationError(result.message)
            # Detail baru menghubungkan KRS dengan kode mata kuliah yang telah lolos validasi.
            detail = KRSDetail(krs_id=krs.id, kode_mk=kode_mk)
            # add menandai detail baru untuk disimpan bersama perubahan parent.
            self.db.add(detail)
            # Perubahan detail juga menyentuh parent agar optimistic version bertambah.
            krs.updated_at = datetime.now(timezone.utc)
            # Commit menyimpan detail dan pembaruan parent dalam transaksi yang sama.
            self.db.commit()
            # Refresh membaca ulang detail setelah commit agar atribut database tersedia.
            self.db.refresh(detail)
            # Detail tersimpan dikembalikan sebagai hasil operasi tambah.
            return detail
        # IntegrityError dapat berasal dari constraint database, termasuk pasangan mata kuliah yang sudah tercatat.
        except IntegrityError as exc:
            # Rollback membatalkan transaksi gagal sebelum error bisnis diteruskan.
            self.db.rollback()
            # Constraint failure diterjemahkan menjadi KRSValidationError yang dapat dipetakan router.
            raise KRSValidationError("Mata kuliah sudah tercatat pada KRS ini atau terjadi konflik constraint.") from exc
        # Error lain tidak disembunyikan: transaksi aktif dibatalkan lalu exception dilempar kembali.
        except Exception:
            # Cek in_transaction menghindari rollback ketika tidak ada transaksi aktif.
            if self.db.in_transaction(): self.db.rollback()
            # raise tanpa argumen mempertahankan exception asli untuk lapisan pemanggil.
            raise

    # remove_course menghapus satu detail, tetapi hanya saat KRS masih dapat diedit.
    def remove_course(self, nim: str, kode_mk: str) -> None:
        # Operasi penghapusan juga menjaga transaksi lewat try/rollback.
        try:
            # KRS yang tidak ada tidak dibuat oleh operasi remove.
            krs = self._lock_krs(nim)
            # Status tetap diperiksa sebelum detail dihapus.
            self._ensure_editable(krs)
            # Detail dicari berdasarkan pasangan ID KRS dan kode mata kuliah.
            detail = self.db.scalar(select(KRSDetail).where(KRSDetail.krs_id == krs.id, KRSDetail.kode_mk == kode_mk))
            # Detail yang tidak ditemukan menghasilkan pesan error khusus.
            if detail is None:
                raise CourseNotFound("Mata kuliah tersebut tidak ditemukan di KRS.")
            # Detail ditandai untuk dihapus dalam transaksi session.
            self.db.delete(detail)
            # Parent disentuh agar perubahan detail ikut menaikkan optimistic version KRS.
            krs.updated_at = datetime.now(timezone.utc)
            # Commit menyimpan penghapusan dan pembaruan versi parent.
            self.db.commit()
        # Bila terjadi error, transaksi aktif dibatalkan lalu exception asli diteruskan.
        except Exception:
            # Rollback hanya dilakukan bila session masih memiliki transaksi aktif.
            if self.db.in_transaction(): self.db.rollback()
            # Exception tidak ditelan oleh service.
            raise

    # >>> FOKUS PRESENTASI UTS <<<
    # validate_krs memeriksa seluruh isi KRS dan mengumpulkan pesan kesalahan, berbeda dari fail-fast saat add_course.
    def validate_krs(self, nim: str) -> list[str]:
        # Eager loading mengambil KRS, detail, dan MataKuliah dalam query agar data untuk validasi tersedia bersama.
        krs = self.db.execute(select(KRS).options(joinedload(KRS.details).joinedload(KRSDetail.mata_kuliah)).where(
            KRS.nim == nim, KRS.semester == self.semester)).unique().scalar_one_or_none()
        # Jika KRS tidak ada, tidak ada isi yang dapat divalidasi.
        if krs is None:
            raise KRSNotFound("KRS untuk NIM dan semester tersebut tidak ditemukan.")
        # Daftar ini mengambil objek mata kuliah dari detail KRS.
        courses = [detail.mata_kuliah for detail in krs.details]
        # errors menampung hasil gagal yang akan dikembalikan ke pemanggil.
        errors: list[str] = []
        # Rantai linked-list ditelusuri untuk mendapatkan setiap validator.
        validators = []
        current = self.validator_chain
        # Loop berakhir ketika node berikutnya tidak ada.
        while current is not None:
            # Simpan node aktif supaya setiap aturan dapat dipanggil pada seluruh mata kuliah.
            validators.append(current)
            # Pindah ke validator berikutnya pada rantai.
            current = current.next_validator
        # Setiap mata kuliah diuji sebagai item baru terhadap mata kuliah lain di dalam KRS.
        for course in courses:
            # Peer mengeluarkan item yang sedang diuji agar tidak dibandingkan dengan dirinya sendiri.
            peers = [item for item in courses if item.kode_mk != course.kode_mk]
            # Context disusun ulang untuk validasi satu course terhadap peers pada KRS yang sama.
            ctx = KRSContext(nim, self.semester, peers, course, self.db, krs.id)
            # Semua validator diperiksa untuk item ini agar error dapat dikumpulkan, bukan berhenti pada kegagalan pertama.
            for validator in validators:
                # check dipanggil langsung; berbeda dari validate(), cara ini tidak meneruskan fail-fast.
                result = validator.check(ctx)
                # Tambahkan pesan gagal yang belum pernah dicatat agar daftar error tidak mengulang pesan sama.
                if not result.oke and result.message not in errors:
                    errors.append(result.message)
        # Total SKS seluruh KRS dihitung kembali sebagai pemeriksaan keseluruhan isi.
        total = sum(course.sks for course in courses)
        # Total di atas 24 SKS menambah error khusus pada posisi awal daftar.
        if total > 24:
            errors.insert(0, f"Total SKS {total} melebihi batas maksimal 24 SKS.")
        # Pemanggil menerima semua pesan yang terkumpul; daftar kosong berarti tidak ada error yang ditemukan.
        return errors

    # Membandingkan versi yang dibaca klien dengan versi KRS saat ini sebelum transisi dijalankan.
    def _check_version(self, krs: KRS, expected_version: int | None) -> None:
        # Versi wajib disediakan agar request perubahan status tidak berjalan tanpa acuan data klien.
        if expected_version is None:
            raise KRSValidationError("Field version wajib dikirim untuk mencegah approval menggunakan data yang sudah usang.")
        # Versi yang berbeda menandakan data klien sudah usang dan perlu dimuat ulang.
        if krs.version != expected_version:
            raise KRSStateConflict(f"Versi KRS sudah berubah (versi saat ini {krs.version}); muat ulang KRS sebelum melanjutkan.")

    # Membuat catatan audit dan notifikasi database untuk sebuah transisi status.
    def _record_transition(self, krs: KRS, actor_role: str, actor_id: str, action: str,
                            from_status: str, note: str | None = None) -> None:
        # Log mencatat aktor, tindakan, status asal/tujuan, dan catatan opsional pada session yang sama.
        self.db.add(KRSLog(krs_id=krs.id, actor_role=actor_role, actor_id=str(actor_id),
                           action=action, from_status=from_status, to_status=krs.status, note=note))
        # Notifikasi disimpan sebagai record database; bagian ini tidak mengirim email atau pesan eksternal.
        self.db.add(KRSNotification(krs_id=krs.id, recipient_nim=krs.nim,
            message=f"KRS semester {krs.semester}: status berubah dari {from_status} menjadi {krs.status}.", is_read=False))

    # >>> FOKUS PRESENTASI UTS <<<
    # submit_krs memvalidasi kepemilikan, versi, state, isi, dan tunggakan sebelum mengajukan KRS.
    def submit_krs(self, nim: str, actor_nim: str, expected_version: int) -> KRS:
        # Submit dijalankan dalam transaksi agar perubahan status, log, dan notifikasi dapat disimpan bersama.
        try:
            # Pemeriksaan tunggakan juga diterapkan pada tahap pengajuan.
            from app.services.finance import has_arrears
            # Submit diblokir jika layanan keuangan melaporkan tunggakan.
            if has_arrears(self.db, nim, self.semester):
                raise KRSForbidden("Submit KRS diblokir: terdapat tagihan SPP belum lunas atau tunggakan.")
            # KRS yang akan diajukan harus sudah ada.
            krs = self._lock_krs(nim)
            # NIM aktor harus sama dengan pemilik KRS; ini pemeriksaan bisnis, bukan autentikasi production.
            if actor_nim != nim:
                raise KRSForbidden("Mahasiswa hanya boleh mengajukan KRS miliknya sendiri.")
            # Versi request diperiksa untuk mencegah submit menggunakan data yang sudah berubah.
            self._check_version(krs, expected_version)
            # Model KRS memeriksa transisi submitted untuk peran mahasiswa.
            krs.check_transition(KRSStatus.submitted.value, "mahasiswa")
            # KRS kosong tidak dapat diajukan.
            if not krs.details:
                raise KRSValidationError("KRS masih kosong. Tambahkan minimal satu mata kuliah sebelum submit.")
            # Semua course divalidasi ulang tepat sebelum status berpindah.
            errors = self.validate_krs(nim)
            # Error yang terkumpul menghentikan submit dan digabungkan menjadi pesan validasi.
            if errors:
                raise KRSValidationError("KRS belum dapat diajukan: " + " ".join(errors))
            # Status asal disimpan untuk keperluan audit log.
            old_status = krs.status
            # transition memanggil check_transition kembali lalu mengubah status dan updated_at.
            krs.transition(KRSStatus.submitted.value, "mahasiswa")
            # Timestamp pengajuan dicatat dalam UTC.
            krs.submitted_at = datetime.now(timezone.utc)
            # Catatan revisi lama dibersihkan ketika mahasiswa mengajukan kembali KRS.
            krs.revision_note = None
            # Perubahan status menghasilkan log dan notifikasi database dalam session yang sama.
            self._record_transition(krs, "mahasiswa", actor_nim, "submit", old_status)
            # Satu commit menyimpan status, waktu submit, audit log, dan notifikasi secara atomik.
            self.db.commit()
            # Refresh memuat ulang nilai KRS setelah commit, termasuk version terbaru.
            self.db.refresh(krs)
            # KRS terbaru dikembalikan ke router untuk diserialisasi sebagai response.
            return krs
        # StaleDataError dapat muncul jika optimistic version berubah di antara pemeriksaan dan penyimpanan.
        except StaleDataError as exc:
            # Rollback membatalkan perubahan yang gagal karena konflik versi.
            self.db.rollback()
            # Konflik diterjemahkan menjadi KRSStateConflict agar router mengembalikan HTTP 409.
            raise KRSStateConflict("KRS berubah saat diproses. Muat ulang data dan coba kembali.") from exc
        # Error lain juga membatalkan transaksi aktif tanpa menelan exception.
        except Exception:
            # Rollback dilakukan hanya jika session masih berada dalam transaksi.
            if self.db.in_transaction(): self.db.rollback()
            # Exception asli diteruskan kembali ke router.
            raise

    # >>> FOKUS PRESENTASI UTS <<<
    # approve_krs memeriksa dosen PA, versi, transisi, dan validitas sebelum menyimpan persetujuan.
    def approve_krs(self, nim: str, actor_id: int, expected_version: int) -> KRS:
        # Seluruh tahap approval berada dalam penanganan transaksi dan error.
        try:
            # Approval hanya dilakukan pada KRS yang sudah ada.
            krs = self._lock_krs(nim)
            # ID aktor harus cocok dengan dosen PA yang ditetapkan pada record KRS.
            if krs.dosen_pa_id is None or krs.dosen_pa_id != actor_id:
                raise KRSForbidden("Hanya dosen PA yang terdaftar pada KRS mahasiswa ini yang boleh menyetujui.")
            # Versi harus masih sama dengan versi yang dilihat klien.
            self._check_version(krs, expected_version)
            # Model KRS memeriksa apakah dosen PA boleh mengubah status ke approved.
            krs.check_transition(KRSStatus.approved.value, "dosen_pa")
            # Isi KRS divalidasi kembali sebelum dosen menyetujui.
            errors = self.validate_krs(nim)
            # Jika validasi menghasilkan error, approval dihentikan.
            if errors:
                raise KRSValidationError("KRS tidak dapat disetujui: " + " ".join(errors))
            # Status lama disimpan untuk audit trail.
            old_status = krs.status
            # Model memvalidasi transisi lalu mengubah status dan waktu pembaruan.
            krs.transition(KRSStatus.approved.value, "dosen_pa")
            # Waktu persetujuan dicatat dalam UTC.
            krs.approved_at = datetime.now(timezone.utc)
            # Satu transisi menambahkan audit log dan notifikasi ke database.
            self._record_transition(krs, "dosen_pa", str(actor_id), "approve", old_status)
            # Status, timestamp, audit log, dan notifikasi masuk dalam satu commit.
            self.db.commit()
            # Refresh membaca state dan version terkini setelah commit.
            self.db.refresh(krs)
            # Objek KRS hasil approval dikembalikan ke router.
            return krs
        # Optimistic version conflict yang muncul saat flush/commit ditangani khusus.
        except StaleDataError as exc:
            # Rollback mengurungkan seluruh perubahan transaksi approval yang gagal.
            self.db.rollback()
            # Konflik versi diteruskan sebagai error bisnis yang dapat dipetakan menjadi HTTP 409.
            raise KRSStateConflict("Versi KRS sudah berubah; approval ditolak. Muat ulang KRS.") from exc
        # Error lain tidak ditelan dan tetap menyebabkan rollback transaksi aktif.
        except Exception:
            # Periksa transaksi sebelum rollback untuk menjaga session.
            if self.db.in_transaction(): self.db.rollback()
            # Teruskan exception yang tidak termasuk konflik versi.
            raise

    # >>> FOKUS PRESENTASI UTS <<<
    # revise_krs meminta perubahan ke revision dengan catatan yang wajib menjelaskan perbaikan.
    def revise_krs(self, nim: str, actor_id: int, expected_version: int, note: str) -> KRS:
        # Revisi menggunakan pola transaksi dan rollback yang sama dengan submit/approval.
        try:
            # KRS harus tersedia sebelum dosen mengajukan revisi.
            krs = self._lock_krs(nim)
            # Aktor harus sama dengan dosen PA yang ditetapkan pada KRS.
            if krs.dosen_pa_id is None or krs.dosen_pa_id != actor_id:
                raise KRSForbidden("Hanya dosen PA yang terdaftar pada KRS mahasiswa ini yang boleh meminta revisi.")
            # Versi lama ditolak sebelum transisi dilakukan.
            self._check_version(krs, expected_version)
            # Catatan kosong atau hanya whitespace tidak dapat menjadi instruksi revisi.
            if not note or not note.strip():
                raise KRSValidationError("Catatan revisi wajib diisi agar mahasiswa mengetahui perbaikannya.")
            # Model memeriksa transisi ke revision untuk peran dosen PA.
            krs.check_transition(KRSStatus.revision.value, "dosen_pa")
            # Status sebelumnya dipertahankan untuk log.
            old_status = krs.status
            # transition menjalankan pemeriksaan state lalu memperbarui status dan updated_at.
            krs.transition(KRSStatus.revision.value, "dosen_pa")
            # Catatan disimpan setelah whitespace di tepi dihapus.
            krs.revision_note = note.strip()
            # Log dan notifikasi database dicatat bersama transisi revisi.
            self._record_transition(krs, "dosen_pa", str(actor_id), "revise", old_status, note.strip())
            # Commit menyimpan status, catatan, log, dan notifikasi dalam satu transaksi.
            self.db.commit()
            # Refresh mengisi state terkini pada objek hasil.
            self.db.refresh(krs)
            # KRS hasil revisi dikembalikan ke router untuk response API.
            return krs
        # Konflik optimistic version ditangani secara khusus.
        except StaleDataError as exc:
            # Rollback membatalkan seluruh transaksi revisi yang gagal.
            self.db.rollback()
            # Error versi usang menjadi konflik bisnis yang dapat dikirim sebagai HTTP 409.
            raise KRSStateConflict("Versi KRS sudah berubah. Muat ulang KRS sebelum meminta revisi.") from exc
        # Error lain juga dibatalkan, lalu diteruskan tanpa disamarkan.
        except Exception:
            # Hanya rollback jika transaksi masih aktif.
            if self.db.in_transaction(): self.db.rollback()
            # Exception asli tetap terlihat oleh pemanggil.
            raise

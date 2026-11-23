from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.exc import StaleDataError
from app.models import KRS, KRSDetail, KRSStatus, MataKuliah, KRSLog, KRSNotification
from app.services.krs_validators import KRSContext, build_chain


class KRSError(Exception):
    status_code = 400

class KRSForbidden(KRSError):
    status_code = 403

class TransitionError(KRSError):
    status_code = 409

class KRSStateConflict(TransitionError):
    pass

class StudentNotFound(KRSError):
    status_code = 404

class CourseNotFound(KRSError):
    status_code = 404

class KRSNotFound(KRSError):
    status_code = 404

class KRSValidationError(KRSError):
    status_code = 400


class KRSManager:
    """Service KRS; transaksi dan otorisasi bisnis dikelola di lapisan service."""
    def __init__(self, db: Session, semester: str, validator_chain=None):
        self.db = db
        self.semester = semester
        self.validator_chain = validator_chain or build_chain()

    def _lock_krs(self, nim: str, create: bool = False) -> KRS:
        # SQLite tidak memiliki SELECT FOR UPDATE. BEGIN IMMEDIATE menserialisasi writer.
        if self.db.get_bind().dialect.name == "sqlite":
            self.db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        stmt = select(KRS).where(KRS.nim == nim, KRS.semester == self.semester).with_for_update()
        krs = self.db.scalar(stmt)
        if krs is None:
            from app.models import CalonMahasiswa
            if self.db.scalar(select(CalonMahasiswa.id).where(CalonMahasiswa.nim == nim)) is None:
                raise StudentNotFound("NIM tidak ditemukan atau mahasiswa belum di-approve.")
            if not create:
                raise KRSNotFound("KRS untuk NIM dan semester tersebut tidak ditemukan.")
            krs = KRS(nim=nim, semester=self.semester, status=KRSStatus.draft.value)
            self.db.add(krs)
            self.db.flush()
        return krs

    def _ensure_editable(self, krs: KRS) -> None:
        if krs.status not in (KRSStatus.draft.value, KRSStatus.revision.value):
            raise KRSStateConflict("Isi KRS terkunci. Perubahan hanya diizinkan pada status draft atau revision.")

    def _context(self, krs: KRS, course: MataKuliah) -> KRSContext:
        existing = list(self.db.scalars(
            select(MataKuliah).join(KRSDetail, KRSDetail.kode_mk == MataKuliah.kode_mk)
            .where(KRSDetail.krs_id == krs.id).order_by(MataKuliah.kode_mk)
        ).all())
        return KRSContext(krs.nim, krs.semester, existing, course, self.db, krs.id)

    def add_course(self, nim: str, kode_mk: str) -> KRSDetail:
        try:
            from app.services.finance import has_arrears
            if has_arrears(self.db, nim, self.semester):
                raise KRSForbidden("Pengisian KRS diblokir: terdapat tagihan SPP belum lunas atau tunggakan.")
            krs = self._lock_krs(nim, create=True)
            self._ensure_editable(krs)
            course = self.db.get(MataKuliah, kode_mk)
            if course is None:
                raise CourseNotFound(f"Mata kuliah {kode_mk} tidak ditemukan.")
            result = self.validator_chain.validate(self._context(krs, course))
            if not result.oke:
                raise KRSValidationError(result.message)
            detail = KRSDetail(krs_id=krs.id, kode_mk=kode_mk)
            self.db.add(detail)
            # Perubahan detail juga menyentuh parent agar optimistic version bertambah.
            krs.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(detail)
            return detail
        except IntegrityError as exc:
            self.db.rollback()
            raise KRSValidationError("Mata kuliah sudah tercatat pada KRS ini atau terjadi konflik constraint.") from exc
        except Exception:
            if self.db.in_transaction(): self.db.rollback()
            raise

    def remove_course(self, nim: str, kode_mk: str) -> None:
        try:
            krs = self._lock_krs(nim)
            self._ensure_editable(krs)
            detail = self.db.scalar(select(KRSDetail).where(KRSDetail.krs_id == krs.id, KRSDetail.kode_mk == kode_mk))
            if detail is None:
                raise CourseNotFound("Mata kuliah tersebut tidak ditemukan di KRS.")
            self.db.delete(detail)
            krs.updated_at = datetime.now(timezone.utc)
            self.db.commit()
        except Exception:
            if self.db.in_transaction(): self.db.rollback()
            raise

    def validate_krs(self, nim: str) -> list[str]:
        krs = self.db.execute(select(KRS).options(joinedload(KRS.details).joinedload(KRSDetail.mata_kuliah)).where(
            KRS.nim == nim, KRS.semester == self.semester)).unique().scalar_one_or_none()
        if krs is None:
            raise KRSNotFound("KRS untuk NIM dan semester tersebut tidak ditemukan.")
        courses = [detail.mata_kuliah for detail in krs.details]
        errors: list[str] = []
        validators = []
        current = self.validator_chain
        while current is not None:
            validators.append(current)
            current = current.next_validator
        for course in courses:
            peers = [item for item in courses if item.kode_mk != course.kode_mk]
            ctx = KRSContext(nim, self.semester, peers, course, self.db, krs.id)
            for validator in validators:
                result = validator.check(ctx)
                if not result.oke and result.message not in errors:
                    errors.append(result.message)
        total = sum(course.sks for course in courses)
        if total > 24:
            errors.insert(0, f"Total SKS {total} melebihi batas maksimal 24 SKS.")
        return errors

    def _check_version(self, krs: KRS, expected_version: int | None) -> None:
        if expected_version is None:
            raise KRSValidationError("Field version wajib dikirim untuk mencegah approval menggunakan data yang sudah usang.")
        if krs.version != expected_version:
            raise KRSStateConflict(f"Versi KRS sudah berubah (versi saat ini {krs.version}); muat ulang KRS sebelum melanjutkan.")

    def _record_transition(self, krs: KRS, actor_role: str, actor_id: str, action: str,
                            from_status: str, note: str | None = None) -> None:
        self.db.add(KRSLog(krs_id=krs.id, actor_role=actor_role, actor_id=str(actor_id),
                           action=action, from_status=from_status, to_status=krs.status, note=note))
        self.db.add(KRSNotification(krs_id=krs.id, recipient_nim=krs.nim,
            message=f"KRS semester {krs.semester}: status berubah dari {from_status} menjadi {krs.status}.", is_read=False))

    def submit_krs(self, nim: str, actor_nim: str, expected_version: int) -> KRS:
        try:
            from app.services.finance import has_arrears
            if has_arrears(self.db, nim, self.semester):
                raise KRSForbidden("Submit KRS diblokir: terdapat tagihan SPP belum lunas atau tunggakan.")
            krs = self._lock_krs(nim)
            if actor_nim != nim:
                raise KRSForbidden("Mahasiswa hanya boleh mengajukan KRS miliknya sendiri.")
            self._check_version(krs, expected_version)
            krs.check_transition(KRSStatus.submitted.value, "mahasiswa")
            if not krs.details:
                raise KRSValidationError("KRS masih kosong. Tambahkan minimal satu mata kuliah sebelum submit.")
            errors = self.validate_krs(nim)
            if errors:
                raise KRSValidationError("KRS belum dapat diajukan: " + " ".join(errors))
            old_status = krs.status
            krs.transition(KRSStatus.submitted.value, "mahasiswa")
            krs.submitted_at = datetime.now(timezone.utc)
            krs.revision_note = None
            self._record_transition(krs, "mahasiswa", actor_nim, "submit", old_status)
            self.db.commit()
            self.db.refresh(krs)
            return krs
        except StaleDataError as exc:
            self.db.rollback()
            raise KRSStateConflict("KRS berubah saat diproses. Muat ulang data dan coba kembali.") from exc
        except Exception:
            if self.db.in_transaction(): self.db.rollback()
            raise

    def approve_krs(self, nim: str, actor_id: int, expected_version: int) -> KRS:
        try:
            krs = self._lock_krs(nim)
            if krs.dosen_pa_id is None or krs.dosen_pa_id != actor_id:
                raise KRSForbidden("Hanya dosen PA yang terdaftar pada KRS mahasiswa ini yang boleh menyetujui.")
            self._check_version(krs, expected_version)
            krs.check_transition(KRSStatus.approved.value, "dosen_pa")
            errors = self.validate_krs(nim)
            if errors:
                raise KRSValidationError("KRS tidak dapat disetujui: " + " ".join(errors))
            old_status = krs.status
            krs.transition(KRSStatus.approved.value, "dosen_pa")
            krs.approved_at = datetime.now(timezone.utc)
            self._record_transition(krs, "dosen_pa", str(actor_id), "approve", old_status)
            # Status, timestamp, audit log, dan notifikasi masuk dalam satu commit.
            self.db.commit()
            self.db.refresh(krs)
            return krs
        except StaleDataError as exc:
            self.db.rollback()
            raise KRSStateConflict("Versi KRS sudah berubah; approval ditolak. Muat ulang KRS.") from exc
        except Exception:
            if self.db.in_transaction(): self.db.rollback()
            raise

    def revise_krs(self, nim: str, actor_id: int, expected_version: int, note: str) -> KRS:
        try:
            krs = self._lock_krs(nim)
            if krs.dosen_pa_id is None or krs.dosen_pa_id != actor_id:
                raise KRSForbidden("Hanya dosen PA yang terdaftar pada KRS mahasiswa ini yang boleh meminta revisi.")
            self._check_version(krs, expected_version)
            if not note or not note.strip():
                raise KRSValidationError("Catatan revisi wajib diisi agar mahasiswa mengetahui perbaikannya.")
            krs.check_transition(KRSStatus.revision.value, "dosen_pa")
            old_status = krs.status
            krs.transition(KRSStatus.revision.value, "dosen_pa")
            krs.revision_note = note.strip()
            self._record_transition(krs, "dosen_pa", str(actor_id), "revise", old_status, note.strip())
            self.db.commit()
            self.db.refresh(krs)
            return krs
        except StaleDataError as exc:
            self.db.rollback()
            raise KRSStateConflict("Versi KRS sudah berubah. Muat ulang KRS sebelum meminta revisi.") from exc
        except Exception:
            if self.db.in_transaction(): self.db.rollback()
            raise

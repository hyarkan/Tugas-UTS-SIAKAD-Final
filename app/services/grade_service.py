"""Authorized, attendance-checked, transactional grade management."""

from typing import Protocol

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import KRS, KRSDetail, KRSStatus, SkalaNilai
from app.models.scheduling import Jadwal


class GradeError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class PresensiPort(Protocol):
    def persentase(self, nim: str, kelas_id: int) -> float: ...


class PresensiStub:
    """Temporary adapter until attendance module arrives in Week 12.

    Fail closed when no attendance data exists; no fabricated attendance.
    """

    def __init__(
        self,
        values: dict[tuple[str, int], float] | None = None
    ):
        self.values = values or {}

    def persentase(self, nim: str, kelas_id: int) -> float:
        if (nim, kelas_id) not in self.values:
            raise GradeError(
                "Presensi belum tersedia; nilai tidak dapat diinput.",
                409
            )

        value = self.values[(nim, kelas_id)]

        if not 0 <= value <= 100:
            raise GradeError("Data presensi tidak valid.", 409)

        return value


class GradeService:
    def __init__(self, db: Session, presensi: PresensiPort):
        self.db = db
        self.presensi = presensi

    def is_pengampu(self, kelas_id: int, dosen_id: int) -> bool:
        return self.db.scalar(
            select(Jadwal.id)
            .where(
                Jadwal.kelas_id == kelas_id,
                Jadwal.dosen_id == dosen_id
            )
            .limit(1)
        ) is not None

    def input_nilai(
        self,
        *,
        dosen_id: int,
        kelas_id: int,
        nim: str,
        nilai: str,
        reason: str | None = None
    ):
        if not self.is_pengampu(kelas_id, dosen_id):
            raise GradeError(
                "Hanya dosen pengampu yang boleh mengisi nilai.",
                403
            )

        enrollment = self.db.execute(
            select(KRSDetail, KRS.status)
            .join(KRS, KRS.id == KRSDetail.krs_id)
            .where(
                KRS.nim == nim,
                KRSDetail.kelas_id == kelas_id
            )
            .with_for_update()
        ).first()

        if enrollment is None:
            raise GradeError("Peserta kelas tidak ditemukan.", 404)

        detail, krs_status = enrollment
        if krs_status != KRSStatus.approved.value:
            raise GradeError(
                "Nilai hanya dapat diinput pada KRS yang telah disetujui.",
                409
            )

        if self.presensi.persentase(nim, kelas_id) < 75:
            raise GradeError("Presensi kurang dari 75%.", 403)

        if self.db.get(SkalaNilai, nilai) is None:
            raise GradeError(
                "Huruf nilai tidak tersedia dalam skala nilai.",
                422
            )

        if detail.nilai == nilai:
            return {
                "nim": nim,
                "kelas_id": kelas_id,
                "nilai": nilai,
                "changed": False
            }

        if detail.nilai is not None and not (reason or "").strip():
            raise GradeError(
                "Alasan wajib untuk perubahan nilai.",
                422
            )

        try:
            # Simpan konteks audit sebelum UPDATE nilai.
            # Trigger database menggunakan konteks ini
            # untuk mencatat perubahan ke grade_history.
            self.db.execute(
                text("""
                    INSERT INTO grade_audit_context (
                        grade_id,
                        changed_by,
                        reason
                    )
                    VALUES (
                        :grade_id,
                        :changed_by,
                        :reason
                    )
                """),
                {
                    "grade_id": detail.id,
                    "changed_by": dosen_id,
                    "reason": reason.strip() if reason else None
                }
            )

            # UPDATE ini akan mengaktifkan trigger Audit Trail.
            detail.nilai = nilai

            # UPDATE dan audit history berada
            # dalam satu transaksi database.
            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return {
            "nim": nim,
            "kelas_id": kelas_id,
            "nilai": nilai,
            "changed": True
        }

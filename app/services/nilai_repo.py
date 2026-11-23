"""Database adapter for GPA and history; pure calculation lives in gpa.py."""
from decimal import Decimal
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.models import KRS, KRSDetail, KRSStatus, MataKuliah, SkalaNilai
from app.services.gpa import NilaiRecord, Skala, hitung_ips, hitung_ipk

class NilaiRepo:
    def __init__(self, db: Session):
        self.db = db
    def records(self, nim: str) -> list[NilaiRecord]:
        rows = self.db.execute(select(KRSDetail.kode_mk, KRS.semester, MataKuliah.sks, KRSDetail.nilai)
            .join(KRS, KRS.id == KRSDetail.krs_id)
            .join(MataKuliah, MataKuliah.kode_mk == KRSDetail.kode_mk)
            .where(
                KRS.nim == nim,
                KRS.status == KRSStatus.approved.value,
                KRSDetail.nilai.is_not(None),
            )).all()
        return [NilaiRecord(kode, semester, sks, nilai) for kode, semester, sks, nilai in rows]
    def skala(self) -> dict[str, Skala]:
        return {r.nilai: Skala(Decimal(str(r.bobot)), r.lulus) for r in self.db.scalars(select(SkalaNilai))}
    def history(self, nim: str) -> list[dict]:
        rows = self.db.execute(text("""SELECT gh.id, gh.grade_id, gh.nim, gh.kode_mk,
            gh.old_value, gh.new_value, gh.changed_by, gh.dosen_nama, gh.changed_at, gh.reason
            FROM v_grade_history AS gh
            JOIN krs_detail AS kd ON kd.id = gh.grade_id
            JOIN krs AS k ON k.id = kd.krs_id
            WHERE gh.nim = :nim AND k.status = :approved_status
            ORDER BY gh.changed_at, gh.id"""), {
                "nim": nim,
                "approved_status": KRSStatus.approved.value,
            }).mappings()
        return [dict(row) for row in rows]

class GPACalculator:
    def __init__(self, repo: NilaiRepo):
        self.repo = repo
    def calculate_ips(self, nim: str, semester: str) -> Decimal:
        return hitung_ips(self.repo.records(nim), self.repo.skala(), semester)
    def calculate_ipk(self, nim: str) -> Decimal:
        return hitung_ipk(self.repo.records(nim), self.repo.skala())

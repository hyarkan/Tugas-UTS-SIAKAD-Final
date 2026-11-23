"""Week 10: full academic transcript, preserving the Week 9 GPA policy.

The passing threshold is read from skala_nilai.lulus (not hardcoded).
IPK uses the highest passing attempt for each course, as in Week 9.
"""
from collections import defaultdict
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import CalonMahasiswa, ProgramStudi, KRS, KRSDetail, KRSStatus, MataKuliah
from app.services.nilai_repo import NilaiRepo, GPACalculator


def predikat(ipk: Decimal, total_sks: int) -> str:
    """PDF specifies >=3.5 and >=3.0; remaining bands need stakeholder confirmation."""
    if not total_sks:
        return "Belum tersedia (belum ada SKS lulus)"
    if ipk >= Decimal('3.50'):
        return 'Cum Laude (indikatif)'
    if ipk >= Decimal('3.00'):
        return 'Sangat Memuaskan (indikatif)'
    return 'Belum ditetapkan (perlu konfirmasi kebijakan)'


class TranscriptService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = NilaiRepo(db)

    def get_transcript(self, nim: str) -> dict | None:
        mahasiswa = self.db.scalar(select(CalonMahasiswa).where(CalonMahasiswa.nim == nim))
        if mahasiswa is None:
            return None
        prodi = self.db.get(ProgramStudi, mahasiswa.program_studi_id)
        skala = self.repo.skala()
        rows = self.db.execute(
            select(KRS.semester, KRSDetail.id, MataKuliah.kode_mk, MataKuliah.nama,
                   MataKuliah.sks, KRSDetail.nilai)
            .join(KRSDetail, KRSDetail.krs_id == KRS.id)
            .join(MataKuliah, MataKuliah.kode_mk == KRSDetail.kode_mk)
            .where(KRS.nim == nim, KRS.status == KRSStatus.approved.value)
            .order_by(KRS.semester, MataKuliah.kode_mk)
        ).all()
        best = {}
        for semester, detail_id, kode, nama, sks, nilai in rows:
            if nilai is None or nilai not in skala or not skala[nilai].lulus:
                continue
            previous = best.get(kode)
            if previous is None or skala[nilai].bobot > previous[0]:
                best[kode] = (skala[nilai].bobot, detail_id, sks)
        grouped = defaultdict(list)
        for semester, detail_id, kode, nama, sks, nilai in rows:
            grade = skala.get(nilai) if nilai else None
            grouped[semester].append({
                'kode_mk': kode, 'nama_mk': nama, 'sks': sks,
                'nilai': nilai, 'bobot': str(grade.bobot) if grade else None,
                'mutu': str((Decimal(sks) * grade.bobot).quantize(Decimal('0.01'))) if grade else None,
                'lulus': grade.lulus if grade else None,
                'dihitung_ipk': bool(kode in best and best[kode][1] == detail_id),
            })
        calculator = GPACalculator(self.repo)
        semesters = []
        for semester in sorted(grouped):
            semesters.append({'semester': semester, 'ips': str(calculator.calculate_ips(nim, semester)),
                              'mata_kuliah': grouped[semester]})
        total_sks = sum(item[2] for item in best.values())
        ipk = calculator.calculate_ipk(nim)
        return {
            'nim': nim, 'nama': mahasiswa.nama_lengkap,
            'program_studi': prodi.nama if prodi else 'Tidak tersedia',
            'fakultas': prodi.fakultas if prodi else 'Tidak tersedia',
            'angkatan': nim[:4] if len(nim) >= 4 and nim[:4].isdigit() and 2000 <= int(nim[:4]) <= 2100 else 'Belum tersedia',
            'semester': semesters, 'total_sks_lulus': total_sks, 'ipk': str(ipk),
            'predikat': predikat(ipk, total_sks),
            'riwayat_perubahan': self.repo.history(nim),
            'catatan': ('Predikat bersifat indikatif, bukan bukti kelulusan. Aturan D/C, '
                        'predikat di bawah 3.00, dan status kelulusan akhir perlu konfirmasi stakeholder.'),
        }


def get_transcript(db: Session, nim: str) -> dict | None:
    return TranscriptService(db).get_transcript(nim)

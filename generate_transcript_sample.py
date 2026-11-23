"""Generate a reproducible ISTN transcript preview using synthetic data only."""

from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from app.services.gpa import NilaiRecord, Skala, hitung_ipk, hitung_ips
from app.services.transcript_pdf import render_transcript_html, render_transcript_pdf


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "artifacts"
GRADE_SCALE = {
    "A": Skala(Decimal("4.00"), True),
    "B": Skala(Decimal("3.00"), True),
}
COURSES = (
    ("20251", "IF101", "Pengantar Informatika", 3, "A"),
    ("20251", "IF102", "Matematika Dasar", 3, "B"),
    ("20252", "IF201", "Struktur Data", 3, "A"),
    ("20252", "IF202", "Basis Data", 3, "B"),
)


def build_sample_transcript() -> dict:
    records = [
        NilaiRecord(kode_mk=code, semester=semester, sks=sks, nilai=grade)
        for semester, code, _name, sks, grade in COURSES
    ]
    best_attempts = {}
    for record in records:
        grade = GRADE_SCALE[record.nilai]
        previous = best_attempts.get(record.kode_mk)
        if grade.lulus and (
            previous is None
            or grade.bobot > GRADE_SCALE[previous.nilai].bobot
        ):
            best_attempts[record.kode_mk] = record

    courses_by_semester = defaultdict(list)
    for semester, code, name, sks, grade in COURSES:
        scale = GRADE_SCALE[grade]
        record = next(
            item for item in records
            if item.kode_mk == code and item.semester == semester
        )
        courses_by_semester[semester].append({
            "kode_mk": code,
            "nama_mk": name,
            "sks": sks,
            "nilai": grade,
            "mutu": str((Decimal(sks) * scale.bobot).quantize(Decimal("0.01"))),
            "dihitung_ipk": best_attempts.get(code) is record,
        })

    semesters = [
        {
            "semester": semester,
            "ips": str(hitung_ips(records, GRADE_SCALE, semester)),
            "mata_kuliah": courses_by_semester[semester],
        }
        for semester in sorted(courses_by_semester)
    ]
    return {
        "nim": "20990001",
        "nama": "Mahasiswa Simulasi",
        "program_studi": "Sistem Informasi",
        "fakultas": "Fakultas Sains dan Teknologi",
        "angkatan": "2025",
        "angkatan_dari_nim": False,
        "semester": semesters,
        "total_sks_lulus": sum(record.sks for record in best_attempts.values()),
        "ipk": str(hitung_ipk(records, GRADE_SCALE)),
        "predikat": "Cum Laude (indikatif)",
        "catatan": (
            "Transkrip sintetis untuk demonstrasi. Predikat bersifat indikatif "
            "dan bukan bukti kelulusan."
        ),
        "riwayat_perubahan": [
            {
                "changed_at": "2026-01-15 10:30:00",
                "kode_mk": "IF102",
                "old_value": "C",
                "new_value": "B",
                "dosen_nama": "Dosen Simulasi",
                "reason": "Koreksi data simulasi",
            },
        ],
    }


def main() -> None:
    transcript = build_sample_transcript()
    OUTPUT_DIR.mkdir(exist_ok=True)
    html_path = OUTPUT_DIR / "transkrip_simulasi_istn.html"
    pdf_path = OUTPUT_DIR / "transkrip_simulasi_istn.pdf"
    html_path.write_text(
        render_transcript_html(
            transcript,
            logo_src="../app/static/images/logo_istn.png",
        ),
        encoding="utf-8",
    )
    pdf_path.write_bytes(render_transcript_pdf(transcript))
    print(
        f"Created {html_path.relative_to(ROOT)} and {pdf_path.relative_to(ROOT)}; "
        f"IPS={[item['ips'] for item in transcript['semester']]}, "
        f"IPK={transcript['ipk']}, "
        f"SKS={transcript['total_sks_lulus']}."
    )


if __name__ == "__main__":
    main()

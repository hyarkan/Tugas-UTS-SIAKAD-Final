"""Acceptance tests: multi-semester, repeats, missing grades, history, HTML/PDF."""
import builtins
import base64
from datetime import date, time
from decimal import Decimal
import re
import struct
import zlib
import pytest
from generate_transcript_sample import build_sample_transcript
from app.models import CalonMahasiswa, KRS, KRSDetail, KRSStatus, MataKuliah, SkalaNilai
from app.models.scheduling import Dosen
from app.models.grades import GradeHistory
from app.services.nilai_repo import GPACalculator, NilaiRepo
from app.services.transcript import TranscriptService, predikat
from app.services.transcript_pdf import render_transcript_html, render_transcript_pdf


def _force_reportlab(monkeypatch):
    original_import = builtins.__import__

    def import_without_weasyprint(name, *args, **kwargs):
        if name == "weasyprint":
            raise ImportError("ReportLab fallback test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_weasyprint)


def _decoded_pdf_streams(pdf):
    for match in re.finditer(rb"(?m)^stream\r?\n", pdf):
        end = pdf.find(b"endstream", match.end())
        raw = pdf[match.end():end].rstrip(b"\r\n")
        metadata = pdf[max(0, match.start() - 250):match.start()]
        if b"/ASCII85Decode" in metadata:
            raw = base64.a85decode(
                raw[:-2],
                adobe=False,
                ignorechars=b" \t\n\r\x0b\x0c",
            )
        if b"/FlateDecode" in metadata:
            raw = zlib.decompress(raw)
        yield raw


def seed(db, *, with_grades=True):
    db.add(CalonMahasiswa(nama_lengkap='Contoh Mahasiswa',email='transkrip@example.test',
        phone='081234567890',tanggal_lahir=date(2005,1,1),alamat='Alamat uji',
        program_studi_id=1,jalur_masuk_id=1,status='approve',nim='20240001'))
    db.add(Dosen(id=110,nidn='N110',nama='Dosen Penguji'))
    db.add_all([SkalaNilai(nilai=k,bobot=Decimal(str(v)),lulus=passed)
        for k,v,passed in [('A',4,True),('B',3,True),('C',2,True),('D',1,False),('E',0,False)]])
    for code,name,sks in [('M101','Algoritma',3),('M102','Basis Data',2),('M103','Jaringan',2)]:
        db.add(MataKuliah(kode_mk=code,nama=name,sks=sks,hari=1,jam_mulai=time(8),jam_selesai=time(10)))
    db.flush()
    for semester, items in [('20241',[('M101','C'),('M102','A')]),
                            ('20242',[('M101','A'),('M103','B')])]:
        krs=KRS(nim='20240001',semester=semester,status='approved')
        db.add(krs);db.flush()
        for kode,nilai in items:
            detail=KRSDetail(
                krs_id=krs.id,
                kode_mk=kode,
                nilai=nilai if with_grades else None
            )
            db.add(detail);db.flush()
            if with_grades and kode=='M101' and semester=='20242':
                db.add(GradeHistory(grade_id=detail.id,old_value='B',new_value='A',
                                    changed_by=110,reason='Koreksi nilai'))
    db.commit()


def test_multisemester_retake_and_history(db_session):
    seed(db_session)
    t=TranscriptService(db_session).get_transcript('20240001')
    assert len(t['semester'])==2
    assert t['total_sks_lulus']==7
    assert t['ipk']=='3.71' # (3*4 + 2*4 + 2*3) / 7
    assert [s['ips'] for s in t['semester']]==['2.80','3.60']
    first=t['semester'][0]['mata_kuliah'][0]
    assert first['kode_mk']=='M101' and not first['dihitung_ipk']
    assert t['semester'][1]['mata_kuliah'][0]['dihitung_ipk']
    assert len(t['riwayat_perubahan'])==1
    assert t['riwayat_perubahan'][0]['reason']=='Koreksi nilai'
    assert 'Cum Laude' in t['predikat']

@pytest.mark.parametrize(
    "krs_status",
    [KRSStatus.draft.value, KRSStatus.submitted.value, KRSStatus.revision.value],
)
def test_unapproved_krs_is_excluded_from_academic_records(db_session, krs_status):
    seed(db_session)
    db_session.add(MataKuliah(
        kode_mk="M104",
        nama="Mata Kuliah Non-approved",
        sks=4,
        hari=1,
        jam_mulai=time(8),
        jam_selesai=time(10),
    ))
    db_session.flush()

    krs = KRS(nim="20240001", semester="20251", status=krs_status)
    db_session.add(krs)
    db_session.flush()
    detail = KRSDetail(krs_id=krs.id, kode_mk="M104", nilai="A")
    db_session.add(detail)
    db_session.flush()
    db_session.add(GradeHistory(
        grade_id=detail.id,
        old_value="B",
        new_value="A",
        changed_by=110,
        reason="Riwayat KRS belum disetujui",
    ))
    db_session.commit()

    repo = NilaiRepo(db_session)
    transcript = TranscriptService(db_session).get_transcript("20240001")

    assert GPACalculator(repo).calculate_ips("20240001", "20251") == Decimal("0.00")
    assert GPACalculator(repo).calculate_ipk("20240001") == Decimal("3.71")
    assert transcript["total_sks_lulus"] == 7
    assert transcript["ipk"] == "3.71"
    assert [semester["semester"] for semester in transcript["semester"]] == [
        "20241",
        "20242",
    ]
    assert all(
        item["kode_mk"] != "M104"
        for semester in transcript["semester"]
        for item in semester["mata_kuliah"]
    )
    assert all(item["kode_mk"] != "M104" for item in transcript["riwayat_perubahan"])


def test_html_pdf_and_routes(db_session,client):
    seed(db_session)
    t=TranscriptService(db_session).get_transcript('20240001')
    html=render_transcript_html(t)
    assert 'INSTITUT SAINS DAN TEKNOLOGI NASIONAL (ISTN)' in html
    assert 'TRANSKRIP AKADEMIK' in html and 'Koreksi nilai' in html
    assert 'SIMULASI AKADEMIK — BUKAN DOKUMEN RESMI' in html
    assert 'Dihitung dalam IPK' in html
    assert '/static/images/logo_istn.png' in html
    pdf=render_transcript_pdf(t)
    assert pdf.startswith(b'%PDF-') and len(pdf)>1800
    base='/api/nilai/20240001/transkrip'
    assert client.get(base).status_code==403
    headers={'x-actor-role':'dosen','x-dosen-id':'110'}
    resp=client.get(base,headers=headers)
    assert resp.status_code==200 and resp.json()['total_sks_lulus']==7
    resp=client.get(base+'/html',headers=headers)
    assert resp.status_code==200 and 'text/html' in resp.headers['content-type']
    resp=client.get(base+'/pdf',headers=headers)
    assert resp.status_code==200 and resp.content.startswith(b'%PDF-')
    assert resp.headers['content-type'] == 'application/pdf'
    assert 'attachment' in resp.headers['content-disposition']
    assert client.get('/api/nilai/not-found/transkrip',headers=headers).status_code==404


def test_synthetic_sample_gpa_and_course_totals_are_consistent(monkeypatch):
    transcript = build_sample_transcript()

    assert transcript["program_studi"] == "Sistem Informasi"
    assert transcript["angkatan"] == "2025"
    assert transcript["angkatan_dari_nim"] is False
    assert [semester["semester"] for semester in transcript["semester"]] == [
        "20251",
        "20252",
    ]
    assert [semester["ips"] for semester in transcript["semester"]] == [
        "3.50",
        "3.50",
    ]
    assert transcript["ipk"] == "3.50"
    assert transcript["total_sks_lulus"] == 12
    assert sum(
        Decimal(course["mutu"])
        for semester in transcript["semester"]
        for course in semester["mata_kuliah"]
    ) == Decimal("42.00")
    assert sum(
        course["sks"]
        for semester in transcript["semester"]
        for course in semester["mata_kuliah"]
    ) == 12

    html = render_transcript_html(transcript)
    assert "Angkatan diperkirakan dari empat digit awal NIM" not in html
    _force_reportlab(monkeypatch)
    pdf_content = b"\n".join(
        _decoded_pdf_streams(render_transcript_pdf(transcript))
    )
    assert b"Angkatan diperkirakan dari empat digit awal NIM" not in pdf_content


def test_transcript_header_text_is_centered_in_html_and_reportlab(monkeypatch):
    from reportlab.lib.enums import TA_CENTER
    import app.services.transcript_pdf as transcript_pdf

    transcript = build_sample_transcript()
    html = render_transcript_html(transcript)
    header = html.split("<header>", 1)[1].split("</header>", 1)[0]
    header_text = re.search(
        r'<div class="header-text">(.*?)</div>',
        header,
        re.DOTALL,
    )
    assert header_text is not None
    assert all(text in header_text.group(1) for text in (
        "INSTITUT SAINS DAN TEKNOLOGI NASIONAL (ISTN)",
        "TRANSKRIP AKADEMIK",
        "SIMULASI AKADEMIK — BUKAN DOKUMEN RESMI",
    ))
    assert re.search(
        r"\.header-text\s*\{[^}]*text-align:\s*center;",
        html,
        re.DOTALL,
    )

    original_table = transcript_pdf.Table
    header_alignments = []

    def capture_header_table(data, *args, **kwargs):
        if (
            len(data) == 1
            and len(data[0]) == 2
            and isinstance(data[0][1], list)
            and len(data[0][1]) == 3
        ):
            header_alignments.extend(
                paragraph.style.alignment for paragraph in data[0][1]
            )
        return original_table(data, *args, **kwargs)

    _force_reportlab(monkeypatch)
    monkeypatch.setattr(transcript_pdf, "Table", capture_header_table)
    assert render_transcript_pdf(transcript).startswith(b"%PDF-")
    assert header_alignments == [TA_CENTER, TA_CENTER, TA_CENTER]


def test_istn_logo_is_served_as_original_transparent_png(client):
    response = client.get("/static/images/logo_istn.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert struct.unpack(">II", response.content[16:24]) == (768, 768)
    assert response.content[25] == 6


def test_reportlab_fallback_contains_transcript_content_and_logo(
    db_session, monkeypatch
):
    seed(db_session)
    transcript = TranscriptService(db_session).get_transcript("20240001")
    _force_reportlab(monkeypatch)

    pdf = render_transcript_pdf(transcript)
    content = b"\n".join(_decoded_pdf_streams(pdf))

    assert b"%PDF-" in pdf[:8]
    assert b"INSTITUT SAINS DAN TEKNOLOGI NASIONAL" in content
    assert b"TRANSKRIP AKADEMIK" in content
    assert b"SIMULASI AKADEMIK" in content
    assert b"Dihitung dalam IPK" in content
    assert b"/Subtype /Image" in pdf
    assert b"/SMask" in pdf
    assert len(re.findall(rb"/Type\s*/Page\b", pdf)) >= 1


def test_reportlab_fallback_paginates_long_transcript(monkeypatch):
    courses = [
        {
            "kode_mk": f"MK{index:03}",
            "nama_mk": f"Mata Kuliah Dengan Nama Panjang {index}",
            "sks": 3,
            "nilai": "A",
            "mutu": "12.00",
            "dihitung_ipk": True,
        }
        for index in range(1, 61)
    ]
    transcript = {
        "nim": "20990001",
        "nama": "Nama Mahasiswa Simulasi Yang Cukup Panjang",
        "program_studi": "Teknik Informatika",
        "fakultas": "Fakultas Sains dan Teknologi",
        "angkatan": "2099",
        "semester": [
            {
                "semester": f"2024{term}",
                "ips": "4.00",
                "mata_kuliah": courses[start:start + 20],
            }
            for term, start in enumerate((0, 20, 40), start=1)
        ],
        "total_sks_lulus": 180,
        "ipk": "4.00",
        "predikat": "Cum Laude (indikatif)",
        "catatan": "Simulasi akademik untuk verifikasi tata letak.",
        "riwayat_perubahan": [
            {
                "changed_at": f"2026-01-{day:02} 12:00:00",
                "kode_mk": f"MK{day:03}",
                "old_value": "B",
                "new_value": "A",
                "dosen_nama": "Dosen Simulasi",
                "reason": "Koreksi nilai untuk pengujian",
            }
            for day in range(1, 41)
        ],
    }
    _force_reportlab(monkeypatch)

    pdf = render_transcript_pdf(transcript)

    assert len(re.findall(rb"/Type\s*/Page\b", pdf)) >= 2


def test_no_grades_and_missing_student(db_session):
    seed(db_session, with_grades=False)
    t=TranscriptService(db_session).get_transcript('20240001')
    assert t['ipk']=='0.00' and t['total_sks_lulus']==0
    assert 'Belum tersedia' in t['predikat']
    assert TranscriptService(db_session).get_transcript('none') is None
    assert render_transcript_pdf(t).startswith(b'%PDF-')


@pytest.mark.parametrize('ipk,sks,expected', [
    ('4.00',7,'Cum Laude'),('3.50',7,'Cum Laude'),('3.49',7,'Sangat Memuaskan'),
    ('3.00',7,'Sangat Memuaskan'),('2.99',7,'Belum ditetapkan'),
    ('0.00',0,'Belum tersedia'),
])
def test_predikat_boundaries(ipk,sks,expected):
    assert expected in predikat(Decimal(ipk),sks)


def test_html_escaping():
    from app.services.transcript_pdf import render_transcript_html
    t={'nim':'123','nama':'<script>alert(1)</script>','program_studi':'SI',
       'fakultas':'F','angkatan':'2024','semester':[],'total_sks_lulus':0,
       'ipk':'0.00','predikat':'Belum tersedia','riwayat_perubahan':[], 'catatan':'uji'}
    assert '<script>' not in render_transcript_html(t)
    assert '&lt;script&gt;' in render_transcript_html(t)

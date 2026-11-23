from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    KeepTogether, Flowable
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from svglib.svglib import svg2rlg

ROOT = Path("docs/uml_final_uts")
OUTPUT = Path("artifacts/final_uts/LAPORAN_UML_FINAL_UTS_SIAKAD.pdf")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="JudulLaporan", parent=styles["Title"],
    fontSize=21, leading=28, spaceAfter=20,
    textColor=colors.HexColor("#17365D")
))
styles.add(ParagraphStyle(
    name="SubjudulLaporan", parent=styles["Heading2"],
    fontSize=13, leading=18, spaceBefore=14,
    spaceAfter=9, textColor=colors.HexColor("#17365D")
))
styles.add(ParagraphStyle(
    name="IsiLaporan", parent=styles["BodyText"],
    fontSize=10, leading=16, spaceAfter=9, alignment=TA_JUSTIFY
))
styles.add(ParagraphStyle(
    name="KeteranganLaporan", parent=styles["BodyText"],
    fontSize=9, leading=14, alignment=TA_CENTER,
    textColor=colors.grey
))

class SVGDiagram(Flowable):
    def __init__(self, filename, max_width, max_height):
        Flowable.__init__(self)
        self.drawing = svg2rlg(str(ROOT / filename))
        if self.drawing is None:
            raise ValueError(f"Gagal membaca {filename}")
        self.filename = filename
        self.scale = min(
            max_width / self.drawing.width,
            max_height / self.drawing.height
        )
        self.width = self.drawing.width * self.scale
        self.height = self.drawing.height * self.scale

    def draw(self):
        self.canv.saveState()
        self.canv.scale(self.scale, self.scale)
        self.drawing.drawOn(self.canv, 0, 0)
        self.canv.restoreState()

def p(text):
    return Paragraph(escape(text), styles["IsiLaporan"])

def heading(text):
    return Paragraph(escape(text), styles["SubjudulLaporan"])

def page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawRightString(280 * mm, 12 * mm, str(doc.page))
    canvas.restoreState()

PAGE = landscape(A4)
doc = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=PAGE,
    rightMargin=20*mm, leftMargin=20*mm,
    topMargin=18*mm, bottomMargin=20*mm,
    title="Laporan UML Final UTS SIAKAD",
    author="Muhamad Arkan Maulana - 251635002"
)

W = PAGE[0] - 40*mm
H = PAGE[1] - 38*mm
story = []

story.append(Spacer(1, 32*mm))
story.append(Paragraph(
    "LAPORAN FINAL UTS<br/>SISTEM INFORMASI AKADEMIK (SIAKAD)",
    styles["JudulLaporan"]
))
story.append(Spacer(1, 8*mm))
story.append(p("Fokus: Modul Penerimaan Mahasiswa Baru (PMB) dan Kartu Rencana Studi (KRS)"))
story.append(p("Dokumentasi Class Diagram, Use Case Diagram, Sequence Diagram, ADR, dan Penggunaan AI"))
story.append(Spacer(1, 12*mm))
story.append(p("Nama Mahasiswa : Muhamad Arkan Maulana"))
story.append(p("NIM : 251635002"))
story.append(p("Program Studi : Sistem Informasi"))
story.append(p("Dosen Pengajar : Akhmad Daniel Sembiring, ST., MT."))
story.append(PageBreak())

story.append(heading("1. Pendahuluan"))
story.append(p(
    "Laporan ini mendokumentasikan rancangan UML pada aplikasi SIAKAD, "
    "dengan fokus pada modul PMB dan KRS. Diagram disusun sebagai rekonstruksi "
    "dan penyelarasan berdasarkan implementasi Minggu 3 sampai Minggu 12, "
    "bukan sebagai klaim bahwa UML telah dibuat sebelum implementasi."
))
story.append(heading("2. Ringkasan Modul PMB"))
story.append(p(
    "PMB mencakup registrasi calon mahasiswa, validasi data, persetujuan "
    "atau penolakan pendaftar, penerbitan NIM, pemeriksaan status, "
    "dan statistik pendaftaran. Status persetujuan pada implementasi "
    "menggunakan nilai approve."
))
story.append(heading("3. Ringkasan Modul KRS"))
story.append(p(
    "KRS mencakup pengambilan mata kuliah, pemeriksaan duplikasi, batas "
    "24 SKS, prasyarat, bentrok jadwal, pengajuan, persetujuan, dan revisi. "
    "Proses validasi menggunakan Chain of Responsibility, sedangkan "
    "perubahan status menggunakan aturan transisi dan transaksi database."
))
story.append(heading("4. Pendekatan Dokumentasi"))
story.append(p(
    "Diagram PlantUML dirender menjadi SVG dan diperiksa agar selaras "
    "dengan struktur model, router, service, dan validator. Beberapa "
    "aktor pada Use Case merupakan representasi proses bisnis, bukan "
    "bukti bahwa autentikasi produksi sudah tersedia."
))
story.append(PageBreak())

diagrams = [
    (
        "5. Class Diagram PMB dan KRS",
        "CLASS_DIAGRAM_PMB_KRS.svg",
        "Memperlihatkan model PMB dan KRS, hubungan data, layanan, "
        "serta komponen validator. PMBService digambarkan secara "
        "konseptual karena implementasinya menggunakan fungsi layanan."
    ),
    (
        "6. Use Case Diagram PMB dan KRS",
        "USE_CASE_PMB_KRS.svg",
        "Memperlihatkan interaksi Calon Mahasiswa, Admin PMB, "
        "Mahasiswa, dan Dosen PA dengan fungsi utama sistem."
    ),
    (
        "7. Sequence Diagram PMB",
        "SEQUENCE_PMB.svg",
        "Menjelaskan alur registrasi, pemeriksaan email dan referensi, "
        "persetujuan pendaftar, serta penerbitan NIM."
    ),
    (
        "8. Sequence Diagram KRS",
        "SEQUENCE_KRS.svg",
        "Menjelaskan penambahan mata kuliah, validasi, pengajuan, "
        "persetujuan, pemeriksaan versi, dan pencatatan transaksi."
    ),
]

for title, filename, description in diagrams:
    story.append(heading(title))
    story.append(p(description))
    story.append(Spacer(1, 4*mm))
    story.append(SVGDiagram(filename, W, H - 44*mm))
    story.append(PageBreak())

story.append(heading("9. Architecture Decision Record (ADR)"))
story.append(p(
    "ADR-001: Validasi KRS menggunakan Chain of Responsibility "
    "dengan urutan Duplicate, SKS, Prerequisite, dan Conflict. "
    "Pemisahan validator membantu pengujian serta pemeliharaan."
))
story.append(p(
    "ADR-002: Pengelolaan KRS menggunakan state machine dengan status "
    "draft, submitted, approved, dan revision. Pemeriksaan versi "
    "dan transaksi database digunakan untuk menjaga konsistensi "
    "perubahan status, audit log, serta notifikasi database."
))
story.append(heading("10. Dokumentasi Penggunaan AI"))
story.append(p(
    "ChatGPT digunakan sebagai alat bantu analisis kebutuhan, "
    "pengembangan PMB dan KRS, penyusunan PlantUML, serta dokumentasi. "
    "Prompt, revisi manual, dan pengujian historis dicatat dalam "
    "AI_USAGE_LOG.md serta AI_USAGE_LOG_FINAL_UTS.md."
))
story.append(p(
    "Pengujian regresi pada salinan proyek UTS sebelumnya "
    "menghasilkan 195 tes lulus dan satu deprecation warning."
))
story.append(heading("11. Keterbatasan"))
story.append(p(
    "Identitas aktor KRS masih disimulasikan melalui header API, "
    "notifikasi dicatat pada database, dan pengujian SQLite belum "
    "membuktikan perilaku concurrency multi-worker pada MySQL."
))
story.append(heading("12. Kesimpulan"))
story.append(p(
    "Keempat diagram UML mendokumentasikan struktur, aktor, "
    "dan alur utama PMB serta KRS. ADR dan AI Usage Log "
    "menjadi bukti pendukung keputusan desain dan proses pengembangan."
))

# Hapus PageBreak terakhir apabila ada.
while story and isinstance(story[-1], PageBreak):
    story.pop()

doc.build(story, onFirstPage=page_number, onLaterPages=page_number)

print("========== PDF BERHASIL DIBUAT ==========")
print(OUTPUT.resolve())
print(f"Ukuran: {OUTPUT.stat().st_size:,} byte")


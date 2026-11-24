from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4, A3
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
from PIL import Image

BASE = Path("docs/uml_final_uts")
# Legacy report generator.
# Does not reproduce the revised Final UTS PDF.
# Output is separated to protect approved documents.
OUTPUT = Path("artifacts/generated/LAPORAN_UML_PROFESIONAL_LEGACY.pdf")
LOGO = Path("app/static/images/logo_istn.png")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

pdfmetrics.registerFont(TTFont("ArialCustom", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("ArialBoldCustom", "C:/Windows/Fonts/arialbd.ttf"))
pdfmetrics.registerFontFamily(
    "ArialCustom",
    normal="ArialCustom",
    bold="ArialBoldCustom"
)

NAVY = colors.HexColor("#17365D")
BLUE = colors.HexColor("#27659A")
GRAY = colors.HexColor("#526173")
LIGHT = colors.HexColor("#EAF1F7")
INK = colors.HexColor("#202C39")
WHITE = colors.white

c = canvas.Canvas(str(OUTPUT), pagesize=A4)
c.setTitle("Laporan Final UTS SIAKAD - PMB dan KRS")
c.setAuthor("Muhamad Arkan Maulana - 251635002")

PAGE_NO = 0
W, H = A4
MARGIN = 23 * mm
CONTENT_W = W - 2 * MARGIN
y = 0

BODY = ParagraphStyle(
    "body", fontName="ArialCustom",
    fontSize=10.2, leading=17,
    alignment=TA_JUSTIFY,
    textColor=INK,
    spaceAfter=8
)

SMALL = ParagraphStyle(
    "small", parent=BODY,
    fontSize=9.3, leading=15
)

def header_footer(section="Laporan Final UTS SIAKAD"):
    c.setStrokeColor(colors.HexColor("#D4DEE8"))
    c.setLineWidth(0.6)
    c.line(MARGIN, H - 20*mm, W-MARGIN, H-20*mm)
    c.setFont("ArialBoldCustom", 8)
    c.setFillColor(NAVY)
    c.drawString(MARGIN, H-16.5*mm, "ISTN  |  SISTEM INFORMASI")
    c.setFont("ArialCustom", 8)
    c.setFillColor(GRAY)
    c.drawRightString(W-MARGIN, H-16.5*mm, section[:65])
    c.line(MARGIN, 17*mm, W-MARGIN, 17*mm)
    c.drawString(MARGIN, 12*mm, "Muhamad Arkan Maulana  |  251635002")
    c.drawRightString(W-MARGIN, 12*mm, f"Halaman {PAGE_NO}")

def new_page(size=A4, section="Laporan Final UTS SIAKAD"):
    global W, H, y, PAGE_NO
    if PAGE_NO:
        c.showPage()
    PAGE_NO += 1
    W, H = size
    c.setPageSize(size)
    header_footer(section)
    y = H - 31*mm

def paragraph(text, style=BODY):
    global y
    content = escape(text)
    p = Paragraph(content, style)
    _, ph = p.wrap(CONTENT_W, H)
    if y - ph < 27*mm:
        new_page(A4)
    p.drawOn(c, MARGIN, y-ph)
    y -= ph + 9*mm

def heading(text, level=1):
    global y
    gap = 15*mm if level == 1 else 11*mm
    if y < 49*mm:
        new_page(A4)
    y -= 5*mm
    c.setFillColor(NAVY if level == 1 else BLUE)
    c.setFont("ArialBoldCustom", 14 if level == 1 else 11.5)
    c.drawString(MARGIN, y, text)
    y -= gap

def section(title, paragraphs):
    heading(title)
    for item in paragraphs:
        paragraph(item)

def caption(text):
    global y
    y -= 3*mm
    c.setFont("ArialCustom", 8.7)
    c.setFillColor(GRAY)
    c.drawCentredString(W/2, y, text)
    y -= 9*mm

def draw_diagram(filename, title, description, part=None):
    global y
    d = svg2rlg(str(BASE / filename))
    if d is None:
        raise ValueError(f"Diagram gagal dibaca: {filename}")

    new_page(A3, title)
    heading(title)
    paragraph(description, SMALL)

    top = y - 5*mm
    bottom = 30*mm
    usable_h = top-bottom
    usable_w = W-2*28*mm

    if part is None:
        scale = min(usable_w/d.width, usable_h/d.height)
        dw, dh = d.width*scale, d.height*scale
        x = (W-dw)/2
        image_bottom = bottom+(usable_h-dh)/2

        c.saveState()
        c.translate(x, image_bottom)
        c.scale(scale, scale)
        renderPDF.draw(d, c, 0, 0)
        c.restoreState()
    else:
        # Bagian atas dan bawah diagram dipisahkan tanpa mengubah SVG.
        scale = usable_w/d.width
        dw, dh = d.width*scale, d.height*scale
        segment_h = dh/2
        if segment_h > usable_h:
            scale *= usable_h/segment_h
            dw, dh = d.width*scale, d.height*scale
            segment_h = dh/2

        x = (W-dw)/2
        clip_bottom = bottom+(usable_h-segment_h)/2

        c.saveState()
        path = c.beginPath()
        path.rect(x, clip_bottom, dw, segment_h)
        c.clipPath(path, stroke=0, fill=0)

        # part=0 menampilkan setengah atas; part=1 setengah bawah.
        offset = -segment_h if part == 0 else 0
        c.translate(x, clip_bottom+offset)
        c.scale(scale, scale)
        renderPDF.draw(d, c, 0, 0)
        c.restoreState()

    c.setFillColor(GRAY)
    c.setFont("ArialCustom", 8.5)
    c.drawCentredString(
        W/2, 24*mm,
        "Sumber: Diagram PlantUML berdasarkan implementasi proyek SIAKAD"
    )

# ===================== SAMPUL =====================

new_page(A4, "Sampul")
c.setFillColor(NAVY)
c.rect(0, H-13*mm, W, 13*mm, fill=1, stroke=0)

if LOGO.exists():
    c.drawImage(
        str(LOGO),
        W/2-28*mm, H-76*mm,
        width=56*mm, height=56*mm,
        preserveAspectRatio=True, mask="auto"
    )

c.setFillColor(NAVY)
c.setFont("ArialBoldCustom", 17)
c.drawCentredString(W/2, H-98*mm, "LAPORAN FINAL UTS")

c.setFont("ArialBoldCustom", 15)
c.drawCentredString(W/2, H-109*mm, "SISTEM INFORMASI AKADEMIK")

c.setFont("ArialBoldCustom", 14)
c.drawCentredString(W/2, H-119*mm, "(SIAKAD)")

c.setStrokeColor(BLUE)
c.setLineWidth(2)
c.line(48*mm, H-127*mm, W-48*mm, H-127*mm)

c.setFillColor(GRAY)
c.setFont("ArialCustom", 10.5)
c.drawCentredString(W/2, H-139*mm, "Perancangan UML Modul PMB dan KRS")

identity = [
    ("Disusun oleh", "Muhamad Arkan Maulana"),
    ("Nomor Induk Mahasiswa", "251635002"),
    ("Program Studi", "Sistem Informasi"),
    ("Dosen Pengajar", "Akhmad Daniel Sembiring, ST., MT.")
]

iy = H-163*mm
for label, value in identity:
    c.setFont("ArialCustom", 9)
    c.setFillColor(GRAY)
    c.drawCentredString(W/2, iy, label.upper())
    c.setFont("ArialBoldCustom", 11)
    c.setFillColor(INK)
    c.drawCentredString(W/2, iy-6*mm, value)
    iy -= 18*mm

c.setFillColor(NAVY)
c.setFont("ArialBoldCustom", 10)
c.drawCentredString(W/2, 43*mm, "INSTITUT SAINS DAN TEKNOLOGI NASIONAL")
c.setFont("ArialCustom", 9)
c.drawCentredString(W/2, 36*mm, "PROGRAM STUDI SISTEM INFORMASI")
c.drawCentredString(W/2, 29*mm, "2026")

# ===================== ISI =====================

new_page(A4, "Pendahuluan")

section("BAB I  PENDAHULUAN", [
    "Sistem Informasi Akademik (SIAKAD) merupakan aplikasi yang mendukung proses administrasi dan kegiatan akademik perguruan tinggi. Dalam proyek ini, dua modul yang menjadi fokus pembahasan adalah Penerimaan Mahasiswa Baru (PMB) dan Kartu Rencana Studi (KRS). Kedua modul tersebut saling berkaitan karena data calon mahasiswa yang telah disetujui dan memperoleh NIM dapat menjadi dasar identifikasi mahasiswa pada proses akademik berikutnya.",
    "Pengembangan aplikasi dilakukan secara bertahap melalui implementasi API, model database, aturan bisnis, pengujian, serta dokumentasi keputusan arsitektur. Laporan ini menyajikan dokumentasi UML yang direkonstruksi dan diselaraskan dengan implementasi proyek Minggu 3 sampai Minggu 12. Dengan demikian, diagram yang disajikan menggambarkan sistem yang telah dikembangkan, bukan mengklaim bahwa seluruh diagram telah dibuat sebelum proses implementasi."
])

section("1.1 Tujuan Perancangan", [
    "Tujuan penyusunan laporan ini adalah menjelaskan struktur kelas dan hubungan antardata, mengidentifikasi interaksi aktor dengan sistem, serta menggambarkan urutan komunikasi antar komponen ketika proses PMB dan KRS dijalankan. Dokumentasi ini juga bertujuan memperjelas alasan pemilihan pola desain, mekanisme validasi, pengelolaan status, dan pengendalian konsistensi data.",
    "Melalui Class Diagram, Use Case Diagram, dan Sequence Diagram, rancangan sistem diharapkan dapat dibaca secara lebih sistematis oleh pengembang maupun penguji. Diagram digunakan sebagai sarana komunikasi teknis yang melengkapi kode sumber dan hasil pengujian."
])

section("1.2 Ruang Lingkup", [
    "Pembahasan dibatasi pada registrasi calon mahasiswa, validasi data pendaftar, persetujuan atau penolakan PMB, pembentukan NIM, pengelolaan mata kuliah KRS, validasi prasyarat akademik, pengajuan KRS, serta persetujuan dan revisi oleh Dosen Pembimbing Akademik. Modul lain pada aplikasi SIAKAD tidak dibahas secara mendalam.",
    "Representasi aktor Admin PMB dan Dosen PA dalam diagram menjelaskan peran pada proses bisnis. Implementasi API yang dibahas belum dapat dianggap sebagai sistem autentikasi produksi yang lengkap."
])

section("BAB II  GAMBARAN UMUM SISTEM", [
    "Aplikasi dikembangkan menggunakan FastAPI untuk menyediakan endpoint REST, SQLAlchemy untuk pemetaan model database, dan Pydantic untuk validasi skema masukan serta keluaran. Pada lingkungan pengembangan, SQLite digunakan sebagai basis data. Pemisahan router, service, model, dan schema membantu membedakan tanggung jawab antarkomponen.",
    "Lapisan router menerima permintaan HTTP dan mengembalikan respons. Lapisan service menjalankan aturan bisnis, sedangkan model mengelola representasi data yang disimpan pada database. Pada modul KRS, komponen validator dipisahkan agar aturan akademik dapat diperiksa secara berurutan."
])

section("2.1 Modul Penerimaan Mahasiswa Baru", [
    "Modul PMB menerima data calon mahasiswa yang meliputi identitas, email, nomor telepon, program studi, dan jalur masuk. Saat registrasi, sistem memeriksa keunikan email serta validitas referensi program studi dan jalur masuk. Data yang lolos pemeriksaan disimpan dengan status awal pending.",
    "Petugas dapat menjalankan proses persetujuan atau penolakan pendaftaran. Ketika pendaftar disetujui, sistem membentuk NIM menggunakan tahun, kode program studi, dan nomor urut yang dikelola melalui NIMCounter. Proses persetujuan memperhatikan konsistensi transaksi dan idempotensi agar permintaan berulang tidak menghasilkan NIM baru untuk pendaftar yang sama.",
    "Nilai status pada implementasi PMB adalah pending, approve, dan rejected. Penulisan approve merupakan nilai aktual yang digunakan dalam kode, bukan approved."
])

section("2.2 Modul Kartu Rencana Studi", [
    "Modul KRS memungkinkan mahasiswa menambahkan atau menghapus mata kuliah, memeriksa validitas rencana studi, mengajukan KRS, dan melihat detailnya. Persetujuan atau revisi dilakukan melalui proses yang merepresentasikan peran Dosen Pembimbing Akademik.",
    "Validasi KRS mencakup pemeriksaan mata kuliah duplikat, batas maksimal 24 SKS, pemenuhan prasyarat berdasarkan riwayat akademik, dan bentrok jadwal. Pemeriksaan tersebut dijalankan melalui rangkaian validator yang terpisah sehingga setiap aturan dapat diuji secara mandiri.",
    "Status KRS terdiri atas draft, submitted, approved, dan revision. Pengubahan status dilakukan dengan aturan transisi tertentu. Sistem juga menggunakan pemeriksaan versi untuk mengurangi risiko perubahan bersamaan dan mencatat riwayat aktivitas serta notifikasi dalam database."
])

section("BAB III  PERANCANGAN UML", [
    "Unified Modeling Language (UML) digunakan untuk mendokumentasikan struktur statis dan perilaku dinamis sistem. Class Diagram menjelaskan komponen data dan relasinya, Use Case Diagram menggambarkan interaksi aktor dengan fungsi aplikasi, sedangkan Sequence Diagram memperlihatkan urutan komunikasi pada skenario tertentu.",
    "Keempat diagram pada halaman berikut berasal dari berkas PlantUML proyek. Diagram ditampilkan pada halaman yang lebih besar agar hubungan, pesan, dan keterangan teknis tetap dapat diperiksa."
])

# ===================== DIAGRAM =====================

draw_diagram(
    "CLASS_DIAGRAM_PMB_KRS.svg",
    "3.1 Class Diagram PMB dan KRS",
    "Struktur model data, hubungan antarkelas, service, dan validator."
)

new_page(A4, "Analisis Class Diagram")
section("3.1.1 Analisis Class Diagram", [
    "Bagian PMB menampilkan CalonMahasiswa sebagai entitas utama yang berhubungan dengan ProgramStudi dan JalurMasuk. Relasi tersebut menggambarkan bahwa satu program studi atau satu jalur masuk dapat digunakan oleh banyak calon mahasiswa. NIMCounter berperan dalam pengelolaan nomor urut NIM berdasarkan tahun dan kode program studi.",
    "Bagian KRS menampilkan KRS, KRSDetail, MataKuliah, SkalaNilai, KRSLog, dan KRSNotification. Satu KRS dapat memiliki beberapa detail mata kuliah, sedangkan catatan aktivitas dan notifikasi disimpan sebagai data pendukung proses akademik.",
    "KRSManager merupakan kelas layanan yang menjalankan operasi pengelolaan KRS. Rangkaian DuplicateValidator, SKSValidator, PrerequisiteValidator, dan ConflictValidator memperlihatkan penerapan Chain of Responsibility. Sebaliknya, PMBService dalam diagram adalah representasi konseptual dari fungsi-fungsi pada pmb_service.py, bukan kelas Python aktual."
])

draw_diagram(
    "USE_CASE_PMB_KRS.svg",
    "3.2 Use Case Diagram PMB dan KRS",
    "Interaksi aktor dengan fitur utama sistem PMB dan KRS."
)

new_page(A4, "Analisis Use Case")
section("3.2.1 Analisis Use Case Diagram", [
    "Aktor Calon Mahasiswa berinteraksi dengan proses registrasi dan pemeriksaan status PMB. Admin PMB direpresentasikan sebagai peran yang menangani persetujuan, penolakan, serta pemeriksaan statistik pendaftaran. Penerbitan NIM merupakan bagian dari proses persetujuan pendaftar.",
    "Pada modul KRS, aktor Mahasiswa menggunakan fitur penambahan dan penghapusan mata kuliah, validasi, pengajuan, serta pemeriksaan detail KRS. Dosen PA menangani persetujuan dan permintaan revisi. Relasi include pada diagram digunakan untuk menunjukkan proses validasi yang diperlukan dalam alur tertentu.",
    "Perlu dibedakan antara aktor konseptual pada UML dan mekanisme otorisasi yang telah tersedia dalam kode. Identitas aktor pada sebagian endpoint KRS masih disimulasikan melalui header permintaan API."
])

draw_diagram(
    "SEQUENCE_PMB.svg",
    "3.3 Sequence Diagram PMB",
    "Urutan interaksi pada registrasi dan persetujuan calon mahasiswa."
)

new_page(A4, "Analisis Sequence PMB")
section("3.3.1 Analisis Sequence Diagram PMB", [
    "Alur registrasi dimulai ketika calon mahasiswa mengirim permintaan POST ke endpoint pendaftaran. Router meneruskan data ke fungsi layanan, kemudian sistem memeriksa email dan referensi program studi serta jalur masuk. Email yang sudah digunakan menghasilkan respons konflik, sedangkan referensi yang tidak valid menghasilkan respons kesalahan permintaan.",
    "Jika seluruh pemeriksaan berhasil, data pendaftar disimpan dengan status pending dan sistem mengembalikan respons HTTP 201 Created. Pada alur persetujuan, layanan memeriksa keberadaan pendaftar dan statusnya sebelum melakukan perubahan data.",
    "Pendaftar yang telah berstatus approve dapat memperoleh hasil persetujuan yang sama ketika permintaan diulang. Untuk pendaftar pending, sistem menerbitkan NIM dan memperbarui status serta waktu persetujuan dalam transaksi database. Mekanisme ini dirancang untuk menjaga konsistensi data."
])

draw_diagram(
    "SEQUENCE_KRS.svg",
    "3.4 Sequence Diagram KRS — Bagian 1",
    "Bagian pertama: penambahan mata kuliah dan awal proses pengajuan.",
    part=0
)

draw_diagram(
    "SEQUENCE_KRS.svg",
    "3.4 Sequence Diagram KRS — Bagian 2",
    "Bagian kedua: kelanjutan pengajuan dan persetujuan oleh Dosen PA.",
    part=1
)

new_page(A4, "Analisis Sequence KRS")
section("3.4.1 Analisis Sequence Diagram KRS", [
    "Alur KRS dimulai ketika mahasiswa mengirim permintaan untuk menambahkan mata kuliah. KRSManager memeriksa keberadaan mahasiswa dan mata kuliah, status KRS, serta persyaratan lain yang relevan. Selanjutnya, validator memeriksa kemungkinan duplikasi, batas SKS, prasyarat, dan konflik jadwal sebelum perubahan disimpan.",
    "Ketika mahasiswa mengajukan KRS, sistem memeriksa kepemilikan, status, kewajiban keuangan, serta versi data. Validasi seluruh mata kuliah dilakukan kembali sebelum status diubah dari draft atau revision menjadi submitted.",
    "Pada tahap persetujuan, sistem memeriksa peran Dosen PA, versi data, dan status KRS. Jika persyaratan terpenuhi, status berubah menjadi approved. Perubahan tersebut disertai pencatatan log dan notifikasi database. Diagram juga memperlihatkan jalur kesalahan ketika validasi atau pemeriksaan kewenangan tidak berhasil."
])

section("BAB IV  KEPUTUSAN ARSITEKTUR (ADR)", [
    "Keputusan arsitektur pertama adalah penggunaan Chain of Responsibility pada validasi KRS. Setiap validator menangani satu jenis aturan dan dapat meneruskan pemeriksaan ke validator berikutnya. Pendekatan ini mengurangi penumpukan logika dalam satu fungsi besar, meningkatkan keterbacaan, dan memudahkan pengujian unit.",
    "Keputusan kedua adalah pengelolaan status KRS menggunakan state machine, transaksi database, dan pemeriksaan versi. Pendekatan ini bertujuan mencegah perubahan status yang tidak sah serta mengurangi risiko kehilangan pembaruan ketika beberapa permintaan memodifikasi data yang sama.",
    "Konsekuensi dari keputusan tersebut adalah meningkatnya kebutuhan pengujian terhadap kombinasi status, validasi, dan perubahan bersamaan. Implementasi SQLite yang diuji dalam lingkungan pengembangan belum otomatis membuktikan keamanan transaksi pada seluruh konfigurasi database produksi."
])

section("BAB V  PENGGUNAAN AI DAN PENGUJIAN", [
    "ChatGPT digunakan sebagai alat bantu dalam memahami kebutuhan, menyusun alternatif rancangan, mengembangkan dan meninjau implementasi, serta mendokumentasikan UML. Penggunaan AI tidak menggantikan pemeriksaan terhadap kode sumber dan hasil pengujian. Riwayat bantuan AI didokumentasikan dalam AI_USAGE_LOG.md dan dokumen AI Usage Log Final UTS.",
    "Dalam pengembangan PMB, bantuan AI mencakup pembahasan validasi pendaftaran, keunikan email, penerbitan NIM, idempotensi, dan pengendalian transaksi. Pada modul KRS, pembahasan mencakup aturan akademik, Chain of Responsibility, pengelolaan status, optimistic locking, serta pencatatan perubahan.",
    "Pengujian regresi pada salinan proyek Final UTS sebelumnya menghasilkan 195 pengujian lulus dengan satu peringatan deprecation. Hasil tersebut menunjukkan bahwa rangkaian pengujian yang dijalankan berhasil, tetapi tidak boleh ditafsirkan sebagai jaminan bahwa seluruh kemungkinan kegagalan produksi telah tercakup."
])

section("5.1 Keterbatasan Implementasi", [
    "Mekanisme identitas aktor KRS masih menggunakan header API untuk simulasi, sehingga belum setara dengan autentikasi dan otorisasi produksi. Notifikasi yang dibahas merupakan pencatatan dalam database dan bukan bukti pengiriman email eksternal.",
    "Pengujian pada SQLite juga belum membuktikan perilaku transaksi dalam skenario MySQL multi-worker. Selain itu, dokumentasi UML ini merupakan penyelarasan terhadap implementasi yang telah ada sehingga tetap memerlukan pemeliharaan apabila kode sumber mengalami perubahan."
])

section("BAB VI  KESIMPULAN", [
    "Perancangan UML membantu menjelaskan hubungan antara model data, peran pengguna, layanan, dan alur pemrosesan pada modul PMB dan KRS. Class Diagram menggambarkan struktur komponen, Use Case Diagram menjelaskan kebutuhan interaksi, dan Sequence Diagram memperlihatkan tahapan komunikasi serta kondisi keberhasilan maupun kegagalan.",
    "Penggunaan Chain of Responsibility, aturan transisi status, transaksi database, dan pemeriksaan versi menunjukkan upaya menjaga keteraturan logika bisnis dan konsistensi data. Dokumentasi ADR, AI Usage Log, dan hasil pengujian melengkapi diagram sebagai bukti proses pengembangan sistem.",
    "Secara keseluruhan, laporan ini memberikan gambaran teknis yang terstruktur mengenai implementasi SIAKAD pada modul PMB dan KRS, sekaligus menjelaskan batasan yang masih perlu diperhatikan dalam pengembangan berikutnya."
])

section("REFERENSI DOKUMENTASI PROYEK", [
    "1. docs/uml_final_uts/CLASS_DIAGRAM_PMB_KRS.puml",
    "2. docs/uml_final_uts/USE_CASE_PMB_KRS.puml",
    "3. docs/uml_final_uts/SEQUENCE_PMB.puml",
    "4. docs/uml_final_uts/SEQUENCE_KRS.puml",
    "5. docs/ADR-001-krs-validation.md dan docs/ADR-002-krs-state-transactions.md",
    "6. docs/uml_final_uts/ADR_FINAL_UTS.md",
    "7. AI_USAGE_LOG.md dan docs/uml_final_uts/AI_USAGE_LOG_FINAL_UTS.md"
])

c.save()

print("========== PDF PROFESIONAL BERHASIL DIBUAT ==========")
print("File:", OUTPUT.resolve())
print("Ukuran:", f"{OUTPUT.stat().st_size:,}", "byte")
print("Jumlah halaman:", PAGE_NO)

from pypdf import PdfReader
reader = PdfReader(str(OUTPUT))
print("Verifikasi pypdf:", len(reader.pages), "halaman")
print("Ukuran halaman:", sorted({
    (round(float(p.mediabox.width)), round(float(p.mediabox.height)))
    for p in reader.pages
}))

from pathlib import Path
from reportlab.lib.pagesizes import landscape, A4

pdf = Path("artifacts/final_uts/LAPORAN_UML_FINAL_UTS_SIAKAD.pdf")

print("========== INFORMASI FILE ==========")
print("File:", pdf.name)
print("Ukuran:", pdf.stat().st_size, "byte")

try:
    from pypdf import PdfReader
except ImportError:
    print("\npypdf belum terpasang.")
    print("Jalankan instalasi pada langkah berikutnya.")
    raise SystemExit(0)

reader = PdfReader(str(pdf))
print("Jumlah halaman:", len(reader.pages))

keywords = [
    "Class Diagram",
    "Use Case",
    "Sequence Diagram PMB",
    "Sequence Diagram KRS",
    "Architecture Decision Record",
    "Dokumentasi Penggunaan AI",
]

print("\n========== PEMERIKSAAN HALAMAN ==========")

all_text = ""

for index, page in enumerate(reader.pages, start=1):
    content = page.extract_text() or ""
    all_text += content + "\n"

    width = float(page.mediabox.width)
    height = float(page.mediabox.height)

    print(
        f"Halaman {index}: "
        f"{width:.0f} x {height:.0f} pt | "
        f"{len(content)} karakter teks"
    )

print("\n========== PEMERIKSAAN BAGIAN ==========")

for keyword in keywords:
    status = "DITEMUKAN" if keyword.lower() in all_text.lower() else "BELUM DITEMUKAN"
    print(f"{keyword}: {status}")

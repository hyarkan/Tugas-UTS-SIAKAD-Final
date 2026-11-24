from pathlib import Path
import hashlib

try:
    from pypdf import PdfReader
except ImportError:
    print("ERROR: pypdf belum terpasang.")
    raise SystemExit(1)

ROOT = Path(__file__).resolve().parents[1]

DOCUMENTS = [
    {
        "name": "Laporan UML Final UTS",
        "path": ROOT / "artifacts/final_uts/LAPORAN_UML_FINAL_UTS_SIAKAD.pdf",
        "pages": 16,
        "sha256": "F5C4B5D3CED79CED158969789924894DDD10E2FCAC0600FDCD542486535337AB",
        "keywords": [
            "PMB",
            "KRS",
            "Class Diagram",
            "Use Case",
            "Sequence",
            "ADR",
        ],
    },
    {
        "name": "ADR Final UTS",
        "path": ROOT / "artifacts/final_uts/ADR_FINAL_UTS_SIAKAD.pdf",
        "pages": 5,
        "sha256": "149E6E3A5C0635F78B6860FA29CC066F25754D3EAFAC78D7EAB0EFFF787FE219",
        "keywords": [
            "PMB",
            "KRS",
            "SOLID",
            "Chain of Responsibility",
            "State Machine",
        ],
    },
]

errors = []

for document in DOCUMENTS:
    path = document["path"]

    print("\n" + "=" * 60)
    print(document["name"].upper())
    print("=" * 60)

    if not path.is_file():
        errors.append(f"File tidak ditemukan: {path.name}")
        continue

    print("File:", path.name)
    print("Ukuran:", f"{path.stat().st_size:,}", "byte")

    actual_hash = hashlib.sha256(
        path.read_bytes()
    ).hexdigest().upper()

    hash_valid = actual_hash == document["sha256"]

    print("SHA256:", actual_hash)
    print("Integritas:", "PASS" if hash_valid else "FAIL")

    if not hash_valid:
        errors.append(f"Hash berbeda: {path.name}")

    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)

        print("Jumlah halaman:", page_count)
        print("Target halaman:", document["pages"])

        if page_count != document["pages"]:
            errors.append(f"Jumlah halaman berbeda: {path.name}")

        all_text = []

        print("\nPEMERIKSAAN SETIAP HALAMAN")

        for index, page in enumerate(reader.pages, start=1):
            content = page.extract_text() or ""

            width = float(page.mediabox.width)
            height = float(page.mediabox.height)

            all_text.append(content)

            print(
                f"Halaman {index:02d}: "
                f"{width:.0f} x {height:.0f} pt | "
                f"{len(content)} karakter teks"
            )

        normalized = " ".join(
            " ".join(all_text).casefold().split()
        )

        if not normalized:
            errors.append(f"Teks tidak terbaca: {path.name}")

        print("\nPEMERIKSAAN KATA KUNCI")

        for keyword in document["keywords"]:
            found = keyword.casefold() in normalized

            print(
                f"{keyword}: "
                f"{'DITEMUKAN' if found else 'TIDAK DITEMUKAN'}"
            )

            if not found:
                errors.append(
                    f"{path.name}: kata kunci {keyword} tidak ditemukan"
                )

    except Exception as exc:
        errors.append(f"Gagal membaca {path.name}: {exc}")

print("\n" + "=" * 60)
print("RINGKASAN AUDIT FINAL UTS")
print("=" * 60)

if errors:
    for error in errors:
        print("FAIL:", error)

    print("\nSTATUS: AUDIT GAGAL")
    raise SystemExit(1)

print("PASS: Laporan UML Final UTS - 16 halaman")
print("PASS: ADR Final UTS - 5 halaman")
print("PASS: Integritas SHA256 kedua PDF")
print("PASS: Pemeriksaan kata kunci utama")
print("\nSTATUS: SELURUH AUDIT BERHASIL")

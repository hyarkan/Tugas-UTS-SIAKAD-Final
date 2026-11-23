from pathlib import Path
from svglib.svglib import svg2rlg

base = Path("docs/uml_final_uts")

diagrams = [
    "CLASS_DIAGRAM_PMB_KRS.svg",
    "USE_CASE_PMB_KRS.svg",
    "SEQUENCE_PMB.svg",
    "SEQUENCE_KRS.svg",
]

print("========== VALIDASI SVG UNTUK PDF ==========")

all_ok = True

for filename in diagrams:
    path = base / filename

    try:
        drawing = svg2rlg(str(path))

        if drawing is None:
            raise ValueError("SVG tidak menghasilkan drawing")

        print(
            f"[OK] {filename} | "
            f"{drawing.width:.0f} x {drawing.height:.0f} pt"
        )

    except Exception as error:
        all_ok = False
        print(f"[GAGAL] {filename}: {error}")

print("\n========== HASIL ==========")

if all_ok:
    print("SEMUA DIAGRAM BERHASIL DIBACA")
    print("Siap melanjutkan pembuatan PDF.")
else:
    print("ADA DIAGRAM YANG PERLU DIPERBAIKI")

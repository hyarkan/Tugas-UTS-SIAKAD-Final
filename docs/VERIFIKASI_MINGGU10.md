# Verifikasi Minggu 10

- Uji baru: `python -m pytest -q tests/test_transcript_week10.py` → **10 passed**.
- Uji regresi yang dapat dijalankan pada lingkungan ini: `python -m pytest -q --ignore=tests/test_grades_week9.py --ignore=tests/test_krs_properties.py --ignore=tests/test_scheduling_properties.py` → **110 passed** (termasuk 10 uji baru).
- Uji lengkap **belum dapat dijalankan di lingkungan pembuatan** karena paket `hypothesis` tidak tersedia dan jaringan instalasi tidak aktif. File `requirements.txt` tetap mencantumkan `hypothesis` agar pengujian lengkap bisa dijalankan setelah instalasi di Windows.
- PDF diawali signature `%PDF-` dan endpoint pengunduhan teruji. Validasi visual dan konfigurasi logo resmi harus dilakukan setelah ada aset institusi.
- Migrasi lama tetap tersedia; fitur Minggu 10 tidak mengubah skema database.

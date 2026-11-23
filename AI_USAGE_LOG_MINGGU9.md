# AI Usage Log — Minggu 9

- **Tujuan:** melanjutkan proyek Minggu 8 untuk grade management, IPS/IPK, audit, dan test.
- **Input:** ZIP proyek Minggu 8, transkrip penjelasan dosen, PDF Minggu 9–10, gambar checklist.
- **Bantuan AI:** rancangan migrasi, model, pure function Decimal, repository/service/API, form demo, tests, dokumentasi.
- **Verifikasi manusia:** konfirmasi definisi lulus dan skala huruf pada stakeholder; uji dengan data dummy dan review keamanan sebelum produksi.
- **Revisi kritis:** hindari float/round, jangan menghitung SKS ulang dua kali untuk MK diulang, jangan percaya header sebagai login, jangan mengasumsikan presensi tersedia.
- **Batasan:** fitur transkrip PDF Minggu 10 belum dikerjakan; autentikasi produksi dan modul presensi belum tersedia.

## Verifikasi dan Revisi Lanjutan

- **Debugging dengan bantuan AI:** ditemukan kasus tepi pada perhitungan IPK ketika mata kuliah yang sama memiliki nilai berbobot lebih tinggi tetapi berstatus tidak lulus.
- **Perbaikan:** fungsi `hitung_ipk()` diperbarui agar menyaring nilai dengan `lulus=true` terlebih dahulu, kemudian memilih bobot tertinggi per `kode_mk`.
- **Pengujian regresi:** ditambahkan `test_ipk_memilih_nilai_tertinggi_yang_lulus` untuk mencegah kesalahan serupa terulang.
- **Verifikasi melalui terminal:** `python -m pytest -q` menghasilkan **131 passed, 1 warning**.
- **Verifikasi database:** migrasi Alembic sampai `0007_grade_management`, struktur tabel dan VIEW, serta integritas foreign key telah diperiksa.
- **Dokumentasi:** kebijakan IPK pada ADR-004 dan informasi verifikasi pada README Minggu 9 disesuaikan dengan implementasi terbaru.
- **Catatan:** satu warning berasal dari deprecation Starlette/httpx. Hasil pengujian tidak membuktikan keamanan autentikasi produksi maupun ketahanan konkurensi multi-worker.

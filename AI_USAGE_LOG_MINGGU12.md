# AI Usage Log — Minggu 12

AI digunakan sebagai alat bantu dalam pengembangan dan pemeriksaan modul presensi QR Code yang merupakan kelanjutan proyek PMB dari minggu sebelumnya.

## Bentuk Bantuan AI

- Membantu meninjau integrasi model dan migrasi database dari minggu sebelumnya.
- Membantu menyusun dan meninjau implementasi QR Code, token JWT, validasi KRS, status kehadiran, dan pencegahan presensi ganda.
- Membantu menyusun analitik pola ketidakhadiran dan early warning berbasis aturan (rule-based), bukan model AI terlatih.
- Membantu menyusun pengujian batas waktu, keamanan endpoint, rate limiting, serta akurasi laporan JSON dan Excel.
- Membantu memeriksa dokumentasi, dependensi, konfigurasi, dan kesiapan proyek.

## Verifikasi Hasil

- Seluruh pengujian otomatis terakhir: 195 passed, 0 failed, 1 warning dalam 11,52 detik.
- Pemeriksaan dependensi menggunakan pip check: No broken requirements found.
- Revisi migrasi database lokal: 0010_attendance_qr (head).
- Peringatan pengujian berasal dari StarletteDeprecationWarning terkait integrasi httpx dan starlette.testclient.

## Catatan

AI digunakan sebagai alat bantu, bukan pengganti proses pemeriksaan. Hasil pengujian menunjukkan skenario yang diuji berhasil, tetapi tidak menjamin aplikasi bebas dari seluruh bug atau risiko keamanan.

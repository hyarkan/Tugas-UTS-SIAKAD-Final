# Tugas Minggu 12 — Modul Presensi (QR Code)

**Nama:** Muhamad Arkan Maulana  
**NIM:** 251635002  
**Prodi:** S1 Sistem Informasi  
**Kelas:** A  
**Mata kuliah:** Pemrograman Berorientasi Objek untuk Sistem AI Agenik

## Ruang lingkup

Kelanjutan proyek Minggu 3–11 (PMB, KRS, penjadwalan, nilai, transkrip, dan SPP). Semua source dan migrasi lama tetap dipertahankan. Minggu 12 menambah QR dosen untuk sesi `jadwal`, presensi mahasiswa terdaftar, laporan per mahasiswa/MK, ekspor XLSX, analitik pola absen dan early warning, serta pembatasan spam scan.

## Instalasi dan menjalankan (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

**Penting:** aplikasi tidak membaca `.env` secara otomatis. Set nilai rahasia pada *environment* PowerShell saat menjalankan, atau gunakan mekanisme pemuatan `.env` yang aman. Contoh untuk demo lokal (ganti dengan nilai acak milik Anda):

```powershell
$env:ATTENDANCE_JWT_SECRET = "GANTI_DENGAN_SECRET_ACAK_MINIMAL_32_KARAKTER"
$env:ATTENDANCE_ADMIN_KEY = "GANTI_DENGAN_KUNCI_DOSEN_RAHASIA"
alembic upgrade head
uvicorn app.main:app --reload
```

Buka `http://127.0.0.1:8000/docs` untuk Swagger UI. SQLite lokal `pmb.db` akan dibuat jika belum ada; lakukan seed data PMB/KRS/jadwal sesuai kebutuhan demo. **Jangan unggah `.env`, database nyata, token, atau kunci ke GitHub.**

## API Minggu 12

| Endpoint | Metode | Tujuan |
|---|---|---|
| `/attendance/qr/{schedule_id}` | GET | PNG QR JWT untuk sesi hari ini (dosen) |
| `/attendance/token/{schedule_id}` | GET | Token JWT untuk uji scan melalui Swagger (dosen) |
| `/attendance/scan` | POST | Scan `{ "token": "...", "nim": "..." }` |
| `/attendance/report?schedule_id=...` | GET | Rekap mahasiswa/MK dan warning `<75%` (dosen) |
| `/attendance/report.xlsx` | GET | Ekspor XLSX dua sheet (dosen) |
| `/attendance/insights` | GET | JSON pola, risiko, dan rekomendasi berbasis aturan (dosen) |

Endpoint dosen membutuhkan dua header: `X-Actor-Role: dosen` dan `X-Attendance-Admin-Key: <nilai ATTENDANCE_ADMIN_KEY>`. Ini autentikasi **demo**, belum menggantikan sistem login/RBAC produksi.

## Aturan validasi dan waktu

- `schedule_id` harus terdaftar; hari dan waktu harus cocok dengan `jadwal` (Asia/Jakarta, Senin=1).
- QR hanya dapat dibuat selama **30 menit pertama** sejak kuliah dimulai. Setiap penerbitan menghasilkan `jti` acak unik yang disimpan dalam tabel `attendance_qr`; JWT ditandatangani HS256.
- **Setiap QR berlaku maksimum 15 menit**, dan bisa lebih pendek jika mencapai akhir periode 30 menit/akhir kuliah. Untuk status terlambat, dosen **menerbitkan QR baru** setelah menit ke-15. Dengan demikian aturan QR 15 menit dan toleransi terlambat hingga menit ke-30 tidak bertentangan.
- `hadir`: scan dari waktu mulai hingga menit ke-15 (inklusif). `terlambat`: setelah menit ke-15 sampai menit ke-30 (inklusif). Di luar periode ditolak.
- JWT harus valid, belum kedaluwarsa, cocok dengan sesi/QR tersimpan, dan tidak boleh ditukar untuk kelas lain.
- NIM harus ada, dan mahasiswa wajib memiliki KRS berstatus `approved` pada semester, mata kuliah, **dan kelas paralel** yang sama (`krs_detail.kelas_id`). KRS yang tidak memilih kelas spesifik tidak dapat scan; tentukan kelas lebih dulu.
- Hanya satu presensi per NIM per sesi; unique constraint database mencegah duplikasi sekalipun ada request paralel.
- Rate limiting scan: maksimal 20 permintaan per 60 detik per IP **dalam satu proses server**. Untuk banyak worker atau produksi, gunakan Redis/reverse proxy.
- `session_date` unik per jadwal; satu sesi untuk satu pertemuan per hari. Ini desain demo sesuai jadwal mingguan.

## Laporan dan analitik

- Denominator persentase = **jumlah sesi perkuliahan yang sudah diterbitkan** untuk jadwal kelas tersebut, bukan jumlah minggu kalender yang belum berlangsung.
- `hadir` dan `terlambat` dihitung sebagai hadir; tanpa record pada sesi yang sudah dibuat dianggap `absen`.
- Persentase <75% menghasilkan warning. XLSX berisi sheet `Rekap Presensi` dan `Detail Sesi`.
- Analitik berbasis aturan (*rule-based*, offline, tidak menggunakan model AI terlatih): kelompok hari/jam berabsen tinggi, mahasiswa dengan kehadiran <75%, pola absen berulang minimal dua sesi, rekomendasi konseling, serta evaluasi jam kelas jika tingkat absen >=40% dengan minimal tiga observasi.
- Analitik memakai KRS `approved` yang berlaku **saat laporan dibuka**. Perubahan KRS setelah sesi dapat memengaruhi laporan historis; untuk produksi sebaiknya buat snapshot peserta per sesi.

## Pengujian

Pengujian otomatis mencakup modul Minggu 12 dan fitur dari minggu sebelumnya.

Perintah pengujian:
- python -m pytest tests/test_attendance_week12.py -v
- python -m pytest tests/test_attendance_boundaries_week12.py -v
- python -m pytest tests/test_attendance_security_week12.py -v
- python -m pytest tests/test_attendance_report_week12.py -v
- python -m pytest -q

Cakupan: QR PNG, JWT unik, kedaluwarsa maksimal 15 menit, validasi hari dan waktu, KRS approved, presensi ganda, otorisasi dosen, rate limiting, laporan JSON/Excel, warning kehadiran, dan AI Insights berbasis aturan.

Hasil pengujian penuh terakhir: 195 passed, 0 failed, 1 warning (StarletteDeprecationWarning), dalam 11,52 detik. Hasil ini tidak menjamin seluruh kemungkinan kondisi atau keamanan produksi.

## Batasan keamanan dan ruang lingkup

- Input scan sesuai soal adalah `{token, nim}`. Karena tidak ada login mahasiswa pada endpoint ini, NIM masih dapat diklaim pihak lain yang memperoleh QR. **Jangan gunakan untuk presensi produksi tanpa autentikasi mahasiswa dan pengikatan NIM ke identitas login.**
- Geolocation disebut **opsional** pada PDF, sehingga belum diaktifkan; jika diterapkan, validasi lokasi harus mempertimbangkan spoofing GPS dan privasi.
- QR yang ditampilkan dapat difoto/dibagikan; validasi kelas, masa berlaku, dan identitas terautentikasi adalah kontrol yang berbeda.
- Laporan tidak menyatakan mahasiswa absen sebelum sesi diterbitkan. Analitik bukan model prediksi ML, melainkan deteksi pola berbasis aturan yang dapat dijelaskan.

## Dokumen dan histori

`README.md` tetap menyimpan catatan lama. README per minggu (`README_MINGGU7.md` sampai `README_MINGGU11.md`) dan `README_BACKUP_SEBELUM_MINGGU11.md` tidak dihapus. Migrasi baru `0010_attendance_qr.py` mengikuti `0009_finance_spp.py`.



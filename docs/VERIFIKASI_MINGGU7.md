# Hasil Verifikasi Minggu 7

Tanggal pembaruan: 21 November 2026.

## 1. Verifikasi pada lingkungan penyusunan sebelumnya

- `python -m compileall -q app migrations`: berhasil.
- `alembic upgrade head` pada SQLite baru: berhasil sampai `0005_scheduling`.
- Seed dengan `--with-conflicts`: dilaporkan menghasilkan 10 ruangan, 15 dosen, 42 kelas, dan 42 jadwal, termasuk 2 jadwal konflik impor.
- Pengujian terpilih: 69 passed.
- Hypothesis belum tersedia pada lingkungan penyusunan sebelumnya.

## 2. Verifikasi aktual pada laptop pengguna

Lingkungan: Windows PowerShell, Python 3.14.0, virtual environment `.venv`, SQLite.

### Dependensi dan migration
- `python -m pip check`: No broken requirements found.
- `python -m alembic heads`: `0005_scheduling (head)`.
- `python -m alembic upgrade head`: berhasil.
- `python -m alembic current`: `0005_scheduling (head)`.
- `python -m alembic check`: No new upgrade operations detected.
- Pemeriksaan tabel, foreign key, CHECK constraint, dan indeks jadwal: berhasil.
- Pengujian CHECK constraint dan foreign key SQLite pada salinan/skema sementara: berhasil.

### Pengujian algoritma dan API
- Pengujian manual naive versus sweep: hasil konsisten pada kasus yang diperiksa.
- Hypothesis manual dengan 200 contoh: naive dan sweep memberikan hasil identik.
- `python -m pytest tests/test_scheduling_week7.py -v`: 8 passed, 1 warning.
- `python -m pytest -v`: 74 passed, 1 warning, dalam 10.03 detik.
- Dua property-based test Minggu 7 lulus:
  - `test_sweep_equals_naive`
  - `test_accepted_schedule_never_overlaps`
- Warning: StarletteDeprecationWarning terkait penggunaan httpx pada TestClient; tidak menyebabkan kegagalan pengujian.

### Seed normal tanpa konflik impor
- `python -m app.seed`: berhasil, 7 mata kuliah dan 5 skala nilai.
- `python -m app.seed_scheduling`: berhasil tanpa `--with-conflicts`.
- Hasil query database:
  - Ruangan: 10
  - Dosen: 15
  - Kelas: 40
  - Jadwal: 40
- `detect_schedule_conflict` terhadap 40 jadwal: 0 konflik.

## 3. Batasan yang belum terverifikasi

- Concurrency nyata lintas koneksi pada PostgreSQL/MySQL belum diuji.
- Otorisasi dan autentikasi admin belum tersedia untuk penggunaan produksi.
- Perilaku pada dataset besar belum dibuktikan melalui benchmark waktu.
- Integrasi notifikasi Observer, AI rescheduling, dan invalidasi KRS termasuk ruang lingkup Minggu 8.
- Pengujian yang lulus tidak otomatis membuktikan seluruh skenario di lingkungan produksi.

## 4. Catatan penggunaan

- Untuk seed normal: `python -m app.seed_scheduling`.
- Gunakan `--with-conflicts` hanya untuk demonstrasi konflik data impor.
- Backup database sebelum migrasi atau perubahan pada database yang berisi data penting.
- Folder Minggu 6 asli tidak digunakan sebagai lokasi perubahan proyek Minggu 7.

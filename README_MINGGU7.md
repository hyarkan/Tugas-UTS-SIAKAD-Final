# Tugas Minggu 7 — Modul Jadwal & Ruangan

Kelanjutan **PMB/KRS Minggu 6**, dengan fitur Minggu 7 saja. Folder asli Minggu 6 tidak diubah.

## Instalasi (Windows PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
python -m app.seed_scheduling
pytest -q
uvicorn app.main:app --reload
```

Swagger: `http://127.0.0.1:8000/docs`.

## Endpoint
- `POST /api/jadwal` — 201 atau 404/409/422
- `PUT /api/jadwal/{jadwal_id}` — 200 atau 404/409/422
- `DELETE /api/jadwal/{jadwal_id}` — 204 atau 404
- `GET /api/jadwal/conflicts` — daftar bentrok data impor

Contoh payload:
```json
{"kelas_id":1,"hari":1,"jam_mulai":"08:00:00","jam_selesai":"09:40:00","ruangan_kode":"A001","dosen_id":1}
```

`409` berisi `detail.message` dan, untuk bentrok, `detail.conflicts` dengan `type` serta `affected` (ID jadwal lama dan `0` untuk kandidat baru yang belum memiliki ID).

## Seed
`python -m app.seed_scheduling` membuat >=10 ruang, >=15 dosen, >=40 jadwal tanpa sengaja menambah bentrok. Tambahkan `--with-conflicts` **hanya untuk demonstrasi** endpoint laporan bentrok akibat impor legacy; opsi ini menyisipkan data langsung ke DB sehingga tidak melewati validasi SchedulingService. Seed idempotent berdasarkan identitas kelas.

## Kompatibilitas
Kolom `matakuliah.hari/jam_*` tetap tersedia untuk kompatibilitas Minggu 5–6. Jadwal baru tersimpan di tabel `jadwal`. `krs_detail.kelas_id` bersifat opsional untuk data legacy. Integrasi validasi KRS berbasis kelas, notifikasi Observer, dashboard dan AI rescheduling termasuk Minggu 8.

## Batasan penting
- Tidak ada autentikasi admin pada endpoint jadwal (demo akademik, jangan publikasikan tanpa otorisasi).
- SQLite memakai BEGIN IMMEDIATE untuk serialisasi penulis; PostgreSQL/MySQL memakai SELECT FOR UPDATE. Uji concurrency nyata pada target DB belum dibuktikan.
- `pytest` membutuhkan paket Hypothesis yang tercantum di requirements.txt.
- Untuk migrasi DB lama, buat backup terlebih dahulu; ZIP ini tidak menyertakan DB pengguna.
- Lihat `docs/ADR-003-scheduling-interval-tree.md`, `docs/OPAR_MINGGU7.md`, `AI_USAGE_LOG_MINGGU7.md`.

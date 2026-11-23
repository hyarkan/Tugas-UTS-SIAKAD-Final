# Catatan Audit dan Verifikasi Tugas Minggu 6

## Perubahan inti

- State machine empat status dengan tabel transisi berbasis aktor dan `transition()`.
- Service `submit_krs`, `approve_krs`, dan `revise_krs`.
- Guard role dan ownership: mahasiswa hanya KRS sendiri; dosen harus sama dengan `krs.dosen_pa_id`.
- Submit menolak KRS kosong dan menjalankan ulang seluruh validator.
- Approval menyimpan status, timestamp, audit log, dan notifikasi database dalam satu transaksi.
- Catatan revisi wajib diisi.
- Pessimistic locking: `SELECT FOR UPDATE` pada database pendukung; `BEGIN IMMEDIATE` untuk SQLite.
- Optimistic locking: SQLAlchemy `version_id_col` dan pemeriksaan `version` request.
- Migration Alembic `0004_krs_state_machine`.
- Property-based test Hypothesis untuk 1000 contoh SKS dan 1000 contoh jadwal.
- Test parameterized empat transisi legal dan 28 transisi ilegal.

## Hasil yang benar-benar dijalankan

### Verifikasi lokal terbaru

1. `python -m pytest -v --cov=app --cov-report=term-missing` — **64 passed**, **0 failed**, **0 errors**, total coverage **85%**. Terdapat satu deprecation warning dari integrasi Starlette TestClient dan HTTPX; warning ini tidak menggagalkan pengujian.
2. Hypothesis berhasil dijalankan setelah dependensi dipasang:
   - Property test batas maksimal SKS menggunakan `max_examples=1000`.
   - Property test bentrok jadwal menggunakan `max_examples=1000`.
3. Pengujian state machine mencakup empat transisi legal dan 28 transisi ilegal (**32 kombinasi**).
4. Migration lokal menggunakan SQLite:
   - `alembic upgrade head` — berhasil.
   - `alembic current` — menunjukkan `0004_krs_state_machine (head)`.
   - Database SQLite lokal berhasil dibuat dan dimigrasikan.

### Hasil audit terdahulu (bukan hasil lokal terbaru)

- `python -m compileall -q app migrations tests` — berhasil.
- Pengujian terdahulu: **61 passed** dengan total coverage **86%**.
- Migration SQLite sementara: `upgrade head` → `downgrade 0003_krs_module` → `upgrade head` — berhasil.
- Smoke test acak manual: 1000 urutan penambahan SKS dan 1000 urutan jadwal — seluruh pemeriksaan lolos.

## Batas verifikasi

- Pengujian lokal menggunakan SQLite. Row-level locking MySQL/InnoDB belum dibuktikan dan race condition lintas worker belum diuji.
- `X-Actor-*` adalah simulasi identitas untuk tugas, bukan autentikasi produksi.
- Notifikasi disimpan sebagai record database, belum dikirim melalui email/push.
- Dosen PA harus ditetapkan pada `krs.dosen_pa_id` sebelum approval.
- Rollback akibat kegagalan di tengah transaksi belum diuji secara khusus.

## Perintah verifikasi pada komputer mahasiswa

```powershell
pip install -r requirements.txt
alembic upgrade head
alembic current
python -m pytest -v --cov=app --cov-report=term-missing
```

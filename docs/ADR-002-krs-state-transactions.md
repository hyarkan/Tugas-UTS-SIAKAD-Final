# ADR-002: State machine, approval transaction, dan version KRS

- **Status:** Diterima
- **Konteks:** KRS Minggu 5 sudah memiliki draft dan validasi isi, tetapi belum memiliki alur submit/approval/revision. Perubahan bersamaan dapat menyebabkan isi KRS berubah ketika dosen sedang memeriksa.

## Keputusan

1. Menggunakan enum `KRSStatus` dengan empat nilai: `draft`, `submitted`, `approved`, dan `revision`.
2. Menggunakan tabel transisi eksplisit pada model `KRS`, dengan aktor pada setiap pasangan state:
   - `draft` + `mahasiswa` → `submitted`
   - `submitted` + `dosen_pa` → `approved` atau `revision`
   - `revision` + `mahasiswa` → `submitted`
3. Semua perpindahan status service dilakukan melalui `KRS.transition()`, yang memanggil `check_transition()` lebih dahulu. `approved` merupakan status akhir.
4. Memisahkan pemeriksaan peran dan kepemilikan. Dosen harus cocok dengan `krs.dosen_pa_id`; mahasiswa harus mengajukan KRS dengan NIM miliknya sendiri.
5. `submit_krs` menolak KRS kosong dan menjalankan ulang seluruh validator sebelum status berubah.
6. `approve_krs` menyimpan status, `approved_at`, audit log, dan notifikasi database dalam satu transaksi. Tidak ada pengiriman email eksternal di dalam transaksi.
7. `revise_krs` mewajibkan catatan revisi agar mahasiswa mengetahui tindakan yang diperlukan.
8. Menggunakan `SELECT FOR UPDATE` pada database yang mendukung row lock. SQLite memakai `BEGIN IMMEDIATE` karena SQLite tidak menyediakan row-level `SELECT FOR UPDATE`.
9. Menggunakan SQLAlchemy `version_id_col` melalui kolom `krs.version`. Endpoint submit/approve/revise meminta versi yang dibaca klien; versi usang ditolak dengan HTTP 409. Perubahan `krs_detail` juga menyentuh `krs.updated_at` agar versi parent bertambah.
10. Menyimpan `KRSLog` dan `KRSNotification` di database. Pengiriman notifikasi eksternal ditunda ke observer/event handler pada materi berikutnya.

## Alternatif

- Menggunakan library `python-statemachine` atau `transitions`. Tidak dipilih karena empat state dan empat transisi dapat dijelaskan secara langsung melalui tabel, tanpa dependensi tambahan.
- Mengandalkan optimistic locking saja. Tidak dipilih sebagai satu-satunya perlindungan karena operasi mutasi tetap memerlukan serialisasi pada database; row lock/SQLite immediate transaction dipertahankan bersama version check.
- Mengirim email saat transaksi approval berlangsung. Ditolak karena efek eksternal tidak dapat di-rollback.

## Konsekuensi dan batasan

- Header `X-Actor-*` pada demo hanya merupakan simulasi identitas untuk pengujian API. Ini bukan autentikasi produksi; aplikasi nyata harus mengambil role, NIM, dan ID dosen dari token/session login yang tervalidasi.
- `dosen_pa_id` harus sudah ditetapkan pada baris KRS oleh proses akademik sebelum approval. Modul login dan master data dosen belum termasuk ruang lingkup proyek ini.
- SQLite menguji alur transaksi aplikasi, tetapi tidak membuktikan row-level locking MySQL/InnoDB atau race condition lintas worker. Pengujian concurrency MySQL masih diperlukan bila database tersebut digunakan.
- Notifikasi yang dibuat di sini adalah catatan database, bukan email/push notification. Pengiriman aktual menjadi tanggung jawab observer pada Minggu 7–8.

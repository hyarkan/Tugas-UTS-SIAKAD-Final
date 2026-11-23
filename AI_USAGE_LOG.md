# AI Usage Log

## Minggu 3

### Fitur
Fondasi aplikasi PMB: model tiga tabel, migration Alembic, endpoint registrasi, validasi input, dan penanganan email duplikat.

### Tujuan
Menggunakan AI sebagai alat bantu untuk memahami rancangan dan mempercepat implementasi aplikasi PMB.

### LLM atau tool
ChatGPT.

### Prompt kunci
"Bantu saya mengembangkan aplikasi PMB berbasis FastAPI menggunakan SQLAlchemy 2.0 dan Alembic. Implementasikan tiga model tabel beserta atribut dan constraint yang diperlukan, konfigurasi migrasi database dengan pengujian upgrade dan downgrade, serta buat endpoint POST /api/pmb/register. Pastikan endpoint memiliki validasi input dan menolak email duplikat dengan HTTP 409."

### Revisi manual
Memeriksa model, relasi, validasi, migration, endpoint, serta hasil pengujian secara manual.

### Hasil uji
Registrasi valid `201`, email duplikat `409`, tanggal lahir tidak valid `422`, dan referensi tidak ditemukan `400`.

## Minggu 4

### Fitur
Endpoint approve/reject, generator NIM, endpoint status dan statistik, pengujian Pytest, dokumentasi Swagger, dan README.

### Tujuan
Menyelesaikan alur PMB serta memastikan pembuatan NIM konsisten ketika approve diulang atau beberapa permintaan diproses berdekatan.

### LLM atau tool
ChatGPT sebagai alat bantu analisis, penyusunan kode, dokumentasi, dan debugging; Pytest dan pytest-cov untuk verifikasi otomatis.

### Prompt kunci
"Perluas aplikasi PMB FastAPI dan SQLAlchemy 2.0 yang sudah ada. Tambahkan endpoint PUT approve/reject, generator NIM dengan format 4 digit tahun + 3 digit kode prodi + 4 digit nomor urut, idempotensi, counter database, transaksi, penguncian sesuai dialect SQLite/MySQL, unique constraint, endpoint GET status dan statistik dengan GROUP BY, serta integration test Pytest. Generator tidak boleh melakukan commit sendiri. Sertakan pengujian approve berulang, data invalid, dan target coverage minimal 80%."

### Revisi manual
- Memilih format NIM 11 digit tanpa strip (`YYYYKKKNNNN`) dan mendokumentasikannya.
- Menggunakan tabel counter dengan primary key gabungan tahun dan kode prodi.
- Memastikan generator hanya melakukan flush dan transaksi/commit dimiliki fungsi approve.
- Menggunakan `BEGIN IMMEDIATE` pada SQLite karena SQLite tidak mendukung row-level `SELECT FOR UPDATE`.
- Menggunakan `SELECT FOR UPDATE` pada database yang mendukungnya serta mempertahankan unique constraint NIM.
- Mempertahankan respons validasi Pydantic/FastAPI `422` untuk nomor telepon tidak valid, sesuai pilihan desain yang sudah dicatat di README.
- Menambahkan kasus uji approve idempotent yang memastikan counter tidak bertambah saat approve diulang.

### OPAR

**Observe:** Modul PMB Minggu 3 belum memiliki alur approve/reject dan generator NIM. Approve berulang dapat menghasilkan nomor baru, sedangkan dua approve bersamaan berisiko membaca nomor urut yang sama.

**Plan:** Menambahkan tabel counter per tahun dan kode prodi, transaksi database, penguncian sesuai database, unique constraint, serta pengujian idempotensi dan kasus error.

**Act:** Mengimplementasikan endpoint approve/reject, generator NIM, endpoint status/stats, migration counter, dokumentasi, dan tes otomatis.

**Reflect:** Tes SQLite memverifikasi alur aplikasi dan idempotensi, tetapi tidak membuktikan row locking MySQL atau race condition multi-worker di lingkungan produksi. Pengujian beban dan verifikasi MySQL masih diperlukan jika lingkungan tersebut tersedia.

### Hasil uji
Perintah `pytest --cov=app --cov-report=term-missing --cov-fail-under=80` berhasil dijalankan. Hasil verifikasi: 15 tes lulus dan total coverage 81,38%, sehingga melewati target minimal 80%.

## Peran Mahasiswa

Mahasiswa bertanggung jawab meninjau kode yang dihasilkan atau disarankan AI, memahami alur transaksi dan penguncian, menjalankan pengujian, memeriksa hasil, serta memastikan dokumentasi sesuai implementasi.

## Pernyataan

AI digunakan sebagai alat bantu. Verifikasi, pemahaman, dan tanggung jawab atas hasil akhir tetap berada pada mahasiswa.


## Minggu 5 – Modul KRS

### Tujuan
Melanjutkan aplikasi PMB menjadi fondasi modul KRS dengan skema relasional, service pengelola KRS, empat validator, query prasyarat, dan perlindungan transaksi.

### Prompt kunci
"Lanjutkan project FastAPI dan SQLAlchemy 2.0 yang sudah ada tanpa merusak modul PMB. Tambahkan model dan migration untuk matakuliah, krs, krs_detail, prerequisite self-reference, serta skala_nilai. Implementasikan KRSManager add/remove/validate, Chain of Responsibility dengan empat validator, query prasyarat NOT EXISTS yang membandingkan bobot nilai minimal C, deteksi bentrok menggunakan irisan interval, constraint unik, dan transaksi dengan row lock. Tambahkan endpoint, seed dummy, dokumentasi keputusan desain, dan pengujian."

### Revisi manual dan keputusan
- Menggunakan format semester `YYYY1` (ganjil) dan `YYYY2` (genap) agar urutan string sesuai urutan semester.
- Menambahkan `skala_nilai` agar nilai huruf tidak dibandingkan secara leksikografis; nilai C memiliki bobot 2 dan dinyatakan lulus.
- Menempatkan `DuplicateValidator` pertama karena murah dan tidak membutuhkan query; urutan serta alasan dicatat pada ADR-001.
- Memakai rumus irisan interval: hari sama, `mulai_A < selesai_B`, dan `mulai_B < selesai_A`.
- Menjalankan validasi dan insert dalam satu transaksi; memakai `SELECT FOR UPDATE` pada database yang mendukungnya dan `BEGIN IMMEDIATE` untuk SQLite.
- Minggu 5 hanya menyediakan status KRS serta operasi add/remove/validate. Transisi state machine submit/approve tetap menjadi pekerjaan Minggu 6.

### OPAR
**Observe:** Modul PMB sudah menghasilkan NIM, tetapi belum menyediakan relasi dan aturan pengambilan mata kuliah. Validasi tanpa penguncian dapat menyebabkan dua permintaan bersamaan melewati batas SKS.

**Plan:** Menambahkan lima tabel terkait KRS, rantai validator, query prasyarat berbasis NOT EXISTS, constraint, transaksi, endpoint, dan pengujian.

**Act:** Menambahkan model, migration 0003, seed mata kuliah dan skala nilai dummy, service, validator, endpoint KRS, ADR, dokumentasi, serta tes regresi PMB dan tes KRS.

**Reflect:** Pengujian SQLite telah memverifikasi aturan validasi KRS, operasi transaksi dasar, serta regresi modul PMB. Dua property-based test menggunakan Hypothesis juga telah ditambahkan untuk memastikan batas maksimal 24 SKS selalu diterapkan dengan benar. Hasil EXPLAIN QUERY PLAN aktual telah didokumentasikan pada docs/EXPLAIN_QUERY_PLAN.txt dan menunjukkan penggunaan indeks SQLite. Namun, pengujian SQLite belum membuktikan row-level locking MySQL atau race condition multi-worker di lingkungan produksi. Pengujian tersebut masih memerlukan verifikasi pada database MySQL. Pengembangan state machine submit/approve tetap dialokasikan untuk Minggu 6.

## Minggu 6 – State Machine, Approval, dan Concurrency KRS

### Fitur
State machine empat status, submit/approve/revise KRS, otorisasi peran dan kepemilikan, transaksi approval, audit log, notifikasi database, pessimistic locking, optimistic versioning, serta pengujian transisi dan properti.

### Tujuan
Mencegah transisi status ilegal, memastikan hanya mahasiswa pemilik yang dapat submit, memastikan hanya dosen PA terdaftar yang dapat approve/revise, dan menjaga konsistensi KRS ketika beberapa request berlangsung berdekatan.

### AI/tool dan prompt kunci
AI digunakan sebagai alat bantu analisis dan implementasi. Prompt kerja yang digunakan:

> Lanjutkan project FastAPI + SQLAlchemy 2.0 modul KRS Minggu 5 tanpa membangun ulang fitur yang sudah ada. Implementasikan enum KRSStatus dan tabel transisi yang memasukkan aktor; hanya izinkan DRAFT→SUBMITTED oleh mahasiswa, SUBMITTED→APPROVED/REVISION oleh dosen PA, dan REVISION→SUBMITTED oleh mahasiswa. Buat transition() sebagai satu-satunya jalur perubahan status. Tolak KRS kosong, validasi ulang saat submit, cek ownership mahasiswa dan dosen_pa_id, buat endpoint submit/approve/revise dengan 403 dan 409 yang tepat, bungkus perubahan status/timestamp/audit log/notifikasi dalam transaksi, tambahkan row lock dan optimistic version, serta tes 1000 contoh SKS, jadwal bentrok, dan seluruh 32 kombinasi state/aktor.

### Revisi dan verifikasi manual
- Menjaga nilai status database tetap lowercase agar kompatibel dengan migration Minggu 5 (`draft`, `submitted`, `approved`, `revision`).
- Menggunakan tabel transisi eksplisit dengan aktor, bukan rangkaian `if` yang tersebar di endpoint.
- Memastikan dosen yang mengirim request juga cocok dengan `dosen_pa_id` pada KRS; role saja tidak cukup.
- Menambahkan header `X-Actor-Role`, `X-Actor-NIM`, dan `X-Actor-Id` sebagai simulasi identitas untuk demo/test. Header ini bukan mekanisme autentikasi produksi dan harus diganti integrasi login/token.
- Menolak KRS kosong dan menjalankan ulang `validate_krs()` saat submit.
- Menyimpan status, waktu approval, audit log, dan catatan notifikasi database dalam satu commit; tidak mengirim email di tengah transaksi.
- Menambahkan `version` dengan SQLAlchemy `version_id_col`; perubahan detail menyentuh `updated_at` pada parent agar version ikut naik.
- Mempertahankan `SELECT FOR UPDATE` untuk database yang mendukungnya dan `BEGIN IMMEDIATE` untuk SQLite.
- Menambahkan migration `0004_krs_state_machine` dan ADR-002.
- Mengubah property test SKS menjadi 1000 contoh serta menambahkan property jadwal dan pemeriksaan 32 kombinasi transisi.

### OPAR
**Observe:** Tanpa state machine, endpoint dapat mengubah status secara tidak konsisten; dosen yang bukan PA dapat menyetujui KRS; KRS kosong dapat diajukan; dan request edit bersamaan dengan submit dapat membuat data yang tidak tervalidasi ikut tersimpan.

**Plan:** Menetapkan empat transisi dengan aktor, ownership guard, validasi ulang, satu transaksi approval, row lock, optimistic version, serta pengujian property-based dan parameterized. Dua property test utama menggunakan Hypothesis dengan masing-masing `max_examples=1000`: property test batas maksimal SKS dan property test bentrok jadwal.

**Act:** Menambahkan method `check_transition()`/`transition()`, service submit/approve/revise, endpoint API, timestamp, audit log, notifikasi database, migration, ADR, dan test.

**Reflect:** Pengujian lokal membuktikan alur API, penolakan aktor salah, penolakan versi usang, catatan revisi, serta konsistensi log/notifikasi pada SQLite. SQLite tidak membuktikan perilaku row-level locking MySQL atau race condition multi-worker. Header identitas saat ini hanya simulasi karena autentikasi belum tersedia. Notifikasi masih berupa record database dan belum dikirim melalui email/push; integrasi eksternal direncanakan pada tahap pengembangan Minggu 7–8.

### Hasil verifikasi yang dijalankan
- `python -m pytest -v --cov=app --cov-report=term-missing`: 64 passed, 0 failed, 0 errors; total coverage 85%.
- Hypothesis berhasil dijalankan setelah dependensi berhasil dipasang. Dua property test utama menggunakan `max_examples=1000`: pengujian batas maksimal SKS dan bentrok jadwal.
- Pengujian parameterized mencakup empat transisi legal dan 28 transisi ilegal.
- `alembic upgrade head` berhasil menjalankan migrasi hingga `0004_krs_state_machine`; `alembic current` menunjukkan `0004_krs_state_machine (head)`.
- Database SQLite lokal berhasil dibuat dengan tabel hasil migrasi.
- Pengujian row-level locking MySQL, race condition lintas worker, dan rollback akibat kegagalan transaksi belum dilakukan.
- Terdapat satu deprecation warning dari integrasi Starlette TestClient dan HTTPX; warning ini tidak menggagalkan pengujian dan seluruh tes tetap berhasil.

### Tanggung jawab mahasiswa
Mahasiswa perlu membaca dan memahami state transition, transaction boundary, optimistic version, serta keterbatasan simulasi identitas. Hasil AI harus diperiksa dan diuji kembali di lingkungan lokal sebelum dikumpulkan.

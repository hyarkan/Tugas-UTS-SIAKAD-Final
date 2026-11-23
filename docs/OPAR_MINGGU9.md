# OPAR — Minggu 9

## Observe
Proyek Minggu 8 sudah punya `krs_detail.nilai` FK dan `skala_nilai.lulus`; bobot masih Integer. Materi Minggu 9 meminta Decimal, audit trail, port presensi, dan pengampu.

## Plan
Migrasi Numeric dan history; implementasi pure GPA, service transaksi, API dan form; pengujian parametrik/properti/integrasi.

## Act
Implementasi dalam folder terpisah `pmb_app_tugas_minggu9_nilai`; pertahankan kode Minggu 8.

Modul Nilai dikembangkan menggunakan GradeService, PresensiPort/PresensiStub, API input nilai, form demo, perhitungan IPS/IPK berbasis Decimal, dan audit perubahan nilai.

Migrasi Alembic diverifikasi sampai `0007_grade_management (head)`. Struktur tabel, SQL VIEW `v_grade_history`, dan integritas foreign key telah diperiksa.

Pengujian otomatis dijalankan menggunakan `python -m pytest -q` dengan hasil **131 passed, 1 warning**. Pengujian regresi juga ditambahkan untuk kasus mata kuliah berulang dengan nilai tertinggi yang tidak lulus.

## Reflect
Kontradiksi D(2.0) harus dikonfirmasi. Presensi stub fail-closed dan header identitas demo belum layak produksi. Audit service tidak menangkap SQL manual; larang akses tulis langsung.

Ditemukan kasus tepi pada perhitungan IPK: pemilihan bobot tertinggi sebelum memeriksa status kelulusan dapat menghilangkan mata kuliah yang sebenarnya memiliki nilai lulus. Logika diperbaiki dengan menyaring `lulus=true` terlebih dahulu, kemudian memilih bobot tertinggi per `kode_mk`.

Seluruh 131 pengujian otomatis lulus setelah perbaikan. Satu warning deprecation Starlette/httpx tidak menggagalkan pengujian. Pengujian yang lulus belum membuktikan keamanan autentikasi produksi maupun ketahanan konkurensi multi-worker.

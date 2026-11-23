# ADR-003: Deteksi bentrok menggunakan grouping + sweep

**Status:** Diterima untuk Minggu 7. **Konteks:** PDF meminta interval tree, video dosen mengizinkan pendekatan sweep apabila dijustifikasi.

## Keputusan
Gunakan dua implementasi: `detect_naive` O(n²) sebagai oracle pengujian dan `detect_schedule_conflict` yang mengelompokkan berdasarkan (hari, ruangan) / (hari, dosen), mengurutkan awal interval, lalu menyapu daftar interval aktif. Gunakan interval setengah terbuka `[mulai, selesai)`.

## Alasan
600 jadwal memerlukan 600×599/2 = **179.700** pemeriksaan pasangan pada algoritma naif. Setelah pengelompokan, jumlah jadwal per ruangan/hari biasanya jauh lebih kecil. Sweep memerlukan sorting O(n log n) ditambah pekerjaan pada interval aktif; pada kasus terburuk ketika semua interval tumpang tindih, keluaran dan pemeriksaan tetap O(n²). **Angka 179.700 adalah hitungan teoretis, bukan hasil benchmark waktu.** Interval tree dapat bermanfaat untuk query interval berulang pada dataset sangat besar, tetapi membawa dependensi dan kompleksitas tambahan.

## Konsekuensi dan batasan
Simpan detektor naif sebagai pembanding property-based test. Optimasi harus dibenchmark sebelum diklaim lebih cepat pada lingkungan produksi. Indeks database `(hari, ruangan_kode)` dan `(hari, dosen_id)` membantu query layanan. SQL database melakukan pengecekan konflik pada create/update, sedangkan sweep memindai data lama untuk endpoint dashboard.

## Concurrency
PostgreSQL/MySQL: `SELECT ... FOR UPDATE` pada baris ruangan lalu dosen sebelum cek konflik. SQLite mengabaikan `FOR UPDATE`, sehingga aplikasi mengawali transaksi tulis dengan `BEGIN IMMEDIATE`. SQLite tidak membuktikan perilaku row lock PostgreSQL/MySQL; uji concurrency lintas koneksi tetap diperlukan pada DB produksi. Tidak ada filter semester aktif di pemeriksaan konflik (jadwal saat ini dianggap satu periode aktif); kebutuhan multi-semester adalah risiko yang harus ditangani berikutnya.

## Migrasi kompatibilitas
Kolom hari/jam legacy di `matakuliah` dipertahankan agar API dan tes Minggu 5–6 tidak rusak. Sumber jadwal baru ada di `jadwal`; penonaktifan kolom legacy dan migrasi validasi KRS ke kelas paralel dijadwalkan pada tahap integrasi berikutnya.

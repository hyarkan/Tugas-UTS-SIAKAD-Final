# Architecture Decision Record (ADR) — Final UTS SIAKAD

## 1. Konteks dan Ruang Lingkup

Dokumen ini merangkum keputusan arsitektur Modul PMB, KRS,
dan perancangan UML SIAKAD, termasuk alternatif desain,
trade-off, mitigasi, dan batasan implementasi.

Modul Minggu 7–12 merupakan pelengkap integrasi sistem,
bukan pengganti fokus utama Final UTS.

Dokumen PDF:
[ADR Final UTS SIAKAD](../../artifacts/final_uts/ADR_FINAL_UTS_SIAKAD.pdf).

## 2. Struktur Kelas dan Pemisahan Layer

| Komponen | Tanggung jawab |
|---|---|
| Router / FastAPI | Menerima request dan menghasilkan respons HTTP. |
| Schema / Pydantic | Memvalidasi kontrak dan tipe data. |
| Service | Menjalankan aturan bisnis PMB dan KRS. |
| Validator | Memeriksa aturan akademik secara terpisah. |
| Model / SQLAlchemy | Memetakan entitas dan relasi database. |
| SQLite | Penyimpanan data lingkungan pengembangan. |
| Alembic | Mengelola migrasi skema 0001–0010. |

Alur umum:

Klien / Swagger → Router → Schema dan Service / Validator → ORM → Database.

PMBService pada UML merupakan representasi konseptual
fungsi dalam pmb_service.py, bukan class Python aktual.

## 3. Penerapan Prinsip SOLID

| Prinsip | Penerapan dan batasan |
|---|---|
| SRP | Pemisahan tanggung jawab router, schema, service, model, dan validator. |
| OCP | Validator terpisah memudahkan penambahan aturan akademik. |
| LSP | Konsistensi kontrak antarvalidator menjadi pedoman desain. |
| ISP | Antarmuka komponen diupayakan tetap terfokus. |
| DIP | Pengelolaan ketergantungan menjadi pedoman pengembangan. |

SOLID digunakan sebagai dasar evaluasi desain.
Kepatuhan formal terhadap seluruh prinsip belum diaudit.

## 4. PMB-A — Validasi Registrasi Berlapis

### Konteks

Registrasi harus menolak data tidak valid, email duplikat,
dan referensi program studi atau jalur masuk yang tidak tersedia.

### Keputusan

- Pydantic memvalidasi input.
- Service memeriksa keunikan email dan referensi.
- Constraint database menjaga integritas data.
- Pendaftar valid disimpan dengan status pending.
- Endpoint status dan statistik mendukung pemantauan.

### Alternatif dan Trade-off

Validasi terpusat dalam router lebih sederhana pada awalnya,
tetapi menyulitkan pengujian dan penggunaan ulang.

Validasi berlapis membutuhkan koordinasi aturan antar
schema, service, dan database.

### Mitigasi

Menjaga konsistensi aturan dan menguji input tidak valid,
referensi yang tidak tersedia, serta duplikasi data.

## 5. PMB-B — Persetujuan dan Penerbitan NIM

### Keputusan

- Format NIM: YYYYKKKNNNN (11 digit).
- NIMCounter mengelola urutan berdasarkan tahun dan kode prodi.
- NIM, status approve, dan approve_at disimpan dalam transaksi.
- Approval berulang mengembalikan NIM yang sama.
- Status PMB: pending, approve, dan rejected.

### Alternatif dan Trade-off

Menghitung jumlah pendaftar sebagai nomor berikutnya
berisiko menghasilkan konflik pada permintaan paralel.

Counter, unique constraint, dan transaksi mengurangi
risiko tersebut, tetapi dapat menambah kontensi tulis.

### Mitigasi

SQLite menggunakan BEGIN IMMEDIATE.
Penguncian dan konkurensi pada DBMS lain perlu diuji
dalam lingkungan target.

## 6. ADR-001 — Chain of Responsibility

### Konteks

Pengambilan mata kuliah memerlukan pemeriksaan duplikasi,
batas SKS, prasyarat, dan bentrok jadwal.

### Keputusan

| Validator | Aturan |
|---|---|
| DuplicateValidator | Mencegah mata kuliah ganda. |
| SKSValidator | Memeriksa batas maksimal 24 SKS. |
| PrerequisiteValidator | Memeriksa kelulusan prasyarat. |
| ConflictValidator | Memeriksa bentrok jadwal. |

Urutan validasi:

Duplicate → SKS → Prerequisite → Conflict.

Operasi add_course menggunakan pendekatan fail-fast.
Operasi validate_krs mengumpulkan kesalahan seluruh mata kuliah.

### Alternatif dan Trade-off

Fungsi validasi tunggal lebih ringkas, tetapi sulit
dipelihara ketika aturan bertambah.

Rantai validator menambah abstraksi dan ketergantungan
pada urutan serta kontrak hasil pemeriksaan.

### Mitigasi

Menjaga kontrak ValidationResult, KRSContext,
urutan validator, dan pengujian setiap aturan.

## 7. ADR-002 — State Machine dan Transaksi KRS

### Keputusan

Status KRS terdiri atas draft, submitted, approved,
dan revision.

Perubahan status menggunakan aturan transisi,
optimistic versioning, dan penguncian transaksi.

Status, KRSLog, dan KRSNotification disimpan secara atomik.

### Alternatif dan Trade-off

Perubahan status langsung lebih sederhana, tetapi
berisiko menghasilkan transisi ilegal dan lost update.

Kontrol versi menambah kebutuhan pemeriksaan konflik.
Permintaan dengan versi usang dapat ditolak.

### Mitigasi

Klien membaca keadaan terbaru sebelum mencoba kembali.

Pada Minggu 8, perubahan jadwal memungkinkan aktor sistem
merevisi KRS submitted atau approved yang terdampak.
Approved tidak selalu menjadi status terminal.

## 8. UML-A — Pemodelan Berbasis Implementasi

Empat diagram PlantUML diselaraskan dengan implementasi:

- [Class Diagram](CLASS_DIAGRAM_PMB_KRS.svg).
- [Use Case Diagram](USE_CASE_PMB_KRS.svg).
- [Sequence Diagram PMB](SEQUENCE_PMB.svg).
- [Sequence Diagram KRS](SEQUENCE_KRS.svg).

Pemodelan konseptual tanpa pemeriksaan kode lebih cepat,
tetapi berisiko menyimpang dari implementasi aktual.

Diagram perlu ditinjau ketika model, kontrak API,
atau aturan bisnis mengalami perubahan.

## 9. Matriks Keputusan Inti UTS

| Keputusan | Masalah | Solusi | Trade-off / Mitigasi |
|---|---|---|---|
| PMB-A | Data tidak valid | Validasi berlapis | Koordinasi aturan dan pengujian. |
| PMB-B | NIM ganda | Counter dan transaksi | Kontensi tulis dan uji konkurensi. |
| ADR-001 | Aturan KRS kompleks | Chain of Responsibility | Menjaga urutan dan kontrak. |
| ADR-002 | Transisi ilegal dan lost update | State machine dan versioning | Penanganan konflik versi. |
| UML-A | Diagram menyimpang dari kode | PlantUML berbasis implementasi | Peninjauan berkala. |

ADR-001 dan ADR-002 mempertahankan nomor historis proyek.

PMB-A, PMB-B, dan UML-A merupakan label ringkasan
retrospektif, bukan nomor ADR historis baru.

Alternatif desain bukan klaim bahwa seluruh alternatif
pernah diimplementasikan atau diuji.

## 10. Keputusan Pelengkap Minggu 7–12

| Periode | Keputusan | Batasan |
|---|---|---|
| Minggu 7–8 | Pemeriksaan interval, grouping/sweep, Observer dan transactional outbox. | Bukan interval tree penuh atau jaminan pengiriman eksternal. |
| Minggu 9–10 | Audit nilai, IPS/IPK, dan transkrip HTML/PDF. | Kebijakan nilai tertentu memerlukan konfirmasi stakeholder. |
| Minggu 11 | Billing SPP, pembayaran manual, simulasi webhook HMAC-SHA256 dan pemeriksaan tunggakan KRS. | Bukan gateway produksi; SMTP dan scheduler perlu konfigurasi. |
| Minggu 12 | QR JWT maksimal 15 menit, validasi sesi, rate limiting dan laporan Excel. | Analitik berbasis aturan, bukan model AI eksternal. |

## 11. Bukti Pengujian dan Batasan

Verifikasi sebelum push awal menghasilkan:

- 195 pengujian lulus.
- 1 peringatan deprecation.
- Durasi pengujian: 20,37 detik.

Hasil tersebut mencakup seluruh suite proyek,
bukan jumlah pengujian khusus PMB/KRS atau code coverage.

Identitas aktor KRS melalui header API merupakan simulasi.
Admin PMB pada UML bersifat konseptual.

Notifikasi database bukan bukti pengiriman email.
Pengujian SQLite belum membuktikan perilaku MySQL multi-worker.

## 12. Referensi dan Pemeliharaan

- [ADR-001](../ADR-001-krs-validation.md).
- [ADR-002](../ADR-002-krs-state-transactions.md).
- [ADR-003](../ADR-003-scheduling-interval-tree.md).
- [ADR-004](../ADR-004-grade-policy.md).
- [Penjelasan UML](PENJELASAN_UML_FINAL_UTS.md).
- [AI Usage Log Final UTS](AI_USAGE_LOG_FINAL_UTS.md).
- [README utama](../../README.md).

Repository:
https://github.com/hyarkan/Tugas-UTS-SIAKAD-Final

Perubahan aturan bisnis, skema database, atau kontrak API
perlu diikuti peninjauan ADR, UML, dan pengujian regresi.

Dokumen ini merupakan ringkasan keputusan desain yang
diselaraskan secara retrospektif dengan implementasi.

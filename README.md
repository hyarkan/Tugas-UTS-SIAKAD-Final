# Final UTS — Sistem Informasi Akademik (SIAKAD)

### Perancangan UML, Implementasi Modul PMB & KRS, dan Pengembangan Sistem Akademik Terintegrasi

**Mata kuliah:** Pemrograman Berorientasi Objek untuk Sistem AI Agenik  
**Mahasiswa:** Muhamad Arkan Maulana  
**NIM:** 251635002  
**Program studi:** Sistem Informasi  
**Dosen pengampu:** Akhmad Daniel Sembiring, ST., MT.  
**Institusi:** Institut Sains dan Teknologi Nasional (ISTN)  
**Jenis pengumpulan:** Ujian Tengah Semester (UTS) — proyek SIAKAD

> **Fokus utama Final UTS:** Modul Penerimaan Mahasiswa Baru (PMB), Modul Kartu Rencana Studi (KRS), dan proses perancangan UML Sistem Informasi Akademik (SIAKAD). Ketiga cakupan tersebut didokumentasikan melalui laporan final UML, keputusan arsitektur (ADR), AI Usage Log, repository GitHub, dan video presentasi. Modul Minggu 7–12 menjadi pelengkap pengembangan sistem terintegrasi.

**Navigasi:** [Pendahuluan](#1-pendahuluan) · [Perjalanan Minggu 1–12](#2-perjalanan-pengembangan-minggu-112) · [Fitur](#3-fitur-dan-aturan-bisnis) · [UML](#4-perancangan-uml-final-uts) · [Arsitektur](#5-arsitektur-teknologi-dan-struktur-proyek) · [Instalasi](#6-instalasi-menjalankan-dan-menguji) · [Dokumentasi](#7-dokumentasi-pendukung-dan-batasan) · [Pengumpulan](#8-pengumpulan-final-uts)

---

## 1. Pendahuluan

SIAKAD adalah proyek aplikasi akademik terintegrasi berbasis **Python, FastAPI, SQLAlchemy 2.0, Alembic, dan SQLite**. Proyek berkembang secara bertahap dari modul Penerimaan Mahasiswa Baru (PMB) hingga Kartu Rencana Studi (KRS), penjadwalan, nilai, transkrip, keuangan SPP, dan presensi berbasis QR Code.

Pada Final UTS, pekerjaan difokuskan pada **menghubungkan perancangan UML dengan kode nyata**. Diagram menggambarkan alur pendaftaran calon mahasiswa, persetujuan dan pembuatan NIM, pengambilan mata kuliah, validasi akademik, serta pengajuan dan persetujuan KRS. Dokumentasi ini juga mencatat keputusan desain, keterbatasan prototipe, dan riwayat pengembangan agar hasil dapat diperiksa dan direproduksi.

**Cakupan:** prototipe akademik untuk pembelajaran dan demonstrasi, **bukan** sistem produksi yang siap menangani data mahasiswa atau pembayaran nyata.

## 2. Perjalanan Pengembangan Minggu 1–12

Agar kronologi mudah diikuti, tugas dikelompokkan menurut fase. Detail teknis setiap minggu tetap tersedia di README mingguan dan dokumen pendukung; tidak diduplikasi di halaman utama.

| Tahap | Fokus tugas | Implementasi / hasil utama |
|---|---|---|
| **Minggu 1–2** | Analisis dan perancangan awal SIAKAD dengan bantuan AI | Pemodelan kebutuhan, aktor, relasi kelas, use case, dan alur interaksi sebagai fondasi rancangan UML. Diagram Final UTS disusun kembali untuk mencerminkan implementasi terkini. |
| **Minggu 3–4** | Fondasi PMB dan penyempurnaan identitas mahasiswa | Registrasi dan validasi calon mahasiswa, relasi program studi/jalur masuk, status pendaftaran, approval/rejection, serta NIM unik berbasis counter dan transaksi. |
| **Minggu 5–6** | Modul KRS dan persetujuan akademik | Mata kuliah, prasyarat, batas **24 SKS**, deteksi bentrok, pola **Chain of Responsibility**, state machine KRS, optimistic versioning, log, dan notifikasi database. |
| **Minggu 7–8** | Penjadwalan dan penanganan perubahan jadwal | Ruangan, dosen, kelas, jadwal, deteksi konflik, Observer, transactional outbox, revisi KRS terdampak, resolver konflik, dan kalender `.ics`. |
| **Minggu 9–10** | Nilai dan transkrip akademik | Input dan riwayat nilai, perhitungan IPS/IPK menggunakan Decimal, kebijakan nilai, serta tampilan dan ekspor transkrip HTML/PDF. |
| **Minggu 11–12** | Keuangan dan presensi | Tagihan SPP, pembayaran manual/webhook simulasi, pemeriksaan tunggakan sebelum KRS, dashboard keuangan, QR JWT presensi, validasi sesi, laporan Excel, dan analitik berbasis aturan. |
| **Final UTS** | Konsolidasi perancangan dan pembuktian implementasi | Empat diagram UML, laporan PDF, penjelasan PMB/KRS, ADR, AI Usage Log, pengujian, repository, dan video penjelasan. |

**Prioritas pembahasan Final UTS:**

| Cakupan utama | Tahapan | Hasil |
|---|---|---|
| Modul PMB | Minggu 3–4 | Registrasi, validasi, persetujuan dan penerbitan NIM |
| Modul KRS | Minggu 5–6 | Validasi akademik, pengajuan, persetujuan dan revisi KRS |
| Perancangan UML SIAKAD | Final UTS | Class Diagram, Use Case Diagram, Sequence PMB dan Sequence KRS |

Minggu 1–2 menjadi fondasi perancangan, sedangkan Minggu 7–12 merupakan pengembangan pelengkap yang menunjukkan integrasi antarmodul.

**Catatan kronologi:** tahap Minggu 1–2 merupakan fase desain dari materi perkuliahan; pengembangan kode aplikasi terdokumentasi terutama mulai Minggu 3. Pengelompokan Minggu 3–4 merangkum perkembangan PMB, bukan klaim bahwa semua fitur selesai sekaligus pada Minggu 3.

Dokumentasi perkembangan: [Minggu 7](README_MINGGU7.md) · [Minggu 8](README_MINGGU8.md) · [Minggu 9](README_MINGGU9.md) · [Minggu 10](README_MINGGU10.md) · [Minggu 11](README_MINGGU11.md) · [Minggu 12](README_MINGGU12.md). Riwayat Minggu 3–6 dijelaskan melalui [AI Usage Log awal](AI_USAGE_LOG.md), [ADR-001](docs/ADR-001-krs-validation.md), [ADR-002](docs/ADR-002-krs-state-transactions.md), dan [verifikasi Minggu 6](docs/VERIFIKASI_MINGGU6.md).

## 3. Fitur dan Aturan Bisnis

### 3.1 PMB — Penerimaan Mahasiswa Baru

- **Registrasi:** menyimpan calon mahasiswa dengan validasi nama, email, nomor telepon, program studi, dan jalur masuk; status awal `pending`.
- **Persetujuan/penolakan:** status implementasi menggunakan `pending`, `approve`, dan `rejected`; penamaan `approve` pada database berbeda dari kata kerja *approved* dalam penjelasan umum.
- **NIM otomatis:** format **`YYYYKKKNNNN`** (11 digit), yaitu tahun persetujuan, kode program studi tiga digit, dan nomor urut empat digit per kombinasi tahun–prodi. Contoh: `20260010001`.
- **Konsistensi:** unique constraint untuk email/NIM, counter unik per tahun–prodi, approval idempotent, dan transaksi untuk mengurangi risiko nomor ganda. Pada SQLite, proses tulis memakai `BEGIN IMMEDIATE`; pada DBMS yang mendukungnya, pendekatan row locking dapat menggunakan `SELECT FOR UPDATE`.
- **Monitoring:** endpoint status dan statistik pendaftar.

| Metode | Endpoint | Fungsi |
|---|---|---|
| `POST` | `/api/pmb/register` | Registrasi calon mahasiswa (`201`) |
| `PUT` | `/api/pmb/{candidate_id}/approve` | Persetujuan dan pembuatan NIM |
| `PUT` | `/api/pmb/{candidate_id}/reject` | Penolakan pendaftaran |
| `GET` | `/api/pmb/status/{candidate_id}` | Pemeriksaan status |
| `GET` | `/api/pmb/stats` | Statistik PMB |

### 3.2 KRS — Kartu Rencana Studi

- **Pengambilan mata kuliah:** tambah/hapus mata kuliah per mahasiswa dan semester (`YYYY1` ganjil, `YYYY2` genap).
- **Rantai validator:** `Duplicate → SKS → Prerequisite → Conflict`, untuk mencegah mata kuliah ganda, beban di atas **24 SKS**, prasyarat belum lulus, dan bentrok jadwal.
- **Prasyarat:** menggunakan riwayat nilai semester sebelumnya; kelulusan diperiksa berdasarkan bobot numerik dan status lulus, bukan perbandingan alfabet nilai.
- **Alur status:** `draft → submitted → approved`, atau `submitted → revision → submitted`. Pada pengembangan Minggu 8, aktor sistem juga dapat merevisi KRS berstatus `submitted` atau `approved` ketika terjadi perubahan jadwal. Karena itu, deskripsi lama bahwa `approved` selalu terminal **tidak berlaku untuk seluruh alur versi terbaru**.
- **Keandalan:** transaksi, pemeriksaan role dan kepemilikan, optimistic versioning, audit log, notifikasi database, dan pemeriksaan tunggakan SPP pada proses tertentu.

| Metode | Endpoint | Fungsi |
|---|---|---|
| `POST` | `/api/krs/{nim}/{semester}/courses` | Menambah mata kuliah |
| `DELETE` | `/api/krs/{nim}/{semester}/courses/{kode_mk}` | Menghapus mata kuliah |
| `GET` | `/api/krs/{nim}/{semester}/validate` | Memeriksa validasi KRS |
| `POST` | `/api/krs/{nim}/{semester}/submit` | Mengajukan KRS |
| `POST` | `/api/krs/{nim}/{semester}/approve` | Persetujuan dosen PA |
| `POST` | `/api/krs/{nim}/{semester}/revise` | Mengembalikan KRS untuk revisi |
| `GET` | `/api/krs/{nim}/{semester}` | Melihat KRS dan total SKS |

**Simulasi aktor:** demonstrasi menggunakan header seperti `X-Actor-Role`, `X-Actor-NIM`, dan `X-Actor-Id`; header ini **bukan autentikasi produksi**. Operasi dosen PA mensyaratkan identitas yang sesuai dengan penugasan pada KRS.

### 3.3 Modul pendukung Minggu 7–12

| Modul | Kemampuan utama | Catatan |
|---|---|---|
| Penjadwalan | Pengelolaan dosen, ruangan, kelas, jadwal; pemeriksaan konflik dan kapasitas | Konflik memakai pemeriksaan interval serta grouping/sweep, bukan implementasi *interval tree* penuh. |
| Observer & Outbox | Menangani perubahan jadwal, mencatat event dan receipt, serta mengelola notifikasi simulasi | Pengiriman eksternal nyata tidak dijamin. |
| Nilai | Input nilai, audit perubahan, IPS/IPK, dan riwayat akademik | Kebijakan beberapa nilai masih memerlukan konfirmasi stakeholder. |
| Transkrip | Penyajian transkrip HTML dan PDF | Dokumen contoh berada di `artifacts/`. |
| Keuangan SPP | Billing, pembayaran manual, webhook HMAC-SHA256 simulasi, dashboard, pemeriksaan tunggakan | Bukan gateway pembayaran produksi. SMTP dan scheduler memerlukan konfigurasi tambahan. |
| Presensi QR | QR JWT per sesi (maksimal 15 menit), validasi KRS/jadwal, hadir/terlambat, Excel, rate limiting | Analitik kehadiran bersifat **rule-based**, bukan model AI eksternal. |

Untuk seluruh endpoint dan contoh payload modul pendukung, lihat README mingguan atau Swagger UI (`/docs`).

## 4. Perancangan UML Final UTS

Empat diagram utama disimpan sebagai **PlantUML (`.puml`)** yang dapat diedit dan **SVG (`.svg`)** untuk ditampilkan. Keduanya memiliki fungsi berbeda dan bukan file duplikat yang perlu dihapus.

| Diagram | Tujuan | Sumber | Visual |
|---|---|---|---|
| **Class Diagram PMB & KRS** | Menggambarkan entitas, atribut, relasi, dan komponen layanan/validasi | [`.puml`](docs/uml_final_uts/CLASS_DIAGRAM_PMB_KRS.puml) | [Lihat SVG](docs/uml_final_uts/CLASS_DIAGRAM_PMB_KRS.svg) |
| **Use Case PMB & KRS** | Menunjukkan aktor dan interaksi sistem | [`.puml`](docs/uml_final_uts/USE_CASE_PMB_KRS.puml) | [Lihat SVG](docs/uml_final_uts/USE_CASE_PMB_KRS.svg) |
| **Sequence PMB** | Menguraikan registrasi, validasi, persetujuan, dan hasil proses PMB | [`.puml`](docs/uml_final_uts/SEQUENCE_PMB.puml) | [Lihat SVG](docs/uml_final_uts/SEQUENCE_PMB.svg) |
| **Sequence KRS** | Menguraikan tambah mata kuliah, validasi, submit, dan approval/revision | [`.puml`](docs/uml_final_uts/SEQUENCE_KRS.puml) | [Lihat SVG](docs/uml_final_uts/SEQUENCE_KRS.svg) |

**Dokumen inti UTS:**

- **[Laporan UML Final UTS — PDF](artifacts/final_uts/LAPORAN_UML_FINAL_UTS_SIAKAD.pdf)** — laporan final 16 halaman yang mencakup timeline pengembangan, implementasi PMB/KRS, empat diagram UML, keputusan desain, dan bukti pengujian.

- **[ADR Final UTS (PDF)](artifacts/final_uts/ADR_FINAL_UTS_SIAKAD.pdf)** — dokumen 5 halaman yang membahas arsitektur, SOLID, design patterns, alternatif desain, trade-off, mitigasi, dan matriks keputusan.
- **[Penjelasan UML Final UTS](docs/uml_final_uts/PENJELASAN_UML_FINAL_UTS.md)** — dokumentasi 12 bagian yang membahas cakupan UTS, timeline, implementasi PMB/KRS, empat diagram UML, dan keterkaitan arsitektur.
- **[ADR Final UTS](docs/uml_final_uts/ADR_FINAL_UTS.md)** — dokumentasi 12 bagian mengenai keputusan arsitektur, alternatif desain, trade-off, mitigasi, dan batasan implementasi.
- **[AI Usage Log Final UTS](docs/uml_final_uts/AI_USAGE_LOG_FINAL_UTS.md)** — dokumentasi penggunaan AI, peninjauan manual, serta penyempurnaan dokumentasi Final UTS.

**Batas interpretasi UML:** diagram merupakan dokumentasi desain yang direkonstruksi dan disesuaikan terhadap kode yang berkembang. Beberapa elemen diagram dapat bersifat konseptual. Misalnya, fungsi layanan PMB pada implementasi tidak seluruhnya dibungkus dalam kelas `PMBService`; jangan menganggap setiap kotak UML adalah kelas Python yang identik. Diagram juga tidak membuktikan adanya autentikasi produksi atau entitas `User`/`Admin` yang terpisah bila belum diimplementasikan.

## 5. Arsitektur, Teknologi, dan Struktur Proyek

### 5.1 Teknologi

| Lapisan | Teknologi | Peran |
|---|---|---|
| Bahasa | Python | Implementasi aplikasi |
| API | FastAPI + Pydantic | Endpoint REST dan validasi request |
| ORM | SQLAlchemy 2.0 | Model, relasi, dan transaksi |
| Migrasi | Alembic | Versi skema database |
| Database pengembangan | SQLite | Penyimpanan dan pengujian lokal |
| Pengujian | Pytest, Hypothesis | Uji unit, integrasi, dan properti |
| UML | PlantUML | Sumber diagram yang dapat diperbarui |
| Dokumen | Markdown, PDF, SVG | Laporan dan dokumentasi |

**Alur umum:** klien/Swagger → router FastAPI → service/validator → model SQLAlchemy → database. Perubahan skema dikelola melalui Alembic. Modul tertentu menambahkan pola Chain of Responsibility, Observer/Outbox, serta pengendalian transaksi dan versi.

### 5.2 Struktur direktori

```text
siakad_final_uts/
├── app/
│   ├── models/              # Entitas PMB, KRS, jadwal, nilai, keuangan, presensi
│   ├── routers/             # Endpoint REST per modul
│   ├── services/            # Aturan bisnis dan integrasi modul
│   ├── static/              # Aset tampilan
│   ├── database.py          # Koneksi dan sesi database
│   ├── main.py              # Entry point FastAPI
│   └── seed.py              # Data referensi/demo
├── migrations/versions/     # Migrasi skema 0001–0010
├── tests/                   # Pengujian otomatis
├── docs/
│   ├── uml_final_uts/       # Sumber UML, SVG, penjelasan, ADR, AI log UTS
│   ├── ADR-*.md             # Keputusan desain per modul
│   └── OPAR_*.md            # Dokumentasi proses pengembangan
├── artifacts/
│   └── final_uts/           # PDF laporan final
├── tools/                   # Utilitas pembuatan diagram/laporan
├── README_MINGGU*.md        # Dokumentasi detail tahapan mingguan
├── AI_USAGE_LOG*.md        # Riwayat penggunaan AI
├── alembic.ini
├── requirements.txt
└── README.md                # Dokumentasi utama Final UTS
```

**Migrasi utama:** `0001` PMB, `0002` counter NIM, `0003` KRS, `0004` state machine, `0005` penjadwalan, `0006` Observer/Outbox, `0007` nilai, `0008` audit nilai, `0009` keuangan SPP, dan `0010` presensi QR. Migrasi harus dijalankan berurutan melalui Alembic, bukan membuat tabel secara manual.

## 6. Instalasi, Menjalankan, dan Menguji

### 6.1 Prasyarat

- Python yang kompatibel dengan `requirements.txt` (pengembangan lokal telah menggunakan Python 3.14).
- Git, terminal PowerShell (Windows) atau terminal setara.
- SQLite untuk lingkungan pengembangan.
- Opsional: Java/PlantUML untuk menghasilkan ulang SVG.

### 6.2 Instalasi lokal (PowerShell)

Jalankan dari folder root proyek:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Akses **Swagger UI**: `http://127.0.0.1:8000/docs` atau **ReDoc**: `http://127.0.0.1:8000/redoc`.

**Perhatian:** gunakan database pengembangan yang kosong/aman saat pertama kali melakukan migrasi dan seed. Jangan menjalankan `alembic stamp` atau `downgrade` pada database penting tanpa memahami kondisi skemanya. Jangan mengunggah `.env`, database lokal, atau kredensial.

### 6.3 Pengujian otomatis

```powershell
python -m pytest -q
```

**Hasil verifikasi sebelum push awal Final UTS:** `195 passed, 1 warning` pada lingkungan lokal. Angka tersebut merupakan hasil pengujian pada saat verifikasi, bukan jaminan bahwa setiap lingkungan selalu menghasilkan angka yang sama. Peringatan yang tercatat terkait deprecation Starlette/TestClient. Untuk coverage (jika plugin tersedia):

```powershell
python -m pytest --cov=app --cov-report=term-missing
```

Riwayat jumlah pengujian mingguan (misalnya 64, 74, 131, 170, dan 175) adalah **snapshot historis**, bukan hasil pengujian final. Pengujian SQLite belum membuktikan keamanan transaksi lintas worker pada MySQL/PostgreSQL atau kesiapan beban produksi.

### 6.4 Demonstrasi singkat PMB dan KRS

1. Jalankan migrasi, seed, dan server; buka `/docs`.
2. Daftarkan calon mahasiswa melalui `POST /api/pmb/register`, lalu periksa statusnya.
3. Lakukan approval untuk memperoleh NIM yang dapat dipakai dalam KRS.
4. Tambahkan mata kuliah pada semester valid, lalu jalankan validasi untuk melihat pemeriksaan SKS, prasyarat, dan jadwal.
5. Lakukan submit dan approval/revision dengan header aktor **khusus simulasi** dan versi KRS yang sesuai.
6. Bandingkan respons API dengan Sequence PMB/KRS dan Class Diagram pada laporan.

Gunakan **data demo**, bukan data pribadi mahasiswa nyata. Langkah detail, payload, dan contoh konfigurasi modul lanjutan tersedia pada README mingguan.

## 7. Dokumentasi Pendukung dan Batasan

### 7.1 Dokumentasi proses dan keputusan

| Dokumen | Tautan |
|---|---|
| AI Usage Log Final UTS | [Buka](docs/uml_final_uts/AI_USAGE_LOG_FINAL_UTS.md) |
| AI Usage Log awal (Minggu 3–6) | [Buka](AI_USAGE_LOG.md) |
| AI Usage Log Minggu 7–12 | [7](AI_USAGE_LOG_MINGGU7.md) · [8](AI_USAGE_LOG_MINGGU8.md) · [9](AI_USAGE_LOG_MINGGU9.md) · [10](AI_USAGE_LOG_MINGGU10.md) · [11](AI_USAGE_LOG_MINGGU11.md) · [12](AI_USAGE_LOG_MINGGU12.md) |
| ADR UTS | [Buka](docs/uml_final_uts/ADR_FINAL_UTS.md) |
| ADR KRS: validator | [ADR-001](docs/ADR-001-krs-validation.md) |
| ADR KRS: status dan transaksi | [ADR-002](docs/ADR-002-krs-state-transactions.md) |
| ADR penjadwalan | [ADR-003](docs/ADR-003-scheduling-interval-tree.md) |
| ADR kebijakan nilai | [ADR-004](docs/ADR-004-grade-policy.md) |
| OPAR yang tersedia | [Minggu 7](docs/OPAR_MINGGU7.md) · [Minggu 8](docs/OPAR_MINGGU8.md) · [Minggu 9](docs/OPAR_MINGGU9.md) |
| Verifikasi pengembangan | [Minggu 6](docs/VERIFIKASI_MINGGU6.md) · [Minggu 7](docs/VERIFIKASI_MINGGU7.md) · [Minggu 10](docs/VERIFIKASI_MINGGU10.md) |
| Sequence Observer Minggu 8 | [Buka](docs/SEQUENCE_OBSERVER_MINGGU8.md) |

**Penggunaan AI:** AI dipakai sebagai alat bantu memahami kebutuhan, menyusun alternatif desain, menghasilkan draf kode/diagram, dan membantu peninjauan. Keputusan akhir perlu dibandingkan dengan kode, pengujian, dan hasil revisi manual. Dokumentasi UTS perlu memperlihatkan **5–7 prompt terpilih**, hasil sebelum–sesudah revisi, alasan perubahan, serta bukti proses yang benar-benar tersedia; keberadaan file AI Usage Log saja tidak otomatis membuktikan seluruh butir rubrik telah terpenuhi.

### 7.2 Keputusan desain dan batasan yang perlu diketahui

- **Database:** SQLite cocok untuk demo dan tes lokal; pengujian row-level locking pada DBMS produksi dan beban multi-worker belum dibuktikan.
- **Keamanan:** header aktor KRS dan beberapa modul merupakan simulasi; tidak menggantikan login, token akses, otorisasi, dan audit produksi.
- **Notifikasi:** pencatatan di database/outbox tidak berarti email/SMS/push telah dikirim ke layanan eksternal.
- **Keuangan:** webhook dan pembayaran menggunakan simulasi; bukan integrasi transaksi uang sungguhan.
- **AI Insights:** analitik kehadiran dan keuangan yang disebut *AI* menggunakan aturan deterministik, bukan model bahasa/ML eksternal.
- **Kebijakan akademik:** aturan nilai tertentu, penugasan dosen PA, dan kalender akademik masih memerlukan penyesuaian dengan kebijakan institusi.
- **UML:** model konseptual dan implementasi harus dibedakan dengan jelas ketika presentasi.

## 8. Pengumpulan Final UTS

Dokumen ini disiapkan sebagai halaman depan repository untuk memudahkan dosen memeriksa tiga komponen pengumpulan melalui **EdLink**.

| Komponen | Tautan / status | Keterangan |
|---|---|---|
| **1. Laporan Final UML (PDF)** | **[Buka laporan PDF](artifacts/final_uts/LAPORAN_UML_FINAL_UTS_SIAKAD.pdf)** | Laporan 16 halaman mencakup PMB, KRS, timeline, perancangan empat diagram UML, dan pembahasan implementasi. |
| **2. Video penjelasan YouTube** | **Belum ditambahkan** | Tautan diisi setelah rekaman, penyuntingan, dan publikasi video. |
| **3. Repository GitHub Final UTS** | [Buka Repository GitHub](https://github.com/hyarkan/Tugas-UTS-SIAKAD-Final) | Repository resmi proyek Final UTS SIAKAD yang telah dipublikasikan, berisi kode, diagram UML, dokumentasi, dan riwayat pengembangan. |

**Dokumentasi tambahan:** [ADR PDF (5 halaman)](artifacts/final_uts/ADR_FINAL_UTS_SIAKAD.pdf) · [ADR Markdown](docs/uml_final_uts/ADR_FINAL_UTS.md) · [AI Usage Log UTS](docs/uml_final_uts/AI_USAGE_LOG_FINAL_UTS.md) · [Penjelasan UML](docs/uml_final_uts/PENJELASAN_UML_FINAL_UTS.md).

**Checklist sebelum mengirim EdLink:** pastikan seluruh tautan dapat dibuka oleh dosen, PDF final benar, video memperlihatkan proses dan penjelasan dengan suara/kamera sesuai instruksi, repository berisi kode dan dokumentasi tanpa kredensial, serta riwayat commit menggambarkan pekerjaan yang benar-benar dilakukan. **ADR PDF terpisah telah disiapkan dalam 5 halaman** sebagai dokumentasi pendukung keputusan arsitektur. Kelengkapan pengumpulan tetap mengikuti instruksi resmi dosen.

---

**Status dokumen:** README utama Final UTS SIAKAD. Laporan UML terdiri atas 16 halaman dan ADR terdiri atas 5 halaman. Repository GitHub telah dipublikasikan. Tautan YouTube akan ditambahkan setelah video dipublikasikan. Dokumentasi Minggu 1–12 tetap dipertahankan sebagai riwayat pengembangan.

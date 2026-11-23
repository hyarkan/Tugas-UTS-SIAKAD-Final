# AI Usage Log - Final UTS SIAKAD

## 1. Tujuan Penggunaan AI

AI digunakan sebagai alat bantu untuk memahami kebutuhan sistem,
menganalisis implementasi, menyusun rancangan UML, membantu
dokumentasi, serta memeriksa konsistensi antara desain dan kode.

Penggunaan AI tidak menggantikan proses verifikasi oleh mahasiswa.

## 2. Pengembangan Modul PMB (Minggu 3-4)

Tool: ChatGPT

### Fokus bantuan AI
- Perancangan model dan relasi database PMB.
- Implementasi registrasi dan validasi input.
- Approval dan rejection calon mahasiswa.
- Generator NIM, transaksi, dan pengujian.

### Bukti prompt
Prompt pengembangan PMB tercatat dalam AI_USAGE_LOG.md
bagian Minggu 3 dan Minggu 4.

### Keputusan dan revisi
- Menggunakan format NIM YYYYKKKNNNN.
- Menggunakan NIMCounter berdasarkan tahun dan kode prodi.
- Menjaga idempotensi approval.
- Menggunakan BEGIN IMMEDIATE untuk SQLite.
- Mempertahankan validasi FastAPI 422 untuk input tidak valid.

### Verifikasi historis
Minggu 4: 15 tes lulus, coverage 81,38%.

## 3. Pengembangan Modul KRS (Minggu 5-6)

Tool: ChatGPT

### Fokus bantuan AI
- Perancangan model KRS dan relasi mata kuliah.
- Validasi menggunakan Chain of Responsibility.
- Pemeriksaan SKS, prasyarat, dan bentrok jadwal.
- State machine, transaksi, approval, dan versioning.

### Bukti prompt
Prompt pengembangan KRS tercatat dalam AI_USAGE_LOG.md
bagian Minggu 5 dan Minggu 6.

### Keputusan dan revisi
- Menggunakan semester YYYY1 dan YYYY2.
- Menggunakan empat validator berurutan.
- Menetapkan batas maksimal 24 SKS.
- Memeriksa kepemilikan mahasiswa dan Dosen PA.
- Menggunakan optimistic versioning dan penguncian transaksi.
- Mencatat transisi dalam KRSLog dan KRSNotification.

### Verifikasi historis
Minggu 6: 64 tes lulus, coverage 85%.

## 4. Rekonstruksi UML Final UTS

Tool: ChatGPT dan PlantUML.

### Instruksi kerja kepada AI
Membantu menyusun Class Diagram, Use Case Diagram, dan
Sequence Diagram untuk modul PMB dan KRS berdasarkan
struktur model, service, router, dan validator yang sudah
diimplementasikan dalam proyek SIAKAD.

### Proses
1. Menginventarisasi dan membaca implementasi PMB dan KRS.
2. Mengidentifikasi class, relasi, endpoint, dan aturan bisnis.
3. Menyusun kode diagram PlantUML.
4. Memvalidasi sintaks dan merender diagram menjadi SVG.
5. Memeriksa kesesuaian diagram dengan kode.
6. Merevisi Class Diagram dengan menambahkan
   ValidationResult dan KRSContext.

### Hasil
- CLASS_DIAGRAM_PMB_KRS.puml dan SVG.
- USE_CASE_PMB_KRS.puml dan SVG.
- SEQUENCE_PMB.puml dan SVG.
- SEQUENCE_KRS.puml dan SVG.
- PENJELASAN_UML_FINAL_UTS.md.

Diagram disusun pada tahap Final UTS sebagai rekonstruksi
dan penyelarasan desain, bukan sebagai dokumen yang
diklaim telah dibuat sebelum implementasi Minggu 3.

## 5. Verifikasi dan Keterbatasan

Pengujian regresi pada salinan proyek UTS sebelumnya
menghasilkan 195 tes lulus dan satu deprecation warning.

Keberhasilan render PlantUML membuktikan sintaks diagram
dapat diproses, tetapi tidak otomatis membuktikan
seluruh relasi dan proses bisnis sudah sempurna.

Autentikasi aktor KRS masih disimulasikan melalui header API.
Notifikasi KRS masih disimpan dalam database.
Perilaku locking MySQL dan concurrency multi-worker
belum diverifikasi dalam lingkungan produksi.

## 6. Tanggung Jawab Mahasiswa

Mahasiswa bertanggung jawab memahami implementasi,
meninjau saran AI, menjalankan pengujian,
memeriksa hasil diagram, dan memastikan laporan
sesuai kondisi proyek sebenarnya.

## 7. Referensi Bukti

- AI_USAGE_LOG.md (Minggu 3-6).
- docs/ADR-001-krs-validation.md.
- docs/ADR-002-krs-state-transactions.md.
- docs/uml_final_uts/ (source dan hasil diagram).
- Hasil pengujian Pytest pada salinan proyek UTS.

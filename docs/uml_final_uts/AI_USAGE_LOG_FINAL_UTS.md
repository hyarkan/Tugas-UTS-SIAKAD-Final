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

---

## Penyempurnaan Dokumentasi Final UTS

### Tujuan Penggunaan AI

AI digunakan sebagai asisten untuk membantu penyempurnaan
dokumentasi Final UTS SIAKAD dengan fokus pada tiga cakupan:

1. Modul Penerimaan Mahasiswa Baru (PMB).
2. Modul Kartu Rencana Studi (KRS).
3. Perancangan UML Sistem Informasi Akademik.

### Aktivitas dan Hasil Penyempurnaan

| Aktivitas | Bantuan AI | Hasil |
|---|---|---|
| Revisi laporan UML | Penyempurnaan materi, timeline, struktur dan tata letak | Laporan PDF 16 halaman |
| Revisi ADR | Pengembangan pembahasan arsitektur, SOLID, design patterns, alternatif dan trade-off | ADR PDF 5 halaman |
| Sinkronisasi ADR Markdown | Penyelarasan keputusan arsitektur dan batasan implementasi | 12 bagian utama |
| Sinkronisasi dokumentasi UML | Pengembangan penjelasan PMB, KRS dan empat diagram UML | 12 bagian utama |
| Verifikasi dokumentasi | Bantuan penyusunan perintah PowerShell dan pemeriksaan output | Empat dokumen revisi teridentifikasi |

### Validasi dan Pengawasan Mahasiswa

Mahasiswa menentukan ruang lingkup revisi, memberikan
referensi format, meninjau hasil penyempurnaan PDF,
dan menjalankan perintah verifikasi melalui VS Code.

Referensi eksternal digunakan sebagai inspirasi struktur
penyajian, bukan sebagai sumber klaim implementasi proyek.

Isi dokumentasi disesuaikan dengan karakteristik proyek
SIAKAD, aturan bisnis, dan implementasi yang dikembangkan.

### Integritas Teknis

Penyempurnaan ini berfokus pada dokumentasi dan tidak
mengubah kode aplikasi maupun empat diagram UML utama.

Hasil 195 pengujian lulus merupakan bukti verifikasi
sebelum push awal, bukan hasil pengujian baru pada
saat revisi dokumentasi.

Tidak ada klaim persentase code coverage tanpa
pengukuran yang mendukung.

### Tanggung Jawab Akhir

AI berperan sebagai alat bantu penyusunan, penyempurnaan,
dan pemeriksaan dokumentasi.

Mahasiswa tetap bertanggung jawab atas pemahaman materi,
validasi hasil, keputusan akhir, serta penjelasan proyek
dalam video presentasi Final UTS.

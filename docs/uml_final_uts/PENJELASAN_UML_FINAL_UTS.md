# Dokumentasi UML Final UTS SIAKAD

## 1. Pendahuluan

Dokumentasi ini menjelaskan perancangan Unified Modeling
Language (UML) pada Sistem Informasi Akademik (SIAKAD),
dengan fokus pada Modul Penerimaan Mahasiswa Baru (PMB)
dan Kartu Rencana Studi (KRS).

Tujuan perancangan adalah mendokumentasikan struktur kelas,
tanggung jawab komponen, interaksi aktor, aturan bisnis,
dan alur komunikasi antarkomponen secara sistematis.

Diagram UML disusun sebagai rekonstruksi dan penyelarasan
desain berdasarkan implementasi proyek Minggu 3–12.
Dokumentasi ini tidak mengklaim bahwa seluruh diagram
dibuat sebelum implementasi.

## 2. Cakupan dan Timeline Pengembangan

| Tahap | Cakupan Pengerjaan | Hasil Pengembangan | Prioritas |
|---|---|---|---|
| Minggu 3–4 | Modul PMB | Registrasi, validasi, persetujuan dan penerbitan NIM | Utama UTS |
| Minggu 5–6 | Modul KRS | Validasi akademik, pengajuan, persetujuan dan revisi | Utama UTS |
| Final UTS | Perancangan UML SIAKAD | Class Diagram, Use Case Diagram dan dua Sequence Diagram | Utama UTS |
| Minggu 7–8 | Penjadwalan | Pemeriksaan konflik jadwal dan Observer | Pelengkap |
| Minggu 9–10 | Pengelolaan nilai | Nilai, IPS/IPK dan transkrip | Pelengkap |
| Minggu 11–12 | Keuangan dan presensi | Pembayaran SPP dan presensi QR Code | Pelengkap |

Timeline tersebut menggambarkan tahapan pengembangan proyek,
bukan tanggal pengerjaan harian atau durasi aktual setiap tugas.

Modul pelengkap menunjukkan perkembangan integrasi SIAKAD,
sedangkan PMB, KRS, dan perancangan UML tetap menjadi fokus
utama pembahasan Final UTS.

## 3. Gambaran Umum Modul PMB

Modul PMB mengelola proses penerimaan calon mahasiswa,
mulai dari registrasi, pemeriksaan status, persetujuan,
penolakan, hingga penerbitan NIM.

Validasi dilakukan melalui schema Pydantic, fungsi layanan,
dan constraint database. Pemeriksaan mencakup format input,
keunikan email, serta keberadaan referensi program studi
dan jalur masuk.

Pendaftar yang memenuhi persyaratan disimpan dengan status
pending. Persetujuan menghasilkan NIM dengan format
YYYYKKKNNNN menggunakan NIMCounter.

Penerbitan NIM, perubahan status approve, dan pencatatan
waktu persetujuan dilakukan dalam transaksi database.
Persetujuan berulang mengembalikan NIM yang sama untuk
menjaga idempotensi.

Status aktual PMB adalah pending, approve, dan rejected.

## 4. Gambaran Umum Modul KRS

Modul KRS mengelola pengambilan mata kuliah, validasi
rencana studi, pengajuan, persetujuan, permintaan revisi,
dan pemeriksaan detail KRS.

Validasi akademik mencakup pemeriksaan mata kuliah ganda,
batas maksimal 24 SKS, kelulusan prasyarat, dan bentrok
jadwal. Setiap aturan dipisahkan melalui pola
Chain of Responsibility.

Status KRS terdiri atas draft, submitted, approved,
dan revision. Perubahan status mengikuti aturan transisi
dan pemeriksaan versi untuk mengurangi risiko lost update.

Pencatatan KRSLog dan KRSNotification mendukung riwayat
aktivitas dan konsistensi perubahan status dalam transaksi.

## 5. Class Diagram PMB dan KRS

- [Visual Class Diagram](CLASS_DIAGRAM_PMB_KRS.svg)
- [Source PlantUML](CLASS_DIAGRAM_PMB_KRS.puml)

Class Diagram menggambarkan struktur statis sistem,
atribut, metode utama, tanggung jawab kelas, dan hubungan
antarkomponen dalam Modul PMB dan KRS.

Modul PMB mencakup CalonMahasiswa, ProgramStudi,
JalurMasuk, NIMCounter, dan representasi konseptual
layanan PMB.

ProgramStudi dan JalurMasuk menjadi referensi bagi
CalonMahasiswa. NIMCounter mengelola urutan penerbitan NIM
berdasarkan tahun dan kode program studi.

PMBService pada diagram merupakan representasi konseptual
fungsi dalam pmb_service.py, bukan class Python aktual.

Modul KRS mencakup KRS, KRSDetail, MataKuliah, SkalaNilai,
KRSLog, KRSNotification, KRSManager, dan validator yang
menerapkan pola Chain of Responsibility.

ValidationResult dan KRSContext menjadi komponen pendukung
pertukaran informasi dalam proses validasi akademik.

Pemisahan tanggung jawab tersebut mendukung modularitas,
pemeliharaan kode, dan pengujian komponen secara terarah.

## 6. Use Case Diagram PMB dan KRS

- [Visual Use Case Diagram](USE_CASE_PMB_KRS.svg)
- [Source PlantUML](USE_CASE_PMB_KRS.puml)

Use Case Diagram menggambarkan interaksi aktor dengan
fungsi sistem berdasarkan kebutuhan proses bisnis.

| Aktor | Tanggung Jawab |
|---|---|
| Calon Mahasiswa | Registrasi dan pemeriksaan status pendaftaran. |
| Admin PMB | Pengelolaan keputusan pendaftaran dan statistik PMB. |
| Mahasiswa | Pengelolaan mata kuliah, validasi dan pengajuan KRS. |
| Dosen PA | Pemeriksaan, persetujuan dan permintaan revisi KRS. |

Fungsi PMB mencakup registrasi, pemeriksaan status,
persetujuan, penolakan, statistik, dan penerbitan NIM.

Fungsi KRS mencakup penambahan dan penghapusan mata kuliah,
validasi, pengajuan, persetujuan, permintaan revisi,
serta pemeriksaan detail KRS.

Admin PMB dan Dosen PA dimodelkan sebagai aktor dengan
tanggung jawab yang jelas dalam proses bisnis.

Identitas aktor KRS melalui header API digunakan untuk
menguji aturan kewenangan dan alur bisnis. Autentikasi
produksi merupakan tahap penguatan keamanan tersendiri.

## 7. Sequence Diagram PMB

- [Visual Sequence Diagram PMB](SEQUENCE_PMB.svg)
- [Source PlantUML](SEQUENCE_PMB.puml)

Sequence Diagram PMB menggambarkan urutan interaksi
Calon Mahasiswa, Admin PMB, FastAPI Router,
fungsi layanan PMB, dan database.

### 7.1 Alur Registrasi

Proses dimulai ketika calon mahasiswa mengirimkan data
pendaftaran melalui endpoint registrasi.

Sistem memvalidasi input, memeriksa keunikan email,
dan memastikan referensi program studi serta jalur masuk
tersedia. Data yang valid disimpan dengan status pending.

### 7.2 Alur Persetujuan dan Penerbitan NIM

Sistem memeriksa status pendaftar sebelum menerbitkan NIM.
NIMCounter digunakan untuk mengelola urutan nomor.

NIM, status approve, dan approve_at disimpan dalam
transaksi database untuk menjaga konsistensi perubahan.

### 7.3 Alur Alternatif

Diagram memperlihatkan kondisi alternatif, termasuk
email duplikat, referensi tidak valid, dan konflik status.

Pemisahan alur utama dan alternatif membantu menjelaskan
perilaku sistem ketika permintaan tidak memenuhi aturan.

## 8. Sequence Diagram KRS

- [Visual Sequence Diagram KRS](SEQUENCE_KRS.svg)
- [Source PlantUML](SEQUENCE_KRS.puml)

Sequence Diagram KRS menggambarkan komunikasi antarkomponen
selama penambahan mata kuliah, pengajuan KRS, dan
persetujuan oleh Dosen PA.

### 8.1 Alur Validasi Mata Kuliah

| Urutan | Validator | Tanggung Jawab |
|---|---|---|
| 1 | DuplicateValidator | Memeriksa mata kuliah ganda. |
| 2 | SKSValidator | Memeriksa batas maksimal 24 SKS. |
| 3 | PrerequisiteValidator | Memeriksa kelulusan prasyarat. |
| 4 | ConflictValidator | Memeriksa bentrok jadwal. |

Validator dijalankan melalui Chain of Responsibility.
Pemisahan aturan memungkinkan setiap validator diuji
dan dipelihara secara terpisah.

Operasi add_course menggunakan pendekatan fail-fast,
sedangkan validate_krs mengumpulkan kesalahan dari
pemeriksaan seluruh mata kuliah.

### 8.2 Alur Pengajuan dan Persetujuan

Proses pengajuan dan persetujuan mencakup pemeriksaan
status, versi data, dan persyaratan akademik yang relevan.

Perubahan status mengikuti aturan State Machine.
Kontrol versi membantu mendeteksi perubahan bersamaan.

Setiap transisi yang berhasil dicatat melalui KRSLog
dan KRSNotification dalam transaksi database.

### 8.3 Alur Alternatif dan Integrasi

Kondisi alternatif mencakup kegagalan validasi,
transisi status tidak sah, dan konflik versi.

Integrasi penjadwalan Minggu 8 memungkinkan KRS yang
terdampak perubahan jadwal dikembalikan ke status revision
sesuai aturan sistem.

Notifikasi yang tercatat dalam database tidak berarti
pengiriman email eksternal telah berhasil dilakukan.

## 9. Keterkaitan UML dan Keputusan Arsitektur

| Keputusan | Keterkaitan dengan UML |
|---|---|
| Validasi PMB berlapis | Struktur schema, layanan dan alur registrasi. |
| NIMCounter dan transaksi | Class Diagram dan Sequence Diagram PMB. |
| Chain of Responsibility | Struktur validator dan Sequence Diagram KRS. |
| State Machine | Alur pengajuan, persetujuan dan revisi KRS. |
| Optimistic versioning | Pemeriksaan konflik perubahan data KRS. |
| Pemisahan layer | Pembagian tanggung jawab antarkomponen. |

Pembahasan alternatif desain, SOLID, trade-off, dan
mitigasi dijelaskan lebih lanjut dalam dokumen ADR.

- [ADR Final UTS Markdown](ADR_FINAL_UTS.md)
- [ADR Final UTS PDF](../../artifacts/final_uts/ADR_FINAL_UTS_SIAKAD.pdf)

## 10. Implementasi dan Bukti Pengujian

Implementasi menggunakan FastAPI, Pydantic, SQLAlchemy,
SQLite, Alembic, dan Pytest.

Verifikasi sebelum push awal menghasilkan:

| Indikator | Hasil |
|---|---|
| Pengujian berhasil | 195 |
| Pengujian gagal | 0 |
| Peringatan deprecation | 1 |
| Durasi pengujian | 20,37 detik |
| Commit pada push awal | 10 |
| File terlacak pada push awal | 134 |

Hasil tersebut mencakup seluruh suite pengujian proyek,
bukan jumlah pengujian khusus PMB dan KRS atau persentase
code coverage.

Pengujian SQLite tidak membuktikan kesiapan seluruh
skenario konkurensi pada database produksi.

## 11. Kesimpulan

Perancangan UML mendokumentasikan struktur kelas,
interaksi aktor, dan urutan proses bisnis SIAKAD
secara sistematis.

Modul PMB menunjukkan penerapan validasi berlapis,
pengelolaan status, dan penerbitan NIM yang konsisten.
Modul KRS menunjukkan penerapan Chain of Responsibility,
State Machine, kontrol versi, dan transaksi database.

Keempat diagram UML menjadi dasar penjelasan hubungan
antara rancangan sistem dan implementasi aktual dalam
laporan serta video presentasi Final UTS.

Modul Minggu 7–12 menjadi pelengkap pengembangan dan
tidak menggantikan tiga cakupan utama tugas UTS.

## 12. Dokumen dan Referensi Final UTS

- [Laporan Final UML SIAKAD - PDF](../../artifacts/final_uts/LAPORAN_UML_FINAL_UTS_SIAKAD.pdf)
- [ADR Final UTS - PDF](../../artifacts/final_uts/ADR_FINAL_UTS_SIAKAD.pdf)
- [ADR Final UTS - Markdown](ADR_FINAL_UTS.md)
- [AI Usage Log Final UTS](AI_USAGE_LOG_FINAL_UTS.md)
- [README Proyek](../../README.md)

Repository GitHub:
https://github.com/hyarkan/Tugas-UTS-SIAKAD-Final

Video YouTube:
Tautan akan dilengkapi setelah video presentasi dipublikasikan.

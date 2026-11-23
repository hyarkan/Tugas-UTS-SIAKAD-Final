# Dokumentasi UML Final UTS SIAKAD

## 1. Pendahuluan

Dokumentasi ini menjelaskan perancangan Unified Modeling Language (UML)
pada Sistem Informasi Akademik (SIAKAD), dengan fokus pada Modul
Penerimaan Mahasiswa Baru (PMB) dan Kartu Rencana Studi (KRS).

Diagram UML disusun sebagai rekonstruksi dan penyelarasan desain
berdasarkan implementasi proyek yang dikembangkan pada Minggu 3–12.
Dokumentasi ini tidak dimaksudkan sebagai klaim bahwa diagram dibuat
sebelum implementasi.

## 2. Class Diagram PMB dan KRS

File: CLASS_DIAGRAM_PMB_KRS.svg

Class Diagram menggambarkan struktur data, class, metode utama,
dan hubungan antarkomponen dalam Modul PMB dan KRS.

Modul PMB mencakup CalonMahasiswa, ProgramStudi, JalurMasuk,
NIMCounter, serta fungsi layanan PMB yang ditampilkan secara konseptual.

Modul KRS mencakup KRS, KRSDetail, MataKuliah, SkalaNilai,
KRSLog, KRSNotification, KRSManager, serta validator yang
menerapkan pola Chain of Responsibility.

ValidationResult dan KRSContext digunakan sebagai komponen pendukung
proses validasi KRS.

## 3. Use Case Diagram PMB dan KRS

File: USE_CASE_PMB_KRS.svg

Use Case Diagram menjelaskan interaksi aktor dengan fungsi sistem.

Aktor konseptual yang digunakan adalah Calon Mahasiswa, Admin PMB,
Mahasiswa, dan Dosen Pembimbing Akademik (Dosen PA).

Fungsi PMB meliputi registrasi, pemeriksaan status, persetujuan,
penolakan, statistik pendaftaran, dan penerbitan NIM.

Fungsi KRS meliputi penambahan dan penghapusan mata kuliah,
validasi, pengajuan, persetujuan, permintaan revisi, serta
pemeriksaan detail KRS.

Peran aktor menggambarkan proses bisnis. Diagram ini tidak
menyatakan bahwa autentikasi pengguna produksi sudah diterapkan.

## 4. Sequence Diagram PMB

File: SEQUENCE_PMB.svg

Sequence Diagram PMB menjelaskan interaksi antara Calon Mahasiswa,
Admin PMB, FastAPI Router, fungsi layanan PMB, dan database.

Proses dimulai dari registrasi calon mahasiswa, pemeriksaan email,
validasi referensi program studi dan jalur masuk, hingga penyimpanan
pendaftar dengan status pending.

Pada proses persetujuan, sistem memeriksa status pendaftar,
menghasilkan NIM menggunakan NIMCounter, lalu menyimpan NIM,
status approve, dan waktu persetujuan dalam transaksi database.

Diagram juga menunjukkan beberapa kondisi gagal, seperti email
yang telah digunakan, referensi tidak valid, dan konflik status.

## 5. Sequence Diagram KRS

File: SEQUENCE_KRS.svg

Sequence Diagram KRS menggambarkan proses penambahan mata kuliah,
pengajuan KRS, dan persetujuan oleh Dosen PA.

Validasi mata kuliah menggunakan pola Chain of Responsibility
dengan urutan DuplicateValidator, SKSValidator,
PrerequisiteValidator, dan ConflictValidator.

Proses pengajuan dan persetujuan mencakup pemeriksaan status,
versi data, serta persyaratan akademik yang relevan.

Setiap transisi status yang berhasil dicatat melalui KRSLog
dan KRSNotification dalam transaksi database.

Identitas aktor KRS saat ini disimulasikan menggunakan header API,
sedangkan notifikasi disimpan pada database.

## 6. Kesimpulan

Keempat diagram UML digunakan untuk mendokumentasikan struktur,
interaksi pengguna, dan alur proses bisnis Modul PMB dan KRS.

Dokumentasi ini menjadi dasar penjelasan perancangan sistem
dalam laporan dan video presentasi Final UTS.

## 7. Daftar Diagram

1. CLASS_DIAGRAM_PMB_KRS.svg
2. USE_CASE_PMB_KRS.svg
3. SEQUENCE_PMB.svg
4. SEQUENCE_KRS.svg

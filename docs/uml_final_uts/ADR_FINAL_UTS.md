# Architecture Decision Record (ADR) — Final UTS SIAKAD

## Identitas
Sistem: Sistem Informasi Akademik (SIAKAD)
Cakupan: Modul PMB dan KRS
Status: Ringkasan keputusan desain yang telah diterapkan
Sumber: ADR-001 dan ADR-002 pada folder docs

## ADR-001 — Strategi Validasi KRS

### Konteks
Penambahan mata kuliah memerlukan pemeriksaan duplikasi,
batas SKS, mata kuliah prasyarat, dan bentrok jadwal.

### Keputusan
Validasi menggunakan pola Chain of Responsibility dengan urutan:
DuplicateValidator -> SKSValidator -> PrerequisiteValidator
-> ConflictValidator.

Operasi add_course berhenti pada kegagalan pertama.
Operasi validate_krs memeriksa seluruh mata kuliah dan
mengumpulkan pesan kesalahan.

### Alasan
Urutan tersebut mendahulukan pemeriksaan sederhana sebelum
validasi yang lebih kompleks. Pemisahan validator juga
memudahkan pengujian dan pemeliharaan kode.

### Konsekuensi
Setiap validator perlu menjaga kontrak hasil pemeriksaan
agar rantai validasi berjalan konsisten.

## ADR-002 — State Machine dan Transaksi KRS

### Konteks
Pengajuan dan persetujuan KRS harus menjaga konsistensi status,
mencegah perubahan oleh aktor yang tidak sesuai, dan menangani
konflik pembaruan data.

### Keputusan
KRS menggunakan status draft, submitted, approved, dan revision.

Perubahan status mengikuti aturan transisi yang ditentukan.
Pengajuan dan persetujuan menggunakan pemeriksaan versi data
(optimistic locking) serta penguncian transaksi database.

Perubahan status, KRSLog, dan KRSNotification disimpan
dalam satu transaksi.

### Alasan
Pendekatan ini membantu mencegah transisi tidak sah,
mengurangi risiko konflik pembaruan, dan menjaga konsistensi
catatan aktivitas dengan status KRS.

### Konsekuensi dan Batasan
Permintaan dengan versi data lama dapat ditolak.
Identitas aktor saat ini disimulasikan melalui header API,
sehingga belum setara dengan autentikasi produksi.

Notifikasi dicatat dalam database dan belum otomatis
dikirim melalui layanan email eksternal.

## Kesimpulan
Kedua keputusan desain mendukung validasi akademik yang
terstruktur dan perubahan status KRS yang konsisten.

Dokumen ini merupakan ringkasan ADR yang sudah tersedia,
bukan klaim keputusan baru yang dibuat sebelum implementasi.

# ADR-001: Urutan dan perilaku validasi KRS

- **Status:** Diterima
- **Konteks:** Penambahan mata kuliah harus memberi umpan balik yang jelas dan menghindari query mahal bila pemeriksaan sederhana sudah gagal.
- **Keputusan:** Urutan rantai `Duplicate → SKS → Prerequisite → Conflict`. `add_course` berhenti pada kegagalan pertama. `validate_krs` memeriksa semua mata kuliah pada kartu dan mengumpulkan pesan kesalahan.
- **Alternatif:** Mengikuti urutan dokumen secara literal (`SKS → Prerequisite → Conflict → Duplicate`) atau selalu mengumpulkan seluruh kegagalan dalam setiap operasi.
- **Alasan:** Duplikasi murah diperiksa tanpa query tambahan. Berhenti lebih awal efisien untuk satu operasi tambah. Validasi seluruh kartu membutuhkan daftar kesalahan lengkap agar mahasiswa dapat memperbaiki beberapa masalah sekaligus.
- **Konsekuensi:** Urutan berbeda dari urutan daftar di dokumen tugas, tetapi sejalan dengan alternatif yang dijelaskan dosen dalam video. Perilaku ini harus dipertahankan dalam tes.

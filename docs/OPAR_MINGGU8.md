# OPAR — Minggu 8

## Observe
Kode Minggu 7 memiliki CRUD jadwal, capacity check, konflik, serta `krs_detail.kelas_id`, tetapi belum memiliki notifikasi perubahan dan invalidasi KRS.

## Plan
Observer tiga penerima dan kanal log, transactional outbox, KRSInvalidator melalui transisi `sistem`, saran jadwal tersaring, UI admin sederhana, ekspor ICS, dan tes.

## Act
Tambahkan migration 0006, event snapshot sebelum/sesudah, dispatcher pasca-commit, endpoint saran/filter/apply, diagram sequence dan dokumentasi.

## Reflect
Perubahan jadwal harus atomik dengan KRS dan outbox; kegagalan notifikasi tidak boleh membatalkan commit. Saran AI tidak boleh melewati validasi. Header role demo belum autentikasi produksi; concurrency SQLite lintas worker belum terbukti.

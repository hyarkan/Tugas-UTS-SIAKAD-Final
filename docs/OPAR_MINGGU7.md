# OPAR Minggu 7

## Objective
Mengembangkan modul penjadwalan dari KRS Minggu 6 untuk menolak bentrok ruangan/dosen dan kelebihan kapasitas, serta melaporkan bentrok impor.

## Plan
Tambahkan migrasi `0005`, model Ruangan/Dosen/Kelas/Jadwal, dua detektor, service dengan locking, 4 endpoint, seed, pengujian contoh dan dua properti.

## Action
Implementasi tersedia di `app/models/scheduling.py`, `app/services/`, `app/routers/scheduling.py`, `app/seed_scheduling.py`, `tests/`, dan ADR-003. Migrasi KRSDetail.kelas_id nullable agar data lama tetap valid.

## Reflection / Risk
- Perbedaan spesifikasi: `time_overlap` bukan konflik menurut penjelasan video; hanya dua tipe dilaporkan.
- `FOR UPDATE` tidak bekerja pada SQLite; gunakan BEGIN IMMEDIATE untuk serialisasi penulis SQLite.
- Penghitungan peserta mencakup KRS submitted/approved yang telah memiliki `kelas_id`, bukan seluruh peserta legacy tanpa kelas.
- Endpoint belum memiliki autentikasi/otorisasi admin; tambahkan sebelum produksi.
- Semester aktif belum difilter; kebutuhan lintas semester perlu model periode akademik.
- Perubahan jadwal belum mengirim notifikasi / invalidasi KRS: fokus Minggu 8.
- Bukti benchmark dan tes concurrency PostgreSQL/MySQL perlu dijalankan di lingkungan sesuai.

# Tugas Minggu 11 — Modul Keuangan (SPP)

**Nama:** Muhamad Arkan Maulana  
**NIM:** 251635002  
**Prodi:** S1 Sistem Informasi  
**Kelas:** A  
**Mata kuliah:** Pemrograman Berorientasi Objek untuk Sistem AI Agenik

Proyek ini merupakan **kelanjutan source code Minggu 3–10**, bukan aplikasi yang ditulis ulang. Fitur lama PMB, KRS, penjadwalan, nilai, dan transkrip dipertahankan.

## Fitur Minggu 11 sesuai PDF dosen

1. **Payment schema:** `billing`, `payment`, `payment_method`, plus `finance_notification`. Status `unpaid`, `partial`, `paid`, `overdue`. Migrasi Alembic `0009_finance_spp`.
2. **Billing service:** generate idempoten per NIM dan semester, tarif Teknik/Sistem Informasi Rp5.000.000 dan Ekonomi Rp4.000.000, jatuh tempo 14 hari, pembayaran manual/webhook, denda keterlambatan, blokir tambah mata kuliah/submit KRS bila ada tagihan semester berjalan belum lunas atau tunggakan jatuh tempo.
3. **Dashboard:** JSON real-time dari database serta halaman `/finance-dashboard` (tabel per mahasiswa dan prodi, grafik batang pembayaran bulanan, refresh 15 detik).
4. **Webhook gateway simulasi:** HMAC-SHA256 pada *raw request body*, idempotensi `transaction_id`, pencatatan pembayaran dalam transaksi, antrean kuitansi email. SMTP opsional untuk benar-benar mengirim email.
5. **AI financial report:** analisis deterministik berbasis aturan dan CSV `nim,jumlah,tanggal,status`, hasil JSON (pendapatan bulan berjalan, collection rate, 10 tunggakan terbesar, rekomendasi reminder). **Ini simulasi analitik AI, bukan integrasi LLM eksternal.**
6. **Scheduled jobs:** APScheduler opsional untuk billing awal semester (contoh 1 September dan 1 Februari), pengecekan denda, reminder harian, dan pengiriman antrean email bila SMTP tersedia.

## Cara menjalankan (Windows PowerShell, dari folder proyek)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Buka `http://127.0.0.1:8000/docs` dan `http://127.0.0.1:8000/finance-dashboard`.

**Penting:** Jangan gunakan database asli tanpa backup terlebih dahulu. Migrasi `0009` menambahkan tabel baru; tidak menghapus tabel lama. Paket ZIP ini **tidak menyertakan database pengguna**.

## Alur demo cepat via Swagger UI

Header admin demo untuk endpoint keuangan: `X-Demo-Admin-Key: demo-admin-key-change-me`. Sebaiknya ubah melalui `FINANCE_ADMIN_KEY` di environment sebelum menjalankan.

1. Siapkan mahasiswa dengan status PMB *approve* dan NIM, menggunakan endpoint PMB yang sudah ada. Bila tidak ada mahasiswa bernomor NIM, generator menghasilkan nol tagihan.
2. `POST /api/finance/methods/seed` untuk menambah metode `manual` dan `gateway`.
3. `POST /api/finance/billing/generate` dengan `{"semester":"20261","semester_start":"2026-09-01"}`.
4. `GET /api/finance/billing` untuk melihat `billing_id`.
5. `POST /api/finance/payments/manual` dengan `{"billing_id":1,"amount":"1000000","method":"manual"}`; status menjadi `partial`. Lunasi sisanya untuk `paid`.
6. `GET /api/finance/dashboard` dan `/api/finance/report`, atau halaman dashboard.
7. `POST /api/finance/reminders/run` untuk mengantrikan pengingat tagihan yang melewati jatuh tempo. `POST /api/finance/billing/penalties` untuk mengenakan denda.
8. Untuk uji webhook, gunakan skrip `demo_webhook.py` (menghasilkan signature dan memanggil API), atau curl dengan signature HMAC-SHA256 dari raw body yang identik.

## Simulasi webhook

```powershell
python demo_webhook.py 1 5000000 trx-demo-001
```

Perintah ini memerlukan server berjalan, metode `gateway` sudah di-seed, dan tagihan ID 1 belum lunas. Secret default hanya untuk demo; ubah `PAYMENT_WEBHOOK_SECRET` pada lingkungan nyata.

## Konfigurasi scheduler dan email

Set sebelum menjalankan server:

```powershell
$env:FINANCE_ADMIN_KEY="ganti-dengan-kunci-admin-kuat"
$env:PAYMENT_WEBHOOK_SECRET="ganti-dengan-secret-webhook-kuat"
$env:FINANCE_SCHEDULER_ENABLED="1"
```

Scheduler hanya berjalan selama proses aplikasi aktif. **Jangan jalankan beberapa worker atau `--reload` dengan scheduler diaktifkan**, karena bisa menggandakan eksekusi job. Kalender semester September/Februari hanyalah asumsi demo; sesuaikan kalender kampus.

Untuk email sungguhan, konfigurasi `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USER`, `SMTP_PASSWORD`, dan `SMTP_STARTTLS`. Tanpa SMTP, kuitansi dan reminder disimpan pada tabel `finance_notification` sebagai **antrean simulasi** dan bisa dilihat di `GET /api/finance/notifications`; email **tidak dikirim**. Setelah SMTP disiapkan, gunakan `POST /api/finance/notifications/send` atau aktifkan scheduler.

## Kebijakan demo dan batasan

- **Denda 1% dari tagihan pokok sekali saat terlambat** adalah asumsi implementasi karena PDF tidak menentukan tarif/rumus denda.
- Tarif default untuk prodi yang namanya mengandung Teknik/Informatika/Sistem Informasi atau fakultas FSTI = Teknik; Ekonomi = Rp4 juta; prodi lainnya ditolak sampai tarif dikonfigurasi.
- Status `overdue` digunakan untuk tagihan belum dibayar setelah jatuh tempo; pembayaran sebagian ditandai `partial`. Denda dikenakan hanya melalui job atau endpoint penilaian denda.
- Dashboard/API menampilkan data terkini ketika diminta, bukan streaming WebSocket.
- Sistem autentikasi admin masih **shared demo header**, bukan login/otorisasi produksi. Webhook memakai secret HMAC demo dan tidak menghubungi gateway sungguhan.
- Pengiriman email menggunakan SMTP opsional, bukan email gateway sungguhan. Tidak ada janji pengiriman jika SMTP tidak diatur.
- Laporan AI menggunakan analitik aturan yang dapat diaudit, bukan panggilan model AI eksternal.
- Transaksi SQLite cocok untuk demo lokal; untuk multi-worker/produksi perlu DB dan locking yang sesuai, penyimpanan kunci aman, rate limiting, queue worker, serta audit yang lebih lengkap.

## Pengujian

```powershell
pytest -q tests/test_finance_week11.py
pytest -q
```

Pada lingkungan pembuatan arsip ini, pengujian Minggu 11 lulus **4/4** dan pengujian yang dapat dijalankan (tanpa tiga berkas yang memerlukan `hypothesis`) lulus **122/122**. **Full suite belum berhasil dijalankan di lingkungan ini karena paket `hypothesis` tidak terpasang dan akses instalasi jaringan tidak tersedia.** Jalankan `pip install -r requirements.txt` lalu `pytest -q` pada komputer Anda untuk verifikasi penuh.

## File tambahan Minggu 11

- `app/models/finance.py`
- `app/services/finance.py`
- `app/services/finance_scheduler.py`
- `app/routers/finance.py`
- `app/finance_dashboard.html`
- `migrations/versions/0009_finance_spp.py`
- `tests/test_finance_week11.py`
- `demo_webhook.py`
- `AI_USAGE_LOG_MINGGU11.md`

# Tugas Minggu 8 — Observer, KRS Invalidation, AI Conflict Resolver & Kalender

Proyek ini adalah kelanjutan **utuh** Minggu 3–7. Modul Minggu 7 tidak dihapus.

## Instalasi Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m app.seed
python -m app.seed_scheduling
python -m uvicorn app.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs. Dashboard admin: http://127.0.0.1:8000/api/jadwal/admin/conflict-resolver

## Fitur Minggu 8

1. `ScheduleSubject.attach/detach/notify` dengan tiga observer mahasiswa/dosen/admin dan kanal Email/SMS/Push berbasis `logging`.
2. `ScheduleOutbox` + `DeliveryReceipt` + `OutboxDispatcher` dengan percobaan ulang maksimal lima kali dan idempotency key.
3. `KRSInvalidator` untuk `submitted`/`approved` ke `revision` melalui `KRS.transition(..., 'sistem')`; audit log dan notifikasi KRS ikut dalam transaksi jadwal.
4. Conflict Resolver UI, daftar bentrok, rekomendasi alternatif deterministik dan integrasi penyedia AI opsional; setiap saran disaring berdasarkan slot nyata dan diperiksa ulang saat diterapkan.
5. Ekspor iCalendar `.ics` mingguan dengan UID stabil dan SEQUENCE yang berubah mengikuti perubahan jadwal. Ekspor menggunakan `TZID=Asia/Jakarta` untuk DTSTART/DTEND, komponen VTIMEZONE, RRULE mingguan dengan UNTIL dalam UTC, escaping karakter khusus, dan line folding maksimal 75 octet.
6. Sequence diagram di `docs/SEQUENCE_OBSERVER_MINGGU8.md`, OPAR dan AI Usage Log.

## Endpoint baru

| Method | Path | Keterangan |
|---|---|---|
| GET | `/api/jadwal/admin/conflict-resolver` | Dashboard demo |
| GET | `/api/jadwal/{id}/suggestions` | Slot + maksimal 3 saran; header `X-Actor-Role: admin_akademik` |
| POST | `/api/jadwal/{id}/filter-suggestions` | Validasi JSON `{"suggestions": [...]}`; header admin |
| POST | `/api/jadwal/{id}/apply-suggestion` | Terapkan melalui SchedulingService; header admin |
| POST | `/api/jadwal/outbox/dispatch` | Coba ulang event pending; header admin |
| GET | `/api/jadwal/calendar/export.ics?start=2026-09-01&end=2026-12-31` | Download kalender semester |

Endpoint CRUD dan konflik Minggu 7 tetap tersedia. Pada contoh ini header role merupakan **simulasi otorisasi**, bukan autentikasi produksi; endpoint CRUD legacy belum dilindungi role admin. Tambahkan autentikasi sebenarnya sebelum dipakai di lingkungan nyata.

## AI scheduling

Secara default, rekomendasi menggunakan algoritma deterministik (mode offline) agar demo tetap dapat digunakan tanpa kredensial API. Untuk memakai model AI OpenAI-compatible, set variabel lingkungan:

```powershell
$env:SCHEDULING_AI_ENDPOINT = 'https://YOUR_PROVIDER/v1/chat/completions'
$env:SCHEDULING_AI_MODEL = 'YOUR_MODEL'
$env:SCHEDULING_AI_API_KEY = 'YOUR_KEY'
```

Jangan commit API key. Prompt sesuai Step 3 PDF, hasil AI harus berupa JSON dan selalu melewati `saring_saran`. Respons endpoint mencantumkan `source=ai_validated` atau `deterministic_fallback`. **Integrasi provider AI eksternal belum diuji live** di paket ini.

Jika penyedia AI tidak tersedia, gagal, atau mengembalikan daftar kosong meskipun masih ada slot valid, endpoint menggunakan `deterministic_suggestions()` sebagai fallback. Bila tidak ada slot tersedia, rekomendasi tetap berupa daftar kosong. Fallback hanya mengubah pemilihan dan sumber rekomendasi; aturan validasi slot, kapasitas, dan bentrok tetap sama.

Rekomendasi deterministik memakai pendekatan **minimal disruption**. Urutan hasil diprioritaskan berdasarkan hari yang sama, selisih jam mulai yang terkecil, dan ruangan yang sama. Jarak hari serta urutan hari, jam, dan kode ruangan menjadi penentu lanjutan ketika prioritas sebelumnya sama. Maksimal tiga rekomendasi valid dikembalikan dalam urutan deterministik. Pendekatan ini membandingkan slot rekomendasi dengan jadwal asli; sistem tidak menghitung atau mengoptimalkan seluruh jadwal individual mahasiswa.

## Deteksi konflik Minggu 7–8

Deteksi konflik memakai **balanced interval tree per hari dan sumber daya**. Struktur pohon disusun dari interval jadwal berdasarkan waktu mulai, dengan nilai `max_end` pada setiap subtree untuk menyimpan waktu selesai terbesar di bawah node tersebut. Saat pencarian interval, subtree dipangkas jika `max_end <= waktu_mulai_pencarian`, sehingga interval yang hanya bersentuhan pada batas setengah terbuka tidak dianggap overlap. Pohon digunakan secara terpisah untuk grup hari dan ruangan maupun hari dan dosen.

`time_overlap` merupakan kondisi dasar bagi konflik sumber daya dan tidak dihasilkan sebagai tipe konflik tersendiri, karena aturan dosen tidak menetapkan konflik sumber daya khusus untuk kategori tersebut. Hasil detektor tetap menggunakan `room_conflict` untuk ruangan yang sama dan `lecturer_conflict` untuk dosen yang sama; pasangan yang menggunakan ruangan dan dosen sama dapat menghasilkan kedua tipe konflik sekaligus. Jadwal di hari berbeda maupun pasangan dengan ruangan dan dosen berbeda tidak menghasilkan konflik.

## Konsistensi kapasitas

Validasi ruang pada rekomendasi AI Rescheduling menggunakan aturan yang sama dengan `SchedulingService._check_capacity()`:

```text
required = max(kelas.kuota, enrolled)
```

Nilai `enrolled` adalah jumlah mahasiswa unik berdasarkan `KRS.nim`, melalui `KRSDetail.kelas_id` untuk kelas yang bersangkutan, dengan status KRS hanya `submitted` atau `approved`. Ruangan yang cukup untuk kuota tetapi tidak cukup untuk jumlah mahasiswa terdaftar tidak ditampilkan sebagai pilihan.

## Demo singkat

1. Seed jadwal; buka dashboard untuk daftar konflik dan saran.
2. Update jadwal yang sudah terhubung ke `krs_detail.kelas_id` (kelas lama/baru).
3. Periksa `schedule_outbox` status `sent`, `schedule_delivery_receipt`, serta log `app.schedule.notifications`.
4. Periksa KRS `submitted/approved` yang terdampak berubah menjadi `revision` dan audit `krs_log`.
5. Ekspor `.ics`, periksa UID, SEQUENCE dan RRULE mingguan.

**Penting:** `krs_detail.kelas_id` bersifat opsional dari Minggu 7. KRS tanpa hubungan kelas tidak dapat diidentifikasi untuk invalidasi spesifik; pada demo harus ditautkan terlebih dahulu. Seed Minggu 7 tidak otomatis menciptakan KRS enrolled.

## Testing

```powershell
python -m pytest -q
python -m alembic check
```

Hasil pengujian terbaru pada Windows dengan Python 3.14: **105 passed, 1 warning in 14.24s**. Seluruh pengujian, termasuk pengujian berbasis Hypothesis, berhasil dijalankan. Pengujian tambahan `test_saring_saran_rejects_actual_schedule_conflict` berhasil memverifikasi penolakan saran AI yang berbenturan dengan jadwal nyata. Satu warning adalah `StarletteDeprecationWarning` terkait TestClient dan bukan kegagalan pengujian. Ekspor kalender juga telah diuji melalui endpoint FastAPI dan berhasil menghasilkan 40 event untuk periode 1 September 2026 sampai 31 Desember 2026. Hasil `alembic check` yang tercatat sebelumnya berhasil pada SQLite baru; **`alembic check` belum dijalankan ulang** sebagai bagian dari hasil pengujian terbaru ini.

## Batasan desain

- Observer diproses dalam satu proses; **bukan** message broker Pub-Sub.
- SQLite tidak menyediakan `SKIP LOCKED` yang efektif; dispatcher demo diasumsikan satu worker. Untuk multi-worker perlu mekanisme claim atomik pada DB yang mendukung row locking.
- Simulasi kanal log dan receipt memberi deduplikasi lokal, bukan jaminan exactly-once pada gateway eksternal.
- Dispatcher dijalankan setelah commit dalam request demo; untuk produksi sebaiknya worker terpisah.
- Pengujian impor langsung untuk kompatibilitas kalender dengan Google Calendar atau Outlook belum dilakukan.
- Pilihan slot jam pada demo: 08:00, 10:00, 13:00, 15:00 untuk hari Senin–Sabtu. Ini konfigurasi contoh, bukan kalender akademik resmi.
- Pengujian concurrency multi-worker, integrasi email/SMS/push sungguhan, AI live, dan acceptance UI browser lintas perangkat belum dilakukan.

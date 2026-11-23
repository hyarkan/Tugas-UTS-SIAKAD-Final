# AI Usage Log — Minggu 7

| Komponen | Bantuan AI | Pemeriksaan/revisi manual yang diperlukan |
|---|---|---|
| Domain & migration | Rancangan model, constraint, FK, indeks | Cocokkan dengan skema Minggu 6 dan jalankan migrasi pada DB salinan |
| Deteksi bentrok | Naif dan grouping+sweep | Uji interval setengah terbuka, hari, pasangan ganda, dua tipe konflik |
| SchedulingService | Pemeriksaan SQL, kapasitas, transaksi | Validasi perilaku `FOR UPDATE` per DB; SQLite gunakan BEGIN IMMEDIATE |
| API | Endpoint dan JSON error | Uji 201/204/404/409/422 via TestClient |
| Seed & tes | Data contoh, dua properti Hypothesis | Periksa hasil pytest dan kesetaraan detektor |

## Catatan penggunaan
AI membantu menyusun kode; tidak ada klaim telah membandingkan dua model eksternal. Hasil pengujian dan batasan lingkungan dicatat terpisah. Review manual terhadap data riil dan uji concurrency DB produksi tetap menjadi tanggung jawab pengembang.

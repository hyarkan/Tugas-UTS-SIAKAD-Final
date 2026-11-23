# AI Usage Log — Minggu 8

Dokumen ini mencatat penggunaan AI sebagai alat bantu pengembangan pada tugas Minggu 8. Seluruh keputusan implementasi, hasil pengujian, dan penerapan batasan tetap diperiksa dan disahkan oleh pengembang manusia.

## 1. Konteks dan tujuan penggunaan AI

AI digunakan sebagai pendamping teknis dalam pengembangan lanjutan dari implementasi Minggu 7 sesuai instruksi dosen dan materi Minggu 7–8. Tujuan penggunaannya adalah membantu memahami instruksi, merinci area implementasi, mengidentifikasi risiko regresi, menyusun solusi, memperjelas dokumentasi, serta membuat skenario pengujian yang terarah.

AI tidak dijadikan otoritas tunggal atas kebenaran fungsi aplikasi. Implementasi tetap harus melalui validasi kode, pengujian otomatis, pemeriksaan perilaku API, dan peninjauan manusia.

## 2. Area pekerjaan yang dibantu AI

Pemanfaatan AI mencakup area berikut:

1. **Analisis instruksi Minggu 7–8** untuk membedakan persyaratan kontrak, batasan implementasi, dan kebutuhan pengujian.
2. **Observer** untuk membantu meninjau pola `ScheduleSubject`, attachment/detachment observer, serta isolasi kegagalan antar-observer.
3. **Transactional outbox** untuk membantu meninjau `ScheduleOutbox`, `DeliveryReceipt`, pencatatan event, percobaan ulang, dan konsistensi transaksi jadwal.
4. **Invalidasi KRS** untuk membantu memastikan status KRS `submitted`/`approved` dapat ditinjau sebagai dampak perubahan jadwal dan ditransisikan ke `revision` secara terkontrol.
5. **Conflict resolver** untuk membantu meninjau deteksi bentrok ruangan/dosen, pemeringkatan rekomendasi, validasi saran AI, serta fallback deterministik.
6. **Ekspor ICS** untuk membantu mempertahankan format iCalendar mingguan, UID, line folding, zona waktu, dan aturan kalender.
7. **Dokumentasi** untuk menyusun README, AI usage log, penjelasan arsitektur, dan batasan desain secara lebih jelas.
8. **Pengujian** untuk membantu merancang pengujian unit dan regresi, termasuk case ruangan fiktif, bentrokan nyata, kapasitas, fallback, dan determinisme hasil.

## 3. Contoh prompt untuk alternatif jadwal

Prompt yang digunakan oleh implementasi berada pada fungsi `build_prompt()` di `app/services/rescheduling.py`. Prompt ini dibentuk dari instruksi sistem dan data `jadwal` serta `available_slots` dalam bentuk JSON:

```text
Anda adalah scheduling assistant. Pilih maksimal 3 alternatif dari available_slots tanpa membuat slot baru. Prioritaskan pagi/siang dan minimalkan gangguan mahasiswa. Balas HANYA JSON array [{hari, jam_mulai, jam_selesai, ruangan_kode, reason}].
{"jadwal": <snapshot jadwal>, "available_slots": <daftar slot tersedia>}
```

Contoh instruksi tegas dari prompt tersebut meliputi:

- Memilih maksimal tiga alternatif.
- Mengambil alternatif hanya dari `available_slots`.
- Tidak membuat slot baru di luar daftar yang tersedia.
- Memprioritaskan waktu pagi/siang dan gangguan seminimal mungkin.
- Mengembalikan respons sebagai JSON array dengan empat atribut jadwal dan `reason`.

Prompt di atas adalah prompt yang **diimplementasikan dalam kode**. Pernyataan ini tidak berarti permintaan telah berhasil dikirim atau diproses oleh penyedia AI eksternal.

## 4. Mekanisme evaluasi hasil AI

Hasil penyedia AI tidak dianggap langsung dapat diterapkan. Alur evaluasi yang diterapkan adalah:

1. `available_slots()` menghasilkan daftar slot yang memenuhi kondisi waktu, kapasitas, ruangan, dosen, dan aturan bentrok saat ini.
2. `saring_saran()` menerapkan whitelist terhadap `available_slots()`. Saran dengan ruangan fiktif, hari tidak valid, slot bentrok, atau duplikasi ditolak.
3. Saran yang lolos dapat diterapkan kembali melalui `SchedulingService`, sehingga validasi diterapkan sekali lagi pada saat perubahan jadwal sebenarnya.
4. Jika penyedia AI tidak tersedia, gagal, atau mengembalikan daftar kosong sementara slot valid masih tersedia, sistem memakai `deterministic_suggestions()` sebagai fallback.
5. Jika tidak ada slot valid, daftar rekomendasi tetap kosong dan tidak dibuat saran palsu.

Fallback deterministik hanya mengubah pemilihan dan sumber rekomendasi. Batas validasi jadwal, penggunaan ruangan/dosen, dan aturan kapasitas tidak dilewati.

## 5. Bukti validasi

Validasi implementasi didukung oleh pengujian otomatis. Hasil pengujian keseluruhan yang dilaporkan untuk tugas ini adalah **105 passed, 1 warning**.

Pengujian khusus mencakup:

- Pengujian `test_suggestion_filter_rejects_fake_and_conflicting_rooms` memastikan saran ruangan fiktif dan data tidak valid ditolak dari daftar saran.
- Pengujian `test_saring_saran_rejects_actual_schedule_conflict` menyusun satu saran valid, satu ruangan fiktif, dan satu jadwal yang benar-benar bentrok pada hari dan jam yang sama. Hasil yang diterima dipastikan tepat satu saran valid.
- Pengujian fallback memastikan `deterministic_suggestions()` dipakai saat AI mengembalikan daftar kosong sementara slot tersedia.
- Pengujian kapasitas memastikan ruangan disaring berdasarkan `max(kelas.kuota, enrolled)`, dengan `enrolled` dihitung dari NIM unik pada KRS berstatus `submitted` atau `approved`.
- Pengujian Minggu 8 juga mencakup observer/outbox, invalidasi KRS, konflik, ICS, dan endpoint terkait.

Catatan warning harus tetap dibedakan dari kegagalan pengujian. Warning yang tercatat berasal dari deprecasi `StarletteDeprecationWarning` pada TestClient dan tidak menyebabkan pengujian gagal.

## 6. Keputusan manusia

Keputusan yang diambil adalah bahwa hasil AI tidak boleh langsung diterapkan sebagai perubahan jadwal. Keputusan ini didasarkan pada risiko bahwa respons model dapat tidak lengkap, tidak konsisten dengan slot yang tersedia, mengandung ruangan fiktif, atau bertentangan dengan jadwal lain.

Setiap hasil AI diperlakukan sebagai kandidat. Kandidat hanya dapat diterima setelah melewati:

- whitelist `available_slots`,
- penghapusan duplikasi dan pembatasan maksimal tiga saran,
- validasi bentrok dan kapasitas,
- validasi ulang melalui `SchedulingService` ketika saran diterapkan.

Jika provider gagal atau respons tidak menghasilkan kandidat valid, fallback deterministik dipakai agar fitur tetap dapat digunakan. Keputusan ini menjaga perilaku aplikasi dapat diprediksi dan membatasi dampak kesalahan model.

## 7. Keterbatasan

Dokumentasi ini tetap mencatat keterbatasan implementasi demo:

- Notifikasi mahasiswa, dosen, dan admin masih berupa simulasi berbasis kanal log serta pencatatan receipt; gateway Email/SMS/Push sungguhan belum diuji.
- Header `X-Actor-Role` adalah simulasi otorisasi untuk demo. Header tersebut bukan autentikasi produksi dan tidak boleh dianggap pengamanan endpoint di lingkungan nyata.
- Penyedia AI eksternal belum diverifikasi langsung secara live pada paket tugas ini.
- Konkurensi lintas worker belum dibuktikan. SQLite dan dispatcher demo memiliki asumsi serta batasan khusus untuk penggunaan multi-worker.

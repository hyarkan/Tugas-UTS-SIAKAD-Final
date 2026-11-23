## Ringkasan perubahan
- [ ] Observer + Email/SMS/Push simulasi
- [ ] Transactional outbox + dispatcher setelah commit
- [ ] KRS invalidator + transisi SISTEM → revision
- [ ] Conflict resolver + saran AI tersaring
- [ ] Sequence diagram + ekspor .ics

## Bukti pengujian
Perintah: `python -m pytest -q` dan `python -m alembic upgrade head`

## Checklist review
- [ ] Perubahan jadwal, KRS, outbox dalam transaksi yang sama
- [ ] Observer gagal tidak menghentikan observer lain
- [ ] Tidak ada notifikasi sebelum commit
- [ ] Saran AI divalidasi ulang sebelum apply
- [ ] Dokumentasi dan AI Usage Log diperbarui

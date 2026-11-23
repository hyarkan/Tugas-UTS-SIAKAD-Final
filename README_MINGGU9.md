# Tugas Minggu 9 — Modul Nilai (Bagian 1)

Minggu 9 berfokus pada input nilai, perhitungan IPS/IPK, aturan bisnis, dan Audit Trail. Transkrip PDF dibahas pada [README_MINGGU10.md](README_MINGGU10.md).

## Menjalankan

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Buka `/docs` untuk API atau `/nilai/form` untuk form demo.

**Peringatan:** identitas dosen pada `x-actor-role: dosen` dan `x-dosen-id` adalah header demo yang dapat dipalsukan, bukan autentikasi aman. Jangan deploy sebagai sistem produksi atau memasukkan data mahasiswa nyata.

## Aturan dan batasan

- Hanya KRS berstatus `approved` yang dapat menerima nilai serta berkontribusi pada IPS, IPK, transkrip, dan riwayat resmi. KRS draft/submitted/revision dan status lain ditolak.
- Nilai hanya dapat dimasukkan oleh dosen pengampu. Koreksi memerlukan alasan.
- Ambang presensi adalah minimal 75%. Modul presensi nyata belum tersedia; `PresensiStub` fail-closed dan menolak input tanpa data presensi. Data uji diberikan melalui dependency override, bukan produksi.
- Audit Trail nilai dibuat oleh trigger migrasi `0008_grade_audit_trigger`. `GradeService` memasukkan konteks dalam transaksi yang sama; aplikasi tidak menambahkan `GradeHistory` secara manual. Trigger menolak perubahan tanpa konteks dan menghapus konteks setelah mencatat riwayat.
- Huruf nilai dikirim sebagai string A, B, C, D, atau E. Bobot menggunakan Decimal; IPS/IPK ditampilkan dengan dua angka desimal.

Endpoint utama: `PUT /api/kelas/{kelas_id}/nilai/{nim}`, `GET /api/nilai/{nim}/ips/{semester}`, `GET /api/nilai/{nim}/ipk`, dan `GET /api/nilai/{nim}/riwayat`.

## Checklist

- [x] Input nilai dan validasi dosen pengampu
- [x] Hanya KRS approved untuk catatan akademik resmi
- [x] Presensi melalui port fail-closed (integrasi nyata menunggu Minggu 12)
- [x] IPS/IPK Decimal, retake, dan riwayat nilai
- [x] Audit Trail melalui trigger `0008`
- [ ] Konfirmasi stakeholder tentang D/C dan E/I
- [ ] Autentikasi dosen sesungguhnya dan integrasi presensi nyata

Baca [docs/ADR-004-grade-policy.md](docs/ADR-004-grade-policy.md) untuk kebijakan sementara dan risiko.

# Tugas Minggu 10 — Modul Nilai & Transkrip (Bagian 2)

Lanjutan dari implementasi Minggu 3–9. Proyek ini mengembangkan **transkrip akademik**, **tampilan HTML**, **unduhan PDF**, **predikat di footer**, **riwayat perubahan nilai**, dan **acceptance test multi-semester**. Riwayat audit dibuat oleh trigger migrasi `0008`; hanya KRS `approved` masuk ke catatan akademik.

## Instalasi & menjalankan (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Buka `http://127.0.0.1:8000/docs` untuk dokumentasi API. Untuk pengujian: `python -m pytest -q`.

## Fitur dan API baru

- `GET /api/nilai/{nim}/transkrip` — catatan akademik dalam JSON: biodata, mata kuliah per semester, SKS, nilai, bobot, mutu, IPS, IPK, SKS lulus, predikat, histori.
- `GET /api/nilai/{nim}/transkrip/html` — template HTML/CSS dinamis, dengan tabel per semester dan footer.
- `GET /api/nilai/{nim}/transkrip/pdf` — mengunduh PDF A4. Backend utama **WeasyPrint** mengonversi template HTML; bila tidak tersedia, fallback **ReportLab** menghasilkan dokumen dari data yang sama. Pada lingkungan pengembangan saat ini WeasyPrint tidak tersedia, sehingga jalur ReportLab yang teruji digunakan.
- `GET /api/nilai/{nim}/riwayat` — histori audit Minggu 9 tetap tersedia.

**Akses demo:** endpoint transkrip memerlukan header `x-actor-role: dosen` dan `x-dosen-id: <integer>` seperti endpoint Minggu 9. Header ini **bukan autentikasi yang aman**, sehingga proyek hanya untuk simulasi akademik dengan data dummy, bukan produksi atau data pribadi nyata.

Contoh dengan PowerShell:

```powershell
Invoke-WebRequest 'http://127.0.0.1:8000/api/nilai/20240001/transkrip/pdf' -Headers @{'x-actor-role'='dosen'; 'x-dosen-id'='110'} -OutFile 'transkrip_demo.pdf'
```

NIM tersebut adalah **contoh dari acceptance test**, bukan NIM yang otomatis tersedia setelah menjalankan seed. Gunakan NIM mahasiswa yang benar-benar tersimpan pada database Anda.

Contoh HTML dan PDF di `artifacts/transkrip_simulasi_istn.html` serta `artifacts/transkrip_simulasi_istn.pdf` dibuat dari data sintetis untuk pemeriksaan tampilan. Angkatan contoh diisi eksplisit 2025; NIM sintetis 20990001 tidak digunakan untuk inferensi angkatan. Semester contoh adalah 20251 dan 20252. Program studinya Sistem Informasi; IPS, IPK, mutu, dan total SKS dihitung dari bobot A=4 dan B=3 dengan fungsi GPA proyek. Pembuatan contoh tersebut tidak membaca atau mengubah database. Untuk membuat ulang, jalankan `python generate_transcript_sample.py` dari folder proyek.

## Ketentuan dan transparansi akademik

- Nilai dan bobot berasal dari tabel `skala_nilai`; **status lulus mengikuti `skala_nilai.lulus`**, sesuai keputusan sementara Minggu 9, bukan hardcode nilai D.
- IPK menghitung **hanya percobaan terbaik yang lulus per kode MK**, konsisten dengan `hitung_ipk` Minggu 9; IPS per semester tetap mencakup semua nilai yang tersedia pada semester itu.
- Nilai kosong ditampilkan `—` dan tidak masuk perhitungan. Jika belum ada nilai lulus, IPK `0.00`.
- Predikat **indikatif**: `>= 3.50` Cum Laude; `3.00–3.49` Sangat Memuaskan. Rentang di bawah 3.00 belum ditetapkan di materi; tidak dikarang. Predikat tidak menyatakan mahasiswa resmi lulus.
- Kolom angkatan diambil dari 4 digit pertama NIM **hanya jika menyerupai tahun 2000–2100**; jika tidak, ditampilkan `Belum tersedia`, karena basis data belum menyediakan kolom angkatan eksplisit.
- Logo ISTN yang diberikan pengguna disajikan melalui `/static/images/logo_istn.png` dan digunakan pada tampilan HTML serta PDF. File sumber dipertahankan byte-for-byte; ukurannya 768×768 piksel RGBA transparan, bukan 3375×3375 seperti diminta dalam spesifikasi. Jika resolusi lebih tinggi diwajibkan, diperlukan aset sumber beresolusi tersebut.
- Blok Dekan hanya ruang tanda tangan/placeholder, bukan tanda tangan atau pengesahan resmi. PDF berlabel **SIMULASI AKADEMIK** dan tidak boleh dianggap dokumen legal.
- Riwayat perubahan nilai memakai view `v_grade_history` dan trigger `0008`; konteks audit, perubahan nilai, riwayat, dan pembersihan konteks berada dalam transaksi yang sama. Tidak ada pencatatan `GradeHistory` manual dari service.
- Presensi nyata dan autentikasi dosen nyata belum tersedia. Presensi fail-closed sampai integrasi Minggu 12; header demo tidak aman untuk produksi.

## Rekap deliverable

| Permintaan Minggu 10 | Implementasi | Pengujian |
|---|---|---|
| `get_transcript(nim)` lengkap | `app/services/transcript.py` | `test_multisemester_retake_and_history` |
| Transkrip PDF dari HTML | `app/templates/transcript.html`, `app/services/transcript_pdf.py` | `test_html_pdf_and_routes` |
| Predikat di footer | HTML dan PDF, aturan indikatif | `test_predikat_boundaries` |
| Tampilan historis | JSON + tabel HTML/PDF dari `v_grade_history` | `test_multisemester_retake_and_history` |
| Acceptance test multi semester | `tests/test_transcript_week10.py` | Multi-semester, retake, SKS/IPK, PDF, akses, data kosong, escaping |

Catatan: penerapan **auth nyata**, **presensi nyata**, konfirmasi aturan D/C, identitas universitas resmi, dan ketentuan predikat lainnya menunggu arahan stakeholder. Tidak ada klaim bahwa fitur tersebut sudah selesai.

## Verifikasi implementasi saat ini

- `py_compile` untuk file Python yang diubah: berhasil.
- `python -m pytest -v`: **166 passed, 1 warning**.
- Warning tersisa berasal dari deprecation Starlette terkait pemakaian `httpx` bersama `starlette.testclient`; tidak menggagalkan suite.

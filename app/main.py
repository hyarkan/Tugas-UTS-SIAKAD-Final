# ==================================================
# ARSITEKTUR — IMPORT DAN ENTRY POINT
# ==================================================
# Path dipakai untuk membangun lokasi folder static dan file dashboard
# berdasarkan lokasi file aplikasi, bukan berdasarkan folder kerja terminal.
from pathlib import Path

# FastAPI menjadi fondasi aplikasi dan menyediakan routing serta dependency injection.
from fastapi import FastAPI
# StaticFiles melayani aset statis, sedangkan FileResponse mengirim file dashboard.
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
# Setiap router membawa endpoint untuk satu area fitur.
# Pemisahan ini membuat entry point tidak perlu memuat seluruh logika bisnis.
from app.routers.pmb import router as pmb_router
from app.routers.krs import router as krs_router

from app.routers.scheduling import router as scheduling_router

from app.routers.grades import router as grades_router

from app.routers.transcript import router as transcript_router

from app.routers.finance import router as finance_router
# asynccontextmanager digunakan untuk mengatur pekerjaan yang berjalan
# sebelum aplikasi melayani request dan saat aplikasi akan berhenti.
from contextlib import asynccontextmanager
import os

# ==================================================
# ARSITEKTUR — SIKLUS HIDUP APLIKASI
# ==================================================
# Fungsi lifespan menjadi tempat mengelola resource sepanjang hidup aplikasi.
# Pada kode ini, scheduler keuangan hanya dinyalakan bila konfigurasi lingkungan memintanya.
@asynccontextmanager
async def lifespan(app):
    # Nilai None menandakan scheduler belum dibuat; ini juga menentukan
    # apakah proses penutupan scheduler perlu dijalankan nanti.
    scheduler = None
    # Fitur scheduler bersifat opsional dan aktif hanya jika nilainya "1".
    if os.getenv("FINANCE_SCHEDULER_ENABLED") == "1":
        # Import dilakukan saat dibutuhkan agar scheduler tidak diinisialisasi
        # ketika fitur tersebut tidak diaktifkan.
        from app.services.finance_scheduler import start_scheduler
        scheduler = start_scheduler()
    # Aplikasi berjalan dan dapat menerima request selama eksekusi berada di sini.
    yield
    # Setelah aplikasi selesai, scheduler yang sempat dijalankan dihentikan.
    if scheduler is not None: scheduler.shutdown(wait=False)

# ==================================================
# ARSITEKTUR — INISIALISASI FASTAPI DAN ROUTER
# ==================================================
# >>> FOKUS PRESENTASI UTS <<<
# Objek FastAPI ini adalah titik masuk aplikasi. Metadata judul dan versi
# ditampilkan pada dokumentasi API, sedangkan lifespan menghubungkan pengelolaan
# resource aplikasi dengan siklus hidup server.
app = FastAPI(title="PMB, KRS, Jadwal, dan Nilai API", version="4.0.0", lifespan=lifespan)
# Lokasi aset statis ditentukan relatif terhadap file ini agar tidak bergantung
# pada direktori tempat server dijalankan.
STATIC_DIR = Path(__file__).resolve().parent / "static"
# Aset di folder static tersedia melalui prefix URL /static.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
# Router PMB dan KRS mendaftarkan endpoint fokus UTS ke aplikasi utama.
# Router lain menambahkan fitur pendukung; masing-masing tetap dikelola di filenya.
app.include_router(pmb_router)
app.include_router(krs_router)
app.include_router(scheduling_router)
app.include_router(grades_router)
app.include_router(transcript_router)
app.include_router(finance_router)

# ==================================================
# ARSITEKTUR — ENDPOINT UMUM
# ==================================================
# Decorator ini mendaftarkan fungsi root sebagai endpoint HTTP GET pada "/".
@app.get("/")
def root():
    # Hasil dictionary dikirim FastAPI sebagai respons JSON sederhana.
    return {"message": "PMB API aktif"}

# Dashboard keuangan disediakan sebagai halaman HTML dan sengaja tidak
# dimasukkan ke dokumentasi OpenAPI karena include_in_schema bernilai False.
@app.get('/finance-dashboard',include_in_schema=False)
def finance_dashboard_page():
    # FileResponse mengirim file HTML yang berada di direktori app.
    return FileResponse(Path(__file__).resolve().parent / 'finance_dashboard.html')

# Router presensi juga didaftarkan ke aplikasi utama.
# Import berada di bagian ini pada source asli; komentar ini menjelaskan
# fungsinya tanpa mengubah susunan implementasi.
from app.routers.attendance import router as attendance_router
app.include_router(attendance_router)

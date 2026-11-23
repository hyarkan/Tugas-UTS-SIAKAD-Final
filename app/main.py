from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers.pmb import router as pmb_router
from app.routers.krs import router as krs_router

from app.routers.scheduling import router as scheduling_router

from app.routers.grades import router as grades_router

from app.routers.transcript import router as transcript_router

from app.routers.finance import router as finance_router
from contextlib import asynccontextmanager
import os

@asynccontextmanager
async def lifespan(app):
    scheduler = None
    if os.getenv("FINANCE_SCHEDULER_ENABLED") == "1":
        from app.services.finance_scheduler import start_scheduler
        scheduler = start_scheduler()
    yield
    if scheduler is not None: scheduler.shutdown(wait=False)

app = FastAPI(title="PMB, KRS, Jadwal, dan Nilai API", version="4.0.0", lifespan=lifespan)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(pmb_router)
app.include_router(krs_router)
app.include_router(scheduling_router)
app.include_router(grades_router)
app.include_router(transcript_router)
app.include_router(finance_router)

@app.get("/")
def root():
    return {"message": "PMB API aktif"}

@app.get('/finance-dashboard',include_in_schema=False)
def finance_dashboard_page():
    return FileResponse(Path(__file__).resolve().parent / 'finance_dashboard.html')

from app.routers.attendance import router as attendance_router
app.include_router(attendance_router)

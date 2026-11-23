"""API Minggu 12: QR dosen, scan mahasiswa, laporan, analitik."""
import io
import os
import time
from collections import defaultdict,deque
from threading import Lock
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from openpyxl import Workbook
from app.database import get_db
from app.services.attendance import issue, scan, qr_png
from app.services.attendance_analytics import overview, insights

router=APIRouter(prefix="/attendance",tags=["Minggu 12 - Presensi QR"])
_events=defaultdict(deque)
_lock=Lock()
def limiter(request:Request):
    key=(request.client.host if request.client else "unknown")
    now=time.monotonic()
    with _lock:
        q=_events[key]
        while q and q[0] <= now-60:q.popleft()
        if len(q)>=20:raise HTTPException(429,"Terlalu banyak scan, coba lagi nanti")
        q.append(now)

def teacher(x_actor_role:str=Header(default=""),x_attendance_admin_key:str=Header(default="")):
    key=os.getenv("ATTENDANCE_ADMIN_KEY","")
    if not key or x_actor_role!="dosen" or not __import__('secrets').compare_digest(x_attendance_admin_key,key):
        raise HTTPException(403,"Akses dosen memerlukan role dan admin key")

class ScanRequest(BaseModel):
    token:str=Field(min_length=20,max_length=4096)
    nim:str=Field(min_length=1,max_length=20)

@router.get("/qr/{schedule_id}",dependencies=[Depends(teacher)])
def generate_qr(schedule_id:int,db:Session=Depends(get_db)):
    token,expiry=issue(db,schedule_id)
    return Response(qr_png(token),media_type="image/png",headers={"Cache-Control":"no-store","X-QR-Expires-At":expiry.isoformat()})

@router.get("/token/{schedule_id}",dependencies=[Depends(teacher)])
def generate_token(schedule_id:int,db:Session=Depends(get_db)):
    token,expiry=issue(db,schedule_id)
    return {"token":token,"expires_at":expiry.isoformat(),"valid_minutes":15}

@router.post("/scan",dependencies=[Depends(limiter)])
def record_scan(data:ScanRequest,db:Session=Depends(get_db)):
    return scan(db,data.token,data.nim)

@router.get("/report",dependencies=[Depends(teacher)])
def report(schedule_id:int|None=Query(default=None),db:Session=Depends(get_db)):
    rows,summary=overview(db,schedule_id)
    return {"records":rows,"student_course_summary":summary,"warnings_below_75":[r for r in summary if r['warning']],"denominator":"sesi perkuliahan yang telah dibuat"}

@router.get("/report.xlsx",dependencies=[Depends(teacher)])
def export_report(schedule_id:int|None=Query(default=None),db:Session=Depends(get_db)):
    rows,summary=overview(db,schedule_id)
    wb=Workbook(); ws=wb.active;ws.title="Rekap Presensi"
    ws.append(["NIM","Kode MK","Kelas","Total Sesi","Hadir/Terlambat","Persentase (%)","Warning <75%"])
    for s in summary:ws.append([s['nim'],s['kode_mk'],s['kelas_id'],s['sessions'],s['attended'],s['percentage'],"YA" if s['warning'] else "TIDAK"])
    detail=wb.create_sheet("Detail Sesi");detail.append(["NIM","Kode MK","Kelas","Jadwal","Tanggal","Hari","Jam","Status"])
    for r in rows:detail.append([r[k] for k in ('nim','kode_mk','kelas_id','schedule_id','date','day','hour','status')])
    for sheet in wb:
        sheet.freeze_panes="A2";sheet.auto_filter.ref=sheet.dimensions
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width=min(30,max(14,max(len(str(cell.value or '')) for cell in column)+2))
    buf=io.BytesIO();wb.save(buf)
    return Response(buf.getvalue(),media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":'attachment; filename="laporan_presensi_minggu12.xlsx"',"Cache-Control":"no-store"})

@router.get("/insights",dependencies=[Depends(teacher)])
def attendance_insights(schedule_id:int|None=Query(default=None),db:Session=Depends(get_db)):
    return insights(db,schedule_id)

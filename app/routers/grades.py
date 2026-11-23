"""Week 9 endpoints. Header identity is DEMO ONLY, not real authentication."""
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.grade_service import GradeService, GradeError, PresensiStub, PresensiPort
from app.services.nilai_repo import NilaiRepo, GPACalculator

router = APIRouter(tags=["Nilai dan IPS/IPK"])

class NilaiIn(BaseModel):
    nilai: str = Field(pattern=r"^[ABCDE]$")
    reason: str | None = None

def get_presensi() -> PresensiPort:
    # No actual attendance system until Week 12. Override in tests or demo.
    return PresensiStub()

def get_current_dosen(x_actor_role: str = Header(default=""), x_dosen_id: int | None = Header(default=None)) -> int:
    # Demo-only. Replace with verified session/JWT identity before production.
    if x_actor_role != "dosen" or x_dosen_id is None:
        raise HTTPException(403, "Identitas dosen diperlukan (header demo).")
    return x_dosen_id

@router.put("/api/kelas/{kelas_id}/nilai/{nim}")
def set_nilai(kelas_id: int, nim: str, body: NilaiIn, db: Session = Depends(get_db),
              dosen_id: int = Depends(get_current_dosen), presensi: PresensiPort = Depends(get_presensi)):
    try:
        return GradeService(db, presensi).input_nilai(dosen_id=dosen_id, kelas_id=kelas_id,
                                                      nim=nim, nilai=body.nilai, reason=body.reason)
    except GradeError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc

@router.get("/api/nilai/{nim}/ips/{semester}")
def ips(nim: str, semester: str, db: Session = Depends(get_db)):
    return {"nim": nim, "semester": semester, "ips": str(GPACalculator(NilaiRepo(db)).calculate_ips(nim, semester))}

@router.get("/api/nilai/{nim}/ipk")
def ipk(nim: str, db: Session = Depends(get_db)):
    return {"nim": nim, "ipk": str(GPACalculator(NilaiRepo(db)).calculate_ipk(nim))}

@router.get("/api/nilai/{nim}/riwayat")
def riwayat(nim: str, db: Session = Depends(get_db), dosen_id: int = Depends(get_current_dosen)):
    return {"nim": nim, "history": NilaiRepo(db).history(nim)}

@router.get("/nilai/form", response_class=HTMLResponse)
def form_nilai():
    # Simple web form; server still enforces authorization and attendance.
    return """<!doctype html><html lang='id'><meta charset='utf-8'>
    <title>Input Nilai - Demo Minggu 9</title>
    <style>body{font:16px system-ui;max-width:580px;margin:4rem auto;padding:1rem;background:#f5f7fa}
    form{display:grid;gap:1rem;background:white;padding:2rem;border-radius:12px}
    input,select,button{padding:.7rem;font:inherit}button{background:#185adb;color:white;border:0}
    pre{white-space:pre-wrap}</style><h1>Input Nilai Mahasiswa</h1>
    <p>DEMO saja: identitas dosen melalui header, presensi belum tersedia. Server menolak input sampai
    adapter presensi disediakan. Jangan gunakan data mahasiswa sungguhan.</p>
    <form id='f'><label>ID Kelas <input name='kelas' type='number' min='1' required></label>
    <label>NIM <input name='nim' required></label><label>ID Dosen Pengampu (demo)
    <input name='dosen' type='number' min='1' required></label>
    <label>Nilai <select name='nilai'><option>A</option><option>B</option><option>C</option>
    <option>D</option><option>E</option></select></label>
    <label>Alasan perubahan <input name='reason' placeholder='Wajib jika mengubah nilai'></label>
    <button type='submit'>Simpan nilai</button></form><pre id='hasil'></pre>
    <script>document.getElementById('f').onsubmit=async e=>{e.preventDefault();
    let x=Object.fromEntries(new FormData(e.target));let r=await fetch('/api/kelas/'+
    encodeURIComponent(x.kelas)+'/nilai/'+encodeURIComponent(x.nim),{method:'PUT',
    headers:{'Content-Type':'application/json','x-actor-role':'dosen','x-dosen-id':x.dosen},
    body:JSON.stringify({nilai:x.nilai,reason:x.reason||null})});
    document.getElementById('hasil').textContent=r.status+' '+await r.text();};</script></html>"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.scheduling import JadwalInput, JadwalResponse
from app.services.scheduling_service import SchedulingError, SchedulingService

router = APIRouter(prefix="/api/jadwal", tags=["Jadwal dan Ruangan"])

def _run(call):
    try:
        return call()
    except SchedulingError as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.body()})

@router.post("", status_code=201, response_model=JadwalResponse)
def create_jadwal(data: JadwalInput, db: Session = Depends(get_db)):
    return _run(lambda: SchedulingService(db).create(data))

@router.put("/{jadwal_id}", response_model=JadwalResponse)
def update_jadwal(jadwal_id: int, data: JadwalInput, db: Session = Depends(get_db)):
    return _run(lambda: SchedulingService(db).update(jadwal_id, data))

@router.delete("/{jadwal_id}", status_code=204)
def delete_jadwal(jadwal_id: int, db: Session = Depends(get_db)):
    result = _run(lambda: SchedulingService(db).delete(jadwal_id))
    return result

@router.get("/conflicts")
def list_conflicts(db: Session = Depends(get_db)):
    return [{"type": c.type, "affected": list(c.affected)} for c in SchedulingService(db).conflicts()]

# Week 8: demo-only role header, NOT production authentication.
from datetime import date
from fastapi import Header, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from app.services.rescheduling import (available_slots, build_prompt, saring_saran,
                                         deterministic_suggestions, apply_suggestion)
from app.services.calendar_export import export_ics
from app.services.ai_scheduling import ai_suggestions, AIUnavailable
from app.services.schedule_observers import OutboxDispatcher
from app.models.scheduling import Jadwal


def require_admin(x_actor_role: str = Header(default="")):
    if x_actor_role != "admin_akademik":
        raise HTTPException(status_code=403, detail="Hanya admin akademik")

class Suggestion(BaseModel):
    hari: int = Field(ge=1, le=6)
    jam_mulai: str
    jam_selesai: str
    ruangan_kode: str
    reason: str = ""

class SuggestionBatch(BaseModel):
    suggestions: list[dict]

@router.get("/{jadwal_id}/suggestions", dependencies=[Depends(require_admin)])
def suggestions(jadwal_id: int, db: Session = Depends(get_db)):
    jadwal = db.get(Jadwal, jadwal_id)
    if jadwal is None:
        raise HTTPException(404, "Jadwal tidak ditemukan")
    slots = available_slots(db, jadwal_id)
    from app.services.scheduling_service import snapshot
    try:
        results = ai_suggestions(db, jadwal_id)
        source = "ai_validated"
        if not results and slots:
            results = deterministic_suggestions(db, jadwal_id)
            source = "deterministic_fallback"
    except AIUnavailable:
        results = deterministic_suggestions(db, jadwal_id)
        source = "deterministic_fallback"
    return {"available_count": len(slots), "suggestions": results,
            "source": source, "ai_prompt": build_prompt(snapshot(jadwal), slots)}

@router.post("/{jadwal_id}/filter-suggestions", dependencies=[Depends(require_admin)])
def filter_suggestions(jadwal_id: int, data: SuggestionBatch, db: Session = Depends(get_db)):
    if db.get(Jadwal, jadwal_id) is None:
        raise HTTPException(404, "Jadwal tidak ditemukan")
    return {"suggestions": saring_saran(db, jadwal_id, data.suggestions)}

@router.post("/{jadwal_id}/apply-suggestion", dependencies=[Depends(require_admin)], response_model=JadwalResponse)
def apply(jadwal_id: int, data: Suggestion, db: Session = Depends(get_db)):
    return _run(lambda: apply_suggestion(db, jadwal_id, data.model_dump()))

@router.post("/outbox/dispatch", dependencies=[Depends(require_admin)])
def dispatch_outbox(db: Session = Depends(get_db)):
    return {"results": OutboxDispatcher(db).run()}

@router.get("/calendar/export.ics")
def calendar_ics(start: date = Query(...), end: date = Query(...), db: Session = Depends(get_db)):
    try:
        body = export_ics(db, start, end)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(content=body, media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="jadwal.ics"'})

@router.get("/admin/conflict-resolver", response_class=HTMLResponse)
def conflict_dashboard():
    return """<!doctype html><html lang='id'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Conflict Resolver Minggu 8</title><style>body{font:16px system-ui;background:#101828;color:#f9fafb;max-width:850px;margin:40px auto;padding:20px}button,input{padding:10px;margin:5px;border-radius:8px}pre{white-space:pre-wrap;background:#202b40;padding:15px;border-radius:10px}button{cursor:pointer}</style>
<h1>Conflict Resolver · Minggu 8</h1><p>Demo admin akademik: cek bentrok, tampilkan saran yang sudah divalidasi, dan terapkan melalui SchedulingService.</p>
<button onclick='conflicts()'>Lihat bentrok</button><pre id='conflicts'></pre>
<label>ID jadwal <input type='number' id='id' min='1' value='1'></label><button onclick='suggest()'>Minta alternatif</button><div id='options'></div>
<script>
const headers={'X-Actor-Role':'admin_akademik','Content-Type':'application/json'};
async function conflicts(){let r=await fetch('/api/jadwal/conflicts');document.getElementById('conflicts').textContent=JSON.stringify(await r.json(),null,2)}
async function suggest(){let id=document.getElementById('id').value,r=await fetch('/api/jadwal/'+id+'/suggestions',{headers}),j=await r.json(),box=document.getElementById('options');box.replaceChildren();if(!r.ok){box.textContent=JSON.stringify(j);return}for(const s of j.suggestions){let p=document.createElement('p');p.textContent=`Hari ${s.hari} ${s.jam_mulai}-${s.jam_selesai} ${s.ruangan_kode}: ${s.reason}`;let b=document.createElement('button');b.textContent='Terapkan';b.onclick=async()=>{if(!confirm('Terapkan perubahan jadwal?'))return;let res=await fetch('/api/jadwal/'+id+'/apply-suggestion',{method:'POST',headers,body:JSON.stringify(s)});alert(JSON.stringify(await res.json()))};p.append(b);box.append(p)}if(!j.suggestions.length)box.textContent='Tidak ada slot tersedia'}
conflicts();</script></html>"""

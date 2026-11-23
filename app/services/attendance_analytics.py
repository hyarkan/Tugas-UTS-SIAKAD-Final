"""Analitik deterministik berbasis aturan; tidak mengklaim sebagai model ML terlatih."""
from collections import defaultdict
from datetime import datetime
from sqlalchemy import select
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.krs import KRS, KRSDetail
from app.models.scheduling import Jadwal, Kelas
from app.models.calon_mahasiswa import CalonMahasiswa
from app.services.attendance import ZONE, utc_from_db

DAYS = ["Senin","Selasa","Rabu","Kamis","Jumat","Sabtu","Minggu"]
def overview(db, schedule_id=None):
    sessions = db.scalars(select(AttendanceSession).order_by(AttendanceSession.session_date,AttendanceSession.id)).all()
    if schedule_id is not None: sessions = [s for s in sessions if s.schedule_id == schedule_id]
    results=[]; groups=defaultdict(list)
    for session in sessions:
        schedule=db.get(Jadwal,session.schedule_id)
        if not schedule: continue
        enrolled=db.execute(select(KRS.nim).join(KRSDetail,KRSDetail.krs_id == KRS.id).where(KRS.semester == schedule.kelas.semester,KRS.status == "approved",KRSDetail.kelas_id == schedule.kelas_id,KRSDetail.kode_mk == schedule.kelas.kode_mk)).scalars().all()
        present={r.nim:r.status for r in db.scalars(select(AttendanceRecord).where(AttendanceRecord.session_id == session.id))}
        for nim in sorted(set(enrolled)):
            row={"nim":nim,"kode_mk":schedule.kelas.kode_mk,"kelas_id":schedule.kelas_id,"schedule_id":schedule.id,"date":session.session_date.isoformat(),"day":DAYS[session.session_date.weekday()],"hour":schedule.jam_mulai.strftime('%H:%M'),"status":present.get(nim,"absen")}
            results.append(row);groups[(nim,schedule.kelas.kode_mk,schedule.kelas_id)].append(row)
    summaries=[]
    for (nim,mk,kelas),records in sorted(groups.items()):
        attended=sum(r['status'] != 'absen' for r in records)
        pct=round(100*attended/len(records),2)
        summaries.append({"nim":nim,"kode_mk":mk,"kelas_id":kelas,"sessions":len(records),"attended":attended,"percentage":pct,"warning":pct<75})
    return results,summaries

def insights(db,schedule_id=None):
    records,summaries=overview(db,schedule_id)
    warnings=[x for x in summaries if x['warning']]
    buckets=defaultdict(lambda:[0,0])
    personal=defaultdict(lambda:[0,0])
    for r in records:
        buckets[(r['day'],r['hour'])][1]+=1
        if r['status']=='absen':buckets[(r['day'],r['hour'])][0]+=1
        personal[(r['nim'],r['day'])][1]+=1
        if r['status']=='absen':personal[(r['nim'],r['day'])][0]+=1
    patterns=[{"day":d,"hour":h,"absent":v[0],"total":v[1],"absence_rate":round(100*v[0]/v[1],2)} for (d,h),v in sorted(buckets.items()) if v[1] and v[0]]
    actions=[{"nim":s['nim'],"kode_mk":s['kode_mk'],"action":"Hubungi mahasiswa untuk konseling dan pemantauan presensi","reason":f"Kehadiran {s['percentage']}% (<75%)"} for s in warnings]
    actions += [{"nim":nim,"day":day,"action":f"Tinjau pola absen {day}; pertimbangkan konseling","reason":f"Absen {v[0]} dari {v[1]} sesi"} for (nim,day),v in sorted(personal.items()) if v[1]>=2 and v[0]>=2 and v[0]/v[1]>=0.5]
    actions += [{"day":p['day'],"hour":p['hour'],"action":"Evaluasi waktu kelas bersama dosen; pertimbangkan penjadwalan ulang","reason":f"Tingkat absen {p['absence_rate']}%"} for p in patterns if p['total']>=3 and p['absence_rate']>=40]
    return {"method":"rule_based_attendance_analytics","sessions_analyzed":len(set((r['schedule_id'],r['date']) for r in records)),"student_course_summaries":summaries,"at_risk_count":len(warnings),"at_risk_students":warnings,"absence_patterns":patterns,"actions":actions,"note":"Analisis berbasis aturan, bukan prediksi model AI terlatih. Persentase dihitung dari sesi yang telah dibuat."}

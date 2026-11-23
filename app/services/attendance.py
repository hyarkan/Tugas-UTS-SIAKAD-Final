"""Aturan presensi: zona waktu kampus, JWT pendek, kelas KRS, satu scan/sesi."""
import io
import os
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import jwt
import qrcode
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.attendance import AttendanceSession, AttendanceQR, AttendanceRecord
from app.models.scheduling import Jadwal
from app.models.krs import KRS, KRSDetail
from app.models.calon_mahasiswa import CalonMahasiswa

ZONE = ZoneInfo("Asia/Jakarta")
def local_now(): return datetime.now(ZONE)
def naive_utc(dt): return dt.astimezone(timezone.utc).replace(tzinfo=None)
def utc_from_db(dt): return dt.replace(tzinfo=timezone.utc)
def secret():
    value = os.getenv("ATTENDANCE_JWT_SECRET", "")
    if len(value) < 32:
        raise HTTPException(503, "ATTENDANCE_JWT_SECRET harus diatur (minimal 32 karakter)")
    return value

def get_schedule(db, schedule_id):
    schedule = db.get(Jadwal, schedule_id)
    if schedule is None: raise HTTPException(404, "Jadwal tidak ditemukan")
    return schedule

def bounds(schedule, day):
    start = datetime.combine(day, schedule.jam_mulai, ZONE)
    end = datetime.combine(day, schedule.jam_selesai, ZONE)
    return start, end

def issue(db, schedule_id, now=None):
    now = now or local_now()
    schedule = get_schedule(db, schedule_id)
    if now.isoweekday() != schedule.hari:
        raise HTTPException(422, "Hari ini bukan hari kuliah jadwal tersebut")
    start, end = bounds(schedule, now.date())
    if not start <= now <= min(end, start + timedelta(minutes=30)):
        raise HTTPException(422, "QR hanya dapat diterbitkan dalam 30 menit awal kuliah")
    session = db.scalar(select(AttendanceSession).where(AttendanceSession.schedule_id == schedule_id, AttendanceSession.session_date == now.date()))
    if session is None:
        session = AttendanceSession(schedule_id=schedule_id, session_date=now.date(), starts_at=naive_utc(start), ends_at=naive_utc(end), created_at=naive_utc(now))
        db.add(session); db.flush()
    jti = secrets.token_hex(24)
    expiry = min(now + timedelta(minutes=15), start + timedelta(minutes=30), end)
    if expiry <= now: raise HTTPException(422, "Jendela presensi sudah ditutup")
    qr_row = AttendanceQR(session_id=session.id, jti=jti, issued_at=naive_utc(now), expires_at=naive_utc(expiry))
    db.add(qr_row); db.commit()
    token = jwt.encode({"schedule_id":schedule_id, "session_id":session.id, "jti":jti, "iat":int(now.timestamp()), "exp":int(expiry.timestamp()), "type":"attendance"},secret(),algorithm="HS256")
    return token, expiry

def qr_png(token):
    image = qrcode.make(token)
    out = io.BytesIO(); image.save(out, format="PNG"); return out.getvalue()

def scan(db, token, nim, now=None):
    now = now or local_now()
    try:
        data = jwt.decode(token, secret(), algorithms=["HS256"], options={"require":["exp","iat"]}, leeway=0)
    except jwt.ExpiredSignatureError: raise HTTPException(401,"QR telah kedaluwarsa")
    except jwt.InvalidTokenError: raise HTTPException(401,"Token QR tidak valid")
    if data.get("type") != "attendance" or not isinstance(data.get("schedule_id"),int) or not isinstance(data.get("session_id"),int) or not isinstance(data.get("jti"),str):
        raise HTTPException(401,"Payload QR tidak valid")
    session = db.get(AttendanceSession,data["session_id"])
    qr = db.scalar(select(AttendanceQR).where(AttendanceQR.session_id == data["session_id"], AttendanceQR.jti == data["jti"]))
    if not session or not qr or session.schedule_id != data["schedule_id"] or naive_utc(now) >= qr.expires_at:
        raise HTTPException(401,"QR tidak berlaku untuk sesi ini")
    schedule = get_schedule(db, session.schedule_id)
    start = utc_from_db(session.starts_at).astimezone(ZONE)
    end = utc_from_db(session.ends_at).astimezone(ZONE)
    if now.date() != session.session_date or now.isoweekday() != schedule.hari or not start <= now <= min(end,start+timedelta(minutes=30)):
        raise HTTPException(422,"Di luar jadwal atau batas 30 menit presensi")
    student = db.scalar(select(CalonMahasiswa).where(CalonMahasiswa.nim == nim))
    if student is None: raise HTTPException(404,"Mahasiswa tidak ditemukan")
    enrolled = db.scalar(select(KRSDetail.id).join(KRS,KRS.id == KRSDetail.krs_id).where(KRS.nim == nim, KRS.semester == schedule.kelas.semester, KRS.status == "approved", KRSDetail.kode_mk == schedule.kelas.kode_mk, KRSDetail.kelas_id == schedule.kelas_id))
    if enrolled is None: raise HTTPException(403,"Mahasiswa tidak terdaftar di kelas ini pada KRS approved")
    if db.scalar(select(AttendanceRecord.id).where(AttendanceRecord.session_id == session.id, AttendanceRecord.nim == nim)) is not None:
        raise HTTPException(409,"Mahasiswa sudah melakukan presensi pada sesi ini")
    status = "hadir" if now <= start+timedelta(minutes=15) else "terlambat"
    db.add(AttendanceRecord(session_id=session.id,nim=nim,scanned_at=naive_utc(now),status=status))
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409,"Presensi duplikat")
    return {"success":True,"status":status,"message":f"Presensi {status} berhasil dicatat"}

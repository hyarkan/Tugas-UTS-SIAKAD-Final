"""Pengujian Minggu 12: akses dosen, QR, enrollment, duplikasi, laporan, Excel, insight."""
from datetime import date, time, timedelta
import os
import pytest
from sqlalchemy import select
from app.models import CalonMahasiswa, ProgramStudi, JalurMasuk, StatusPMB, MataKuliah
from app.models.krs import KRS, KRSDetail
from app.models.scheduling import Ruangan, Dosen, Kelas, Jadwal
from app.services.attendance import local_now, issue, scan, ZONE
from app.services.attendance_analytics import overview, insights
from fastapi import HTTPException
from openpyxl import load_workbook
from io import BytesIO

@pytest.fixture
def scenario(db_session,monkeypatch):
    monkeypatch.setenv('ATTENDANCE_JWT_SECRET','test-secret-very-long-at-least-32-characters')
    monkeypatch.setenv('ATTENDANCE_ADMIN_KEY','test-teacher-key')
    now=local_now()
    prodi=db_session.scalar(select(ProgramStudi).where(ProgramStudi.kode=='001'))
    jalur=db_session.scalar(select(JalurMasuk).where(JalurMasuk.nama=='SNBP'))
    db_session.add_all([CalonMahasiswa(nama_lengkap='Student A',email='a-att@example.test',phone='081234567890',tanggal_lahir=date(2002,1,1),alamat='Depok',program_studi_id=prodi.id,jalur_masuk_id=jalur.id,status=StatusPMB.approve,nim='ATT001'),CalonMahasiswa(nama_lengkap='Student B',email='b-att@example.test',phone='081234567890',tanggal_lahir=date(2002,1,1),alamat='Depok',program_studi_id=prodi.id,jalur_masuk_id=jalur.id,status=StatusPMB.approve,nim='ATT002'),MataKuliah(kode_mk='ATT12',nama='Presensi',sks=2,hari=now.isoweekday(),jam_mulai=time(0),jam_selesai=time(23,59)),Ruangan(kode='ATT-R',kapasitas=30),Dosen(nidn='ATT-D',nama='Dosen')]);db_session.flush()
    db_session.add_all([Kelas(kode_mk='ATT12',nama='A',kuota=30,semester='20262'),Kelas(kode_mk='ATT12',nama='B',kuota=30,semester='20262')]);db_session.flush()
    kelas=db_session.scalar(select(Kelas).where(Kelas.nama=='A',Kelas.kode_mk=='ATT12'))
    other=db_session.scalar(select(Kelas).where(Kelas.nama=='B',Kelas.kode_mk=='ATT12'))
    start=(now-timedelta(minutes=2)).time().replace(second=0,microsecond=0)
    end=(now+timedelta(minutes=50)).time().replace(second=0,microsecond=0)
    db_session.add(Jadwal(kelas_id=kelas.id,hari=now.isoweekday(),jam_mulai=start,jam_selesai=end,ruangan_kode='ATT-R',dosen_id=db_session.scalar(select(Dosen).where(Dosen.nidn=='ATT-D')).id))
    db_session.add(KRS(nim='ATT001',semester='20262',status='approved'));db_session.flush()
    krs=db_session.scalar(select(KRS).where(KRS.nim=='ATT001'))
    db_session.add(KRSDetail(krs_id=krs.id,kode_mk='ATT12',kelas_id=kelas.id));db_session.commit()
    return db_session.scalar(select(Jadwal).where(Jadwal.kelas_id==kelas.id)).id

def test_qr_scan_report_excel_insights(client,db_session,scenario):
    headers={'X-Actor-Role':'dosen','X-Attendance-Admin-Key':'test-teacher-key'}
    assert client.get(f'/attendance/qr/{scenario}').status_code==403
    image=client.get(f'/attendance/qr/{scenario}',headers=headers)
    assert image.status_code==200 and image.content[:8]==b'\x89PNG\r\n\x1a\n'
    response=client.get(f'/attendance/token/{scenario}',headers=headers)
    assert response.status_code==200,response.text
    token=response.json()['token']
    assert client.post('/attendance/scan',json={'token':token,'nim':'ATT002'}).status_code==403
    success=client.post('/attendance/scan',json={'token':token,'nim':'ATT001'})
    assert success.status_code==200,success.text
    assert success.json()['status']=='hadir'
    assert client.post('/attendance/scan',json={'token':token,'nim':'ATT001'}).status_code==409
    report=client.get('/attendance/report',headers=headers)
    assert report.status_code==200
    assert report.json()['student_course_summary'][0]['percentage']==100
    excel=client.get('/attendance/report.xlsx',headers=headers)
    assert excel.status_code==200
    wb=load_workbook(BytesIO(excel.content));assert 'Rekap Presensi' in wb.sheetnames
    insight=client.get('/attendance/insights',headers=headers)
    assert insight.status_code==200 and insight.json()['at_risk_count']==0

def test_expired_invalid_wrong_day_and_late(db_session,scenario):
    from app.models.attendance import AttendanceQR
    token,_=issue(db_session,scenario)
    with pytest.raises(HTTPException) as error:scan(db_session,token,'ATT002')
    assert error.value.status_code==403
    row=db_session.scalar(select(AttendanceQR).order_by(AttendanceQR.id.desc()))
    row.expires_at=row.issued_at-timedelta(seconds=1);db_session.commit()
    with pytest.raises(HTTPException) as error:scan(db_session,token,'ATT001')
    assert error.value.status_code==401
    with pytest.raises(HTTPException) as error:scan(db_session,'bad-token','ATT001')
    assert error.value.status_code==401

def test_missing_secret(db_session,scenario,monkeypatch):
    monkeypatch.delenv('ATTENDANCE_JWT_SECRET')
    with pytest.raises(HTTPException) as error:issue(db_session,scenario)
    assert error.value.status_code==503

def test_late_status_with_fresh_qr(db_session,scenario):
    from app.models.scheduling import Jadwal
    schedule=db_session.get(Jadwal,scenario)
    now=local_now()
    schedule.jam_mulai=(now-timedelta(minutes=18)).time().replace(second=0,microsecond=0)
    db_session.commit()
    token,_=issue(db_session,scenario)
    assert scan(db_session,token,'ATT001')['status']=='terlambat'

def test_warning_and_pattern(db_session,scenario):
    from app.models.attendance import AttendanceSession
    from app.services.attendance import naive_utc
    now=local_now()
    schedule=db_session.get(Jadwal,scenario)
    for days in (7,14):
        earlier=now-timedelta(days=days)
        start=earlier.replace(hour=schedule.jam_mulai.hour,minute=schedule.jam_mulai.minute,second=0,microsecond=0)
        db_session.add(AttendanceSession(schedule_id=scenario,session_date=earlier.date(),starts_at=naive_utc(start),ends_at=naive_utc(start+timedelta(minutes=50)),created_at=naive_utc(start)))
    db_session.commit()
    data=insights(db_session,scenario)
    assert data['at_risk_count']==1
    assert data['at_risk_students'][0]['percentage']==0
    assert any('konseling' in action['action'].lower() for action in data['actions'])

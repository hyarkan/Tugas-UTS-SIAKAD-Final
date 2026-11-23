"""Pengujian akurasi laporan JSON dan Excel Minggu 12."""
from datetime import timedelta
from io import BytesIO

from openpyxl import load_workbook
from sqlalchemy import select

from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.scheduling import Jadwal
from app.services.attendance import local_now, naive_utc
from test_attendance_week12 import scenario


def test_report_excel_matches_attendance_percentage(client, db_session, scenario):
    now = local_now()
    schedule = db_session.get(Jadwal, scenario)

    for days in (21, 14, 7, 0):
        day = now - timedelta(days=days)
        start = day.replace(
            hour=schedule.jam_mulai.hour,
            minute=schedule.jam_mulai.minute,
            second=0,
            microsecond=0,
        )
        session = AttendanceSession(
            schedule_id=scenario,
            session_date=day.date(),
            starts_at=naive_utc(start),
            ends_at=naive_utc(start + timedelta(minutes=50)),
            created_at=naive_utc(start),
        )
        db_session.add(session)
        db_session.flush()

        if days in (21, 14):
            db_session.add(
                AttendanceRecord(
                    session_id=session.id,
                    nim="ATT001",
                    scanned_at=naive_utc(start + timedelta(minutes=5)),
                    status="hadir",
                )
            )

    db_session.commit()

    headers = {
        "X-Actor-Role": "dosen",
        "X-Attendance-Admin-Key": "test-teacher-key",
    }

    report = client.get(
        f"/attendance/report?schedule_id={scenario}",
        headers=headers,
    )
    assert report.status_code == 200

    summary = report.json()["student_course_summary"]
    assert len(summary) == 1
    assert summary[0]["sessions"] == 4
    assert summary[0]["attended"] == 2
    assert summary[0]["percentage"] == 50.0
    assert summary[0]["warning"] is True

    excel = client.get(
        f"/attendance/report.xlsx?schedule_id={scenario}",
        headers=headers,
    )
    assert excel.status_code == 200

    workbook = load_workbook(BytesIO(excel.content))
    sheet = workbook["Rekap Presensi"]
    row = list(sheet.iter_rows(min_row=2, values_only=True))[0]

    assert row[0] == "ATT001"
    assert row[3] == 4
    assert row[4] == 2
    assert row[5] == 50.0
    assert row[6] == "YA"

    detail = workbook["Detail Sesi"]
    statuses = [
        row[7]
        for row in detail.iter_rows(min_row=2, values_only=True)
    ]
    assert sorted(statuses) == ["absen", "absen", "hadir", "hadir"]

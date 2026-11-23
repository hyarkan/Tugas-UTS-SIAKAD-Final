from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.attendance import AttendanceQR
from app.models.scheduling import Jadwal
from app.services.attendance import issue, scan
from test_attendance_week12 import scenario


@pytest.mark.parametrize(
    "minute,expected",
    [
        (15, "hadir"),
        (16, "terlambat"),
        (30, "terlambat"),
        (31, "ditolak"),
    ],
)
def test_attendance_time_boundaries(db_session, scenario, minute, expected):
    import app.services.attendance as service

    today = datetime.now(ZoneInfo("Asia/Jakarta")).date()
    start = datetime.combine(today, time(8, 0), ZoneInfo("Asia/Jakarta"))
    scan_time = start + timedelta(minutes=minute)

    schedule = db_session.get(Jadwal, scenario)
    schedule.jam_mulai = time(8, 0)
    schedule.jam_selesai = time(10, 0)
    db_session.commit()

    if minute == 31:
        with pytest.raises(HTTPException) as error:
            issue(db_session, scenario, now=scan_time)
        assert error.value.status_code == 422
        return

    token, _ = issue(db_session, scenario, now=start)

    payload = jwt.decode(
        token,
        service.secret(),
        algorithms=["HS256"],
        options={"verify_exp": False, "verify_iat": False},
    )

    real_now = datetime.now(timezone.utc)
    payload["iat"] = int((real_now - timedelta(minutes=1)).timestamp())
    payload["exp"] = int((real_now + timedelta(hours=1)).timestamp())

    test_token = jwt.encode(
        payload,
        service.secret(),
        algorithm="HS256",
    )

    qr = db_session.scalar(
        select(AttendanceQR).where(AttendanceQR.jti == payload["jti"])
    )
    qr.expires_at = service.naive_utc(scan_time + timedelta(minutes=1))
    db_session.commit()

    result = scan(db_session, test_token, "ATT001", now=scan_time)
    assert result["status"] == expected

def test_scan_after_30_minutes_is_rejected(db_session, scenario):
    """Scan setelah 30 menit harus ditolak meskipun token masih valid."""
    import jwt
    from datetime import datetime, timedelta, time, timezone
    from zoneinfo import ZoneInfo
    from sqlalchemy import select
    from fastapi import HTTPException
    from app.models.attendance import AttendanceQR
    from app.models.scheduling import Jadwal
    from app.services.attendance import issue, scan, secret, naive_utc

    today = datetime.now(ZoneInfo("Asia/Jakarta")).date()
    start = datetime.combine(today, time(8, 0), ZoneInfo("Asia/Jakarta"))
    scan_time = start + timedelta(minutes=31)

    schedule = db_session.get(Jadwal, scenario)
    schedule.jam_mulai = time(8, 0)
    schedule.jam_selesai = time(10, 0)
    db_session.commit()

    token, _ = issue(db_session, scenario, now=start)
    payload = jwt.decode(
        token, secret(), algorithms=["HS256"],
        options={"verify_exp": False, "verify_iat": False},
    )

    real_now = datetime.now(timezone.utc)
    payload["iat"] = int((real_now - timedelta(minutes=1)).timestamp())
    payload["exp"] = int((real_now + timedelta(hours=1)).timestamp())
    test_token = jwt.encode(payload, secret(), algorithm="HS256")

    qr = db_session.scalar(
        select(AttendanceQR).where(AttendanceQR.jti == payload["jti"])
    )
    qr.expires_at = naive_utc(scan_time + timedelta(minutes=1))
    db_session.commit()

    with pytest.raises(HTTPException) as error:
        scan(db_session, test_token, "ATT001", now=scan_time)

    assert error.value.status_code == 422

def test_qr_rejected_on_wrong_class_day(db_session, scenario):
    """QR tidak boleh diterbitkan pada hari selain jadwal kuliah."""
    from datetime import timedelta
    from fastapi import HTTPException
    from app.models.scheduling import Jadwal
    from app.services.attendance import issue, local_now

    schedule = db_session.get(Jadwal, scenario)
    now = local_now()

    schedule.hari = (now.isoweekday() % 7) + 1
    db_session.commit()

    with pytest.raises(HTTPException) as error:
        issue(db_session, scenario, now=now)

    assert error.value.status_code == 422
    assert "hari" in error.value.detail.lower()

@pytest.mark.parametrize(
    "issued_minute,expected_valid_minutes",
    [(0, 15), (10, 15), (20, 10), (29, 1)],
)
def test_qr_expiry_never_exceeds_15_minutes(
    db_session, scenario, issued_minute, expected_valid_minutes
):
    """Masa berlaku QR maksimal 15 menit dan tidak melewati batas presensi."""
    from datetime import datetime, timedelta, time
    from zoneinfo import ZoneInfo
    from app.models.scheduling import Jadwal
    from app.services.attendance import issue, secret

    schedule = db_session.get(Jadwal, scenario)
    today = datetime.now(ZoneInfo("Asia/Jakarta")).date()
    start = datetime.combine(today, time(8, 0), ZoneInfo("Asia/Jakarta"))

    schedule.jam_mulai = time(8, 0)
    schedule.jam_selesai = time(10, 0)
    db_session.commit()

    issued_at = start + timedelta(minutes=issued_minute)
    token, expiry = issue(db_session, scenario, now=issued_at)

    payload = jwt.decode(
        token,
        secret(),
        algorithms=["HS256"],
        options={"verify_exp": False, "verify_iat": False},
    )

    actual_minutes = (expiry - issued_at).total_seconds() / 60

    assert actual_minutes == expected_valid_minutes
    assert actual_minutes <= 15
    assert expiry <= start + timedelta(minutes=30)
    assert payload["exp"] == int(expiry.timestamp())

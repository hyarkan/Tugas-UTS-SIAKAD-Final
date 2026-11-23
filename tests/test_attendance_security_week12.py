"""Pengujian tambahan Minggu 12: rate limiting presensi."""
from fastapi import HTTPException
import pytest
from app.routers.attendance import limiter, _events


def test_attendance_rate_limit_20_per_minute(monkeypatch):
    class FakeClient:
        host = "test-rate-limit-week12"

    class FakeRequest:
        client = FakeClient()

    request = FakeRequest()
    monkeypatch.setattr("app.routers.attendance.time.monotonic", lambda: 1000.0)

    try:
        for _ in range(20):
            limiter(request)

        with pytest.raises(HTTPException) as error:
            limiter(request)

        assert error.value.status_code == 429
    finally:
        _events.pop("test-rate-limit-week12", None)

def test_expired_jwt_is_rejected(db_session, scenario):
    """JWT dengan exp kedaluwarsa harus ditolak HTTP 401."""
    import jwt
    from datetime import datetime, timedelta, timezone
    from fastapi import HTTPException
    from app.services.attendance import issue, scan, secret

    token, _ = issue(db_session, scenario)

    payload = jwt.decode(
        token,
        secret(),
        algorithms=["HS256"],
        options={"verify_exp": False},
    )

    now = datetime.now(timezone.utc)
    payload["iat"] = int((now - timedelta(minutes=20)).timestamp())
    payload["exp"] = int((now - timedelta(minutes=1)).timestamp())

    expired_token = jwt.encode(
        payload,
        secret(),
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as error:
        scan(db_session, expired_token, "ATT001")

    assert error.value.status_code == 401
    assert "kedaluwarsa" in error.value.detail.lower()

from test_attendance_week12 import scenario

@pytest.mark.parametrize(
    "endpoint,headers",
    [
        ("/attendance/report", {}),
        ("/attendance/report", {
            "X-Actor-Role": "mahasiswa",
            "X-Attendance-Admin-Key": "test-teacher-key",
        }),
        ("/attendance/report", {
            "X-Actor-Role": "dosen",
            "X-Attendance-Admin-Key": "wrong-key",
        }),
        ("/attendance/token/1", {}),
        ("/attendance/token/1", {
            "X-Actor-Role": "mahasiswa",
            "X-Attendance-Admin-Key": "test-teacher-key",
        }),
        ("/attendance/token/1", {
            "X-Actor-Role": "dosen",
            "X-Attendance-Admin-Key": "wrong-key",
        }),
    ],
)
def test_teacher_endpoints_reject_unauthorized_access(
    client, monkeypatch, endpoint, headers
):
    monkeypatch.setenv("ATTENDANCE_ADMIN_KEY", "test-teacher-key")

    response = client.get(endpoint, headers=headers)

    assert response.status_code == 403

def test_unique_qr_tokens_cannot_duplicate_attendance(db_session, scenario):
    """QR berbeda pada satu sesi tidak boleh menghasilkan presensi ganda."""
    import jwt
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.models.attendance import AttendanceRecord
    from app.services.attendance import issue, scan, secret

    token1, _ = issue(db_session, scenario)
    token2, _ = issue(db_session, scenario)

    assert token1 != token2

    payload1 = jwt.decode(token1, secret(), algorithms=["HS256"])
    payload2 = jwt.decode(token2, secret(), algorithms=["HS256"])

    assert payload1["jti"] != payload2["jti"]
    assert payload1["session_id"] == payload2["session_id"]

    first = scan(db_session, token1, "ATT001")
    assert first["success"] is True

    with pytest.raises(HTTPException) as error:
        scan(db_session, token2, "ATT001")

    assert error.value.status_code == 409

    records = db_session.scalars(
        select(AttendanceRecord).where(AttendanceRecord.nim == "ATT001")
    ).all()

    assert len(records) == 1

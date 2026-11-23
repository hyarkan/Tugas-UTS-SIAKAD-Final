"""Week 8 core acceptance scenarios (no external AI/API or notification gateway)."""
from datetime import time
from app.models import (
    CalonMahasiswa,
    KRS,
    KRSDetail,
    MataKuliah,
    KRSLog,
    KRSNotification,
)
from app.models.outbox import ScheduleOutbox, DeliveryReceipt
from app.models.scheduling import Ruangan, Dosen, Kelas, Jadwal
from app.schemas.scheduling import JadwalInput
from app.services.schedule_observers import ScheduleSubject, ScheduleEvent, OutboxDispatcher
from app.services.scheduling_service import SchedulingService
from app.services.rescheduling import (
    available_slots,
    saring_saran,
    deterministic_suggestions,
)
from app.services.calendar_export import export_ics
from datetime import date


def setup_schedule(db):
    db.add(MataKuliah(kode_mk="MK8", nama="AI Agenik", sks=3, hari=1, jam_mulai=time(8), jam_selesai=time(10)))
    db.add_all([Ruangan(kode="A101", kapasitas=40), Ruangan(kode="B101", kapasitas=40),
                Dosen(id=81, nidn="0081", nama="Dosen A"), Dosen(id=82, nidn="0082", nama="Dosen B")])
    db.flush()
    db.add(Kelas(id=81, kode_mk="MK8", nama="A", kuota=30, semester="20261"))
    db.flush()
    db.add(Jadwal(kelas_id=81, hari=1, jam_mulai=time(8), jam_selesai=time(10), ruangan_kode="A101", dosen_id=81))
    db.commit()
    return db.query(Jadwal).one()


def test_observer_attach_once_and_failure_isolation():
    calls = []
    class Good:
        def update(self, event, db): calls.append(event.event_id)
    class Bad:
        def update(self, event, db): raise RuntimeError("SMS offline")
    good, bad = Good(), Bad()
    subject = ScheduleSubject()
    subject.attach(bad); subject.attach(good); subject.attach(good)
    event = ScheduleEvent.new("SCHEDULE_CHANGED", {}, {})
    assert subject.notify(event) == ["Bad"]
    assert calls == [event.event_id]
    subject.detach(bad)
    assert subject.notify(event) == []


def test_update_invalidates_krs_and_dispatches_outbox(db_session):
    schedule = setup_schedule(db_session)
    # This test uses a KRS record without FK-linked student; fixture SQLite FK checks require student.
    from app.models import CalonMahasiswa, StatusPMB
    db_session.add(CalonMahasiswa(nama_lengkap="Maya", email="maya8@example.com", phone="081234567890",
        tanggal_lahir=date(2006, 1, 1), alamat="Depok", program_studi_id=1,
        jalur_masuk_id=1, status=StatusPMB.approve, nim="20260010088"))
    db_session.flush()
    krs = KRS(nim="20260010088", semester="20261", status="approved")
    db_session.add(krs); db_session.flush()
    db_session.add(KRSDetail(krs_id=krs.id, kode_mk="MK8", kelas_id=81))
    db_session.commit()
    updated = SchedulingService(db_session).update(schedule.id, JadwalInput(
        kelas_id=81, hari=2, jam_mulai=time(10), jam_selesai=time(12),
        ruangan_kode="B101", dosen_id=82))
    assert updated.hari == 2
    assert db_session.get(KRS, krs.id).status == "revision"
    assert db_session.query(KRSLog).filter_by(action="invalidate_schedule").count() == 1
    assert db_session.query(KRSNotification).filter_by(krs_id=krs.id).count() == 1
    outbox = db_session.query(ScheduleOutbox).one()
    assert outbox.status == "sent"
    assert db_session.query(DeliveryReceipt).count() >= 5
    count = db_session.query(DeliveryReceipt).count()
    OutboxDispatcher(db_session).run()
    assert db_session.query(DeliveryReceipt).count() == count


def test_suggestion_filter_rejects_fake_and_conflicting_rooms(db_session):
    schedule = setup_schedule(db_session)
    suggestions = deterministic_suggestions(db_session, schedule.id)
    assert suggestions
    bad = {**suggestions[0], "ruangan_kode": "FICTIONAL"}
    invalid = {**suggestions[0], "hari": 99}
    filtered = saring_saran(db_session, schedule.id, [bad, invalid, suggestions[0], suggestions[0]])
    assert len(filtered) == 1
    assert filtered[0]["ruangan_kode"] == suggestions[0]["ruangan_kode"]


def test_saring_saran_rejects_actual_schedule_conflict(db_session):
    schedule = setup_schedule(db_session)
    db_session.add(Jadwal(
        kelas_id=81,
        hari=1,
        jam_mulai=time(13),
        jam_selesai=time(15),
        ruangan_kode="A101",
        dosen_id=82,
    ))
    db_session.commit()

    valid = available_slots(db_session, schedule.id)[0]
    valid_suggestion = {**valid, "reason": "Saran valid"}
    fake_room_suggestion = {
        **valid_suggestion,
        "ruangan_kode": "FICTIONAL",
        "reason": "Ruangan fiktif",
    }
    actual_conflict_suggestion = {
        "hari": 1,
        "jam_mulai": "13:00",
        "jam_selesai": "15:00",
        "ruangan_kode": "A101",
        "reason": "Bentrok dengan jadwal lain",
    }

    filtered = saring_saran(db_session, schedule.id, [
        valid_suggestion,
        fake_room_suggestion,
        actual_conflict_suggestion,
    ])

    assert len(filtered) == 1
    assert filtered[0]["ruangan_kode"] == valid["ruangan_kode"]
    assert filtered[0]["hari"] == valid["hari"]
    assert filtered[0]["jam_mulai"] == valid["jam_mulai"]
    assert filtered[0]["jam_selesai"] == valid["jam_selesai"]


def test_available_slots_use_enrolled_students_for_capacity(db_session):
    schedule = setup_schedule(db_session)
    db_session.add_all([
        Ruangan(kode="SMALL35", kapasitas=32),
        Ruangan(kode="LARGE35", kapasitas=35),
    ])
    db_session.flush()

    students = []
    krs_records = []
    for index in range(36):
        nim = f"202600200{index:02d}"
        student = CalonMahasiswa(
            nama_lengkap=f"Mahasiswa {index}",
            email=f"capacity-{index}@example.com",
            phone=f"08123456{index:04d}",
            tanggal_lahir=date(2006, 1, 1),
            alamat="Depok",
            program_studi_id=1,
            jalur_masuk_id=1,
            nim=nim,
        )
        students.append(student)
        status = "draft" if index == 35 else ("submitted" if index % 2 else "approved")
        krs_records.append(KRS(nim=nim, semester="20261", status=status))

    db_session.add_all(students)
    db_session.flush()
    db_session.add_all(krs_records)
    db_session.flush()

    krs_by_nim = {krs.nim: krs for krs in krs_records}
    db_session.add_all([
        KRSDetail(krs_id=krs_by_nim[nim].id, kode_mk="MK8", kelas_id=81)
        for nim in (krs.nim for krs in krs_records)
    ])
    db_session.commit()

    slots = available_slots(db_session, schedule.id)
    rooms = {slot["ruangan_kode"] for slot in slots}

    assert "SMALL35" not in rooms
    assert "LARGE35" in rooms
    assert "B101" in rooms


def test_deterministic_suggestions_rank_minimal_disruption(db_session, monkeypatch):
    schedule = setup_schedule(db_session)
    available = [
        {"hari": 1, "jam_mulai": "10:00", "jam_selesai": "12:00", "ruangan_kode": "B101"},
        {"hari": 2, "jam_mulai": "08:00", "jam_selesai": "10:00", "ruangan_kode": "A101"},
        {"hari": 1, "jam_mulai": "10:00", "jam_selesai": "12:00", "ruangan_kode": "A101"},
        {"hari": 1, "jam_mulai": "08:00", "jam_selesai": "10:00", "ruangan_kode": "B101"},
    ]
    monkeypatch.setattr("app.services.rescheduling.available_slots", lambda *_: available)

    first = deterministic_suggestions(db_session, schedule.id)
    second = deterministic_suggestions(db_session, schedule.id)

    assert first == second
    assert [(
        item["hari"],
        item["jam_mulai"],
        item["ruangan_kode"],
    ) for item in first] == [
        (1, "08:00", "B101"),
        (1, "10:00", "A101"),
        (1, "10:00", "B101"),
    ]
    assert "Minimal disruption" in first[0]["reason"]
    assert len(first) <= 3


def test_ics_export_contains_weekly_rule(db_session):
    setup_schedule(db_session)
    body = export_ics(db_session, date(2026, 9, 1), date(2026, 12, 31))
    assert "BEGIN:VCALENDAR\r\n" in body
    assert "RRULE:FREQ=WEEKLY" in body
    assert "UID:jadwal-" in body
    assert "LOCATION:A101" in body


def test_failed_update_rolls_back_without_outbox(db_session):
    schedule = setup_schedule(db_session)
    from app.services.scheduling_service import CapacityError
    import pytest
    with pytest.raises(CapacityError):
        # Same schedule but room capacity insufficient for class quota.
        db_session.add(Ruangan(kode="TINY", kapasitas=5))
        db_session.commit()
        SchedulingService(db_session).update(schedule.id, JadwalInput(
            kelas_id=81, hari=2, jam_mulai=time(8), jam_selesai=time(10),
            ruangan_kode="TINY", dosen_id=81))
    db_session.expire_all()
    assert db_session.get(Jadwal, schedule.id).ruangan_kode == "A101"
    assert db_session.query(ScheduleOutbox).count() == 0


def test_admin_resolver_and_calendar_endpoints(client, db_session):
    schedule = setup_schedule(db_session)
    endpoint = f"/api/jadwal/{schedule.id}/suggestions"
    assert client.get(endpoint).status_code == 403
    response = client.get(endpoint, headers={"X-Actor-Role": "admin_akademik"})
    assert response.status_code == 200
    assert response.json()["suggestions"]
    assert response.json()["source"] in {"ai_validated", "deterministic_fallback"}
    calendar = client.get("/api/jadwal/calendar/export.ics?start=2026-09-01&end=2026-12-31")
    assert calendar.status_code == 200
    assert "BEGIN:VCALENDAR" in calendar.text
    assert client.get("/api/jadwal/admin/conflict-resolver").status_code == 200


def test_suggestions_use_deterministic_fallback_when_ai_returns_empty(
    client, db_session, monkeypatch
):
    schedule = setup_schedule(db_session)
    expected = deterministic_suggestions(db_session, schedule.id)
    assert expected
    monkeypatch.setattr("app.routers.scheduling.ai_suggestions", lambda *_: [])

    response = client.get(
        f"/api/jadwal/{schedule.id}/suggestions",
        headers={"X-Actor-Role": "admin_akademik"},
    )

    assert response.status_code == 200
    assert response.json()["suggestions"] == expected
    assert response.json()["source"] == "deterministic_fallback"


def test_empty_ai_suggestions_remain_empty_when_no_slots_exist(
    client, db_session, monkeypatch
):
    schedule = setup_schedule(db_session)
    monkeypatch.setattr("app.routers.scheduling.available_slots", lambda *_: [])
    monkeypatch.setattr("app.routers.scheduling.ai_suggestions", lambda *_: [])

    response = client.get(
        f"/api/jadwal/{schedule.id}/suggestions",
        headers={"X-Actor-Role": "admin_akademik"},
    )

    assert response.status_code == 200
    assert response.json()["available_count"] == 0
    assert response.json()["suggestions"] == []
    assert response.json()["source"] == "ai_validated"


def test_42_illegal_transitions_and_6_legal():
    from itertools import product
    from app.services.krs_service import KRSForbidden, TransitionError
    legal = {("draft", "submitted", "mahasiswa"),
             ("submitted", "approved", "dosen_pa"),
             ("submitted", "revision", "dosen_pa"),
             ("revision", "submitted", "mahasiswa"),
             ("submitted", "revision", "sistem"),
             ("approved", "revision", "sistem")}
    cases = list(product(("draft", "submitted", "approved", "revision"), repeat=2))
    illegal = 0
    for (source, target), actor in product(cases, ("mahasiswa", "dosen_pa", "sistem")):
        krs = KRS(nim="20260010088", semester="20261", status=source)
        if (source, target, actor) in legal:
            krs.transition(target, actor)
            assert krs.status == target
        else:
            import pytest
            with pytest.raises((KRSForbidden, TransitionError)):
                krs.transition(target, actor)
            illegal += 1
    assert illegal == 42

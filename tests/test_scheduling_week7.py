from datetime import time
import pytest
from app.models import MataKuliah
from app.models.scheduling import Ruangan, Dosen, Kelas, Jadwal
from app.services.schedule_conflicts import (
    Conflict,
    ScheduleSlot,
    _IntervalTree,
    detect_naive,
    detect_schedule_conflict,
)


def slot(id, start, end, room="A101", lecturer=1, day=1):
    return ScheduleSlot(id, day, time(*start), time(*end), room, lecturer)

@pytest.mark.parametrize("other,expected", [
    (slot(2,(9,0),(10,0),lecturer=2), {Conflict("room_conflict",(1,2))}),
    (slot(2,(9,0),(10,0),room="B101"), {Conflict("lecturer_conflict",(1,2))}),
    (slot(2,(9,40),(10,40)), set()),
    (slot(2,(8,0),(9,0),day=2), set()),
    (slot(2,(8,30),(9,0)), {Conflict("room_conflict",(1,2)), Conflict("lecturer_conflict",(1,2))}),
])
def test_conflict_cases(other, expected):
    schedules = [slot(1,(8,0),(9,40)), other]
    assert set(detect_naive(schedules)) == expected
    assert set(detect_schedule_conflict(schedules)) == expected

def test_interval_tree_finds_overlapping_nested_and_identical_intervals():
    schedules = [
        slot(1,(8,0),(12,0)),
        slot(2,(9,0),(10,0)),
        slot(3,(8,0),(12,0)),
        slot(4,(12,0),(13,0)),
    ]
    tree = _IntervalTree(schedules)

    overlapping = tree.query(time(9), time(10))
    assert sorted(entry.slot.id for entry in overlapping) == [1,2,3]

    touching = tree.query(time(12), time(13))
    assert [entry.slot.id for entry in touching] == [4]
    assert tree.query(time(9), time(9)) == []

def test_conflict_detector_ignores_different_days_and_resources():
    original = slot(1,(8,0),(10,0))
    assert detect_schedule_conflict([
        original,
        slot(2,(8,0),(10,0),room="B101",lecturer=2),
    ]) == []
    assert detect_schedule_conflict([
        original,
        slot(3,(8,0),(10,0),day=2),
    ]) == []

def test_interval_tree_detector_matches_naive_without_duplicates():
    schedules = [
        slot(1,(8,0),(12,0)),
        slot(2,(9,0),(10,0),lecturer=2),
        slot(3,(8,0),(12,0)),
        slot(4,(12,0),(13,0)),
        slot(5,(9,0),(10,0),day=2),
        slot(6,(9,0),(10,0),room="B101",lecturer=3),
    ]

    actual = detect_schedule_conflict(schedules)
    assert actual == detect_naive(schedules)
    assert len(actual) == len(set(actual))

@pytest.fixture
def scheduling_data(db_session):
    db_session.add(MataKuliah(kode_mk="T700", nama="Mata Kuliah Tujuh", sks=2, hari=1, jam_mulai=time(8), jam_selesai=time(10)))
    db_session.add_all([Ruangan(kode="A101",kapasitas=40), Ruangan(kode="B101",kapasitas=20), Dosen(nidn="12345678",nama="Dosen 1"), Dosen(nidn="87654321",nama="Dosen 2")])
    db_session.flush()
    db_session.add_all([Kelas(kode_mk="T700",nama="A",kuota=30,semester="20261"),Kelas(kode_mk="T700",nama="B",kuota=30,semester="20261")])
    db_session.commit()
    return db_session

def payload(db, room="A101", lecturer=1, start="08:00:00", end="09:40:00", kelas_id=None):
    return {"kelas_id":kelas_id or db.query(Kelas).first().id,"hari":1,"jam_mulai":start,"jam_selesai":end,"ruangan_kode":room,"dosen_id":lecturer}

def test_api_create_conflict_update_delete_and_422(client,scheduling_data):
    db = scheduling_data
    first = client.post("/api/jadwal",json=payload(db))
    assert first.status_code == 201, first.text
    identifier = first.json()["id"]
    second = client.post("/api/jadwal",json=payload(db,lecturer=2,start="09:00:00",end="10:00:00"))
    assert second.status_code == 409
    assert second.json()["detail"]["conflicts"][0]["type"] == "room_conflict"
    assert client.post("/api/jadwal",json=payload(db,room="B101",lecturer=2)).status_code == 409
    assert client.post("/api/jadwal",json=payload(db,start="09:40:00",end="10:40:00",lecturer=2)).status_code == 201
    assert client.post("/api/jadwal",json=payload(db,start="10:00:00",end="09:00:00")).status_code == 422
    assert client.put(f"/api/jadwal/{identifier}",json=payload(db)).status_code == 200
    assert client.put("/api/jadwal/9999",json=payload(db)).status_code == 404
    assert client.delete("/api/jadwal/9999").status_code == 404
    assert client.delete(f"/api/jadwal/{identifier}").status_code == 204

def test_conflicts_from_import(client,scheduling_data):
    db=scheduling_data
    data=payload(db)
    from app.schemas.scheduling import JadwalInput
    from app.services.scheduling_service import SchedulingService
    saved=SchedulingService(db).create(JadwalInput(**data))
    other=db.query(Dosen).filter(Dosen.id != saved.dosen_id).first()
    db.add(Jadwal(kelas_id=saved.kelas_id,hari=1,jam_mulai=time(9),jam_selesai=time(10),ruangan_kode="A101",dosen_id=other.id))
    db.commit()
    res=client.get("/api/jadwal/conflicts")
    assert res.status_code==200
    assert any(c["type"]=="room_conflict" for c in res.json())

def test_capacity_and_both_conflict_types(client,scheduling_data):
    db = scheduling_data
    kelas = db.query(Kelas).first()
    first = client.post('/api/jadwal',json=payload(db))
    assert first.status_code == 201
    both = client.post('/api/jadwal',json=payload(db,start='08:30:00',end='09:30:00'))
    assert both.status_code == 409
    assert {c['type'] for c in both.json()['detail']['conflicts']} == {'room_conflict','lecturer_conflict'}
    # Kelas dengan kuota 30 tidak muat di ruang B101 kapasitas 20.
    other = db.query(Dosen).filter(Dosen.id != first.json()['dosen_id']).first()
    result = client.post('/api/jadwal',json=payload(db,room='B101',lecturer=other.id,start='10:00:00',end='11:00:00'))
    assert result.status_code == 409
    assert 'kapasitas 20' in result.json()['detail']['message']

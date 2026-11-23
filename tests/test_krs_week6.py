from datetime import date, time
from itertools import product
import pytest
from app.models import (CalonMahasiswa, StatusPMB, MataKuliah, SkalaNilai, KRS,
                        KRSDetail, KRSLog, KRSNotification, KRSStatus)
from app.services.krs_service import KRSForbidden, TransitionError

NIM = "20260010001"
SEMESTER = "20261"
STUDENT_HEADERS = {"X-Actor-Role": "mahasiswa", "X-Actor-NIM": NIM}
LECTURER_HEADERS = {"X-Actor-Role": "dosen_pa", "X-Actor-Id": "501"}


def setup_week6(db):
    student = CalonMahasiswa(nama_lengkap="Arkan", email="arkan.week6@example.com",
        phone="081234567890", tanggal_lahir=date(2007, 2, 11), alamat="Depok",
        program_studi_id=1, jalur_masuk_id=1, status=StatusPMB.approve, nim=NIM)
    db.add(student)
    db.add_all([
        MataKuliah(kode_mk="MA101", nama="Kalkulus I", sks=3, hari=1, jam_mulai=time(8), jam_selesai=time(10)),
        MataKuliah(kode_mk="MA201", nama="Kalkulus II", sks=3, hari=2, jam_mulai=time(8), jam_selesai=time(10)),
    ])
    db.add_all([SkalaNilai(nilai="A", bobot=4, lulus=True), SkalaNilai(nilai="B", bobot=3, lulus=True),
                SkalaNilai(nilai="C", bobot=2, lulus=True), SkalaNilai(nilai="D", bobot=1, lulus=False),
                SkalaNilai(nilai="E", bobot=0, lulus=False)])
    db.commit()


def add_valid_course(client):
    return client.post(f"/api/krs/{NIM}/{SEMESTER}/courses", json={"kode_mk": "MA101"}, headers=STUDENT_HEADERS)


def assign_pa(db):
    krs = db.query(KRS).filter_by(nim=NIM, semester=SEMESTER).one()
    krs.dosen_pa_id = 501
    db.commit()
    db.refresh(krs)
    return krs


def test_submit_empty_krs_is_rejected(client, db_session):
    setup_week6(db_session)
    krs = KRS(nim=NIM, semester=SEMESTER, status="draft", dosen_pa_id=501)
    db_session.add(krs); db_session.commit()
    response = client.post(f"/api/krs/{NIM}/{SEMESTER}/submit", json={"version": 1}, headers=STUDENT_HEADERS)
    assert response.status_code == 400
    assert "kosong" in response.json()["detail"].lower()
    assert db_session.query(KRS).filter_by(nim=NIM).one().status == "draft"


def test_submit_approve_is_atomic_and_creates_log_notification(client, db_session):
    setup_week6(db_session)
    assert add_valid_course(client).status_code == 201
    krs = assign_pa(db_session)
    submitted = client.post(f"/api/krs/{NIM}/{SEMESTER}/submit", json={"version": krs.version}, headers=STUDENT_HEADERS)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "submitted"
    version = submitted.json()["version"]
    approved = client.post(f"/api/krs/{NIM}/{SEMESTER}/approve",
        json={"dosen_pa_id": 501, "version": version}, headers=LECTURER_HEADERS)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["approved_at"] is not None
    assert db_session.query(KRSLog).filter_by(action="approve").count() == 1
    assert db_session.query(KRSNotification).filter_by(recipient_nim=NIM).count() == 2


def test_wrong_pa_gets_403_and_does_not_change_krs(client, db_session):
    setup_week6(db_session)
    add_valid_course(client)
    krs = assign_pa(db_session)
    submitted = client.post(f"/api/krs/{NIM}/{SEMESTER}/submit", json={"version": krs.version}, headers=STUDENT_HEADERS)
    version = submitted.json()["version"]
    headers = {"X-Actor-Role": "dosen_pa", "X-Actor-Id": "777"}
    response = client.post(f"/api/krs/{NIM}/{SEMESTER}/approve",
        json={"dosen_pa_id": 777, "version": version}, headers=headers)
    assert response.status_code == 403
    assert db_session.query(KRS).filter_by(nim=NIM).one().status == "submitted"


def test_stale_version_gets_409(client, db_session):
    setup_week6(db_session)
    add_valid_course(client)
    krs = assign_pa(db_session)
    stale_version = krs.version
    krs.updated_at = krs.updated_at.replace(microsecond=0)
    krs.revision_note = "perubahan lain"
    db_session.commit()
    response = client.post(f"/api/krs/{NIM}/{SEMESTER}/submit",
        json={"version": stale_version}, headers=STUDENT_HEADERS)
    assert response.status_code == 409


def test_revise_requires_note_and_student_can_resubmit(client, db_session):
    setup_week6(db_session)
    add_valid_course(client)
    krs = assign_pa(db_session)
    submitted = client.post(f"/api/krs/{NIM}/{SEMESTER}/submit", json={"version": krs.version}, headers=STUDENT_HEADERS)
    version = submitted.json()["version"]
    revise = client.post(f"/api/krs/{NIM}/{SEMESTER}/revise",
        json={"dosen_pa_id": 501, "version": version, "catatan": "Lengkapi mata kuliah wajib."}, headers=LECTURER_HEADERS)
    assert revise.status_code == 200, revise.text
    assert revise.json()["status"] == "revision"
    assert revise.json()["revision_note"] == "Lengkapi mata kuliah wajib."
    resubmit = client.post(f"/api/krs/{NIM}/{SEMESTER}/submit",
        json={"version": revise.json()["version"]}, headers=STUDENT_HEADERS)
    assert resubmit.status_code == 200
    assert resubmit.json()["status"] == "submitted"


def test_other_student_cannot_add_course(client, db_session):
    setup_week6(db_session)
    response = client.post(f"/api/krs/{NIM}/{SEMESTER}/courses", json={"kode_mk": "MA101"},
        headers={"X-Actor-Role": "mahasiswa", "X-Actor-NIM": "20260019999"})
    assert response.status_code == 403


STATES = ["draft", "submitted", "approved", "revision"]
ACTORS = ["mahasiswa", "dosen_pa", "sistem"]
LEGAL_TRANSITIONS = [
    ("draft", "submitted", "mahasiswa"),
    ("submitted", "approved", "dosen_pa"),
    ("submitted", "revision", "dosen_pa"),
    ("revision", "submitted", "mahasiswa"),
    ("submitted", "revision", "sistem"),
    ("approved", "revision", "sistem"),
]
ALL_TRANSITIONS = list(product(STATES, STATES, ACTORS))
ILLEGAL_TRANSITIONS = [case for case in ALL_TRANSITIONS if case not in LEGAL_TRANSITIONS]
assert len(ALL_TRANSITIONS) == 48 and len(ILLEGAL_TRANSITIONS) == 42


@pytest.mark.parametrize("source,target,actor", LEGAL_TRANSITIONS)
def test_six_legal_state_transitions(source, target, actor):
    krs = KRS(nim=NIM, semester=SEMESTER, status=source)
    krs.transition(target, actor)
    assert krs.status == target


@pytest.mark.parametrize("source,target,actor", ILLEGAL_TRANSITIONS)
def test_each_of_42_illegal_state_transitions_is_rejected(source, target, actor):
    krs = KRS(nim=NIM, semester=SEMESTER, status=source)
    with pytest.raises((TransitionError, KRSForbidden)):
        krs.transition(target, actor)
    assert krs.status == source

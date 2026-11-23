from datetime import date, time
from app.models import (CalonMahasiswa, StatusPMB, MataKuliah, SkalaNilai,
                        KRS, KRSDetail, prerequisite)


STUDENT_HEADERS = {"X-Actor-Role": "mahasiswa", "X-Actor-NIM": "20260010001"}

def setup_student_and_catalog(db_session):
    student = CalonMahasiswa(
        nama_lengkap="Muhamad Arkan Maulana", email="arkan.krs@example.com",
        phone="081234567890", tanggal_lahir=date(2007, 2, 11), alamat="Depok",
        program_studi_id=1, jalur_masuk_id=1, status=StatusPMB.approve, nim="20260010001",
    )
    db_session.add(student)
    courses = [
        MataKuliah(kode_mk="IF101", nama="Algoritma", sks=3, hari=1,
                   jam_mulai=time(8), jam_selesai=time(10)),
        MataKuliah(kode_mk="IF201", nama="Struktur Data", sks=3, hari=2,
                   jam_mulai=time(8), jam_selesai=time(10)),
        MataKuliah(kode_mk="SI101", nama="Pengantar SI", sks=2, hari=1,
                   jam_mulai=time(10), jam_selesai=time(12)),
        MataKuliah(kode_mk="SI201", nama="Basis Data", sks=3, hari=1,
                   jam_mulai=time(9), jam_selesai=time(11)),
        MataKuliah(kode_mk="MK301", nama="Mata Kuliah 3 SKS", sks=3, hari=3,
                   jam_mulai=time(8), jam_selesai=time(10)),
    ]
    db_session.add_all(courses)
    db_session.add_all([
        SkalaNilai(nilai="A", bobot=4, lulus=True),
        SkalaNilai(nilai="B", bobot=3, lulus=True),
        SkalaNilai(nilai="C", bobot=2, lulus=True),
        SkalaNilai(nilai="D", bobot=1, lulus=False),
        SkalaNilai(nilai="E", bobot=0, lulus=False),
    ])
    db_session.flush()
    db_session.execute(prerequisite.insert().values(kode_mk="IF201", kode_prasyarat="IF101"))
    db_session.commit()
    return student


def test_add_course_creates_draft_krs(client, db_session):
    setup_student_and_catalog(db_session)
    response = client.post("/api/krs/20260010001/20261/courses", json={"kode_mk": "SI101"}, headers=STUDENT_HEADERS)
    assert response.status_code == 201, response.text
    assert response.json()["kode_mk"] == "SI101"


def test_add_course_without_prerequisite_is_rejected(client, db_session):
    setup_student_and_catalog(db_session)
    response = client.post("/api/krs/20260010001/20261/courses", json={"kode_mk": "IF201"}, headers=STUDENT_HEADERS)
    assert response.status_code == 400
    assert "Algoritma" in response.json()["detail"]


def test_duplicate_course_is_rejected(client, db_session):
    setup_student_and_catalog(db_session)
    url = "/api/krs/20260010001/20261/courses"
    assert client.post(url, json={"kode_mk": "SI101"}, headers=STUDENT_HEADERS).status_code == 201
    response = client.post(url, json={"kode_mk": "SI101"}, headers=STUDENT_HEADERS)
    assert response.status_code == 400
    assert "sudah ada" in response.json()["detail"]


def test_overlapping_interval_is_rejected(client, db_session):
    setup_student_and_catalog(db_session)
    url = "/api/krs/20260010001/20261/courses"
    assert client.post(url, json={"kode_mk": "SI201"}, headers=STUDENT_HEADERS).status_code == 201
    # SI101 ends at 12:00, SI201 is 09:00-11:00: overlap even though start differs.
    response = client.post(url, json={"kode_mk": "SI101"}, headers=STUDENT_HEADERS)
    assert response.status_code == 400
    assert "bentrok" in response.json()["detail"].lower()


def test_adjacent_schedule_is_allowed(client, db_session):
    setup_student_and_catalog(db_session)
    url = "/api/krs/20260010001/20261/courses"
    # IF101 ends at 10:00; SI101 starts exactly at 10:00 on the same day.
    assert client.post(url, json={"kode_mk": "IF101"}, headers=STUDENT_HEADERS).status_code == 201
    assert client.post(url, json={"kode_mk": "SI101"}, headers=STUDENT_HEADERS).status_code == 201


def test_total_sks_limit_24_is_allowed_but_27_rejected(client, db_session):
    setup_student_and_catalog(db_session)
    # Add 8 unique 3-SKS courses directly as a fixture to reach 24 SKS.
    for i in range(8):
        code = f"X{i:03d}"
        db_session.add(MataKuliah(kode_mk=code, nama=f"Course {i}", sks=3, hari=1,
                                  jam_mulai=time(8 + i),
                                  jam_selesai=time(9 + i)))
    db_session.commit()
    url = "/api/krs/20260010001/20261/courses"
    # The first eight courses total 24; final add must be rejected at 27.
    for i in range(8):
        response = client.post(url, json={"kode_mk": f"X{i:03d}"}, headers=STUDENT_HEADERS)
        if response.status_code != 201:
            # Adjacent-day collision is not expected; any failure indicates a test setup issue.
            assert False, response.text
    extra = MataKuliah(kode_mk="X999", nama="Extra", sks=3, hari=6,
                       jam_mulai=time(18), jam_selesai=time(19))
    db_session.add(extra); db_session.commit()
    response = client.post(url, json={"kode_mk": "X999"}, headers=STUDENT_HEADERS)
    assert response.status_code == 400
    assert "27" in response.json()["detail"]


def test_remove_course_and_validate_endpoint(client, db_session):
    setup_student_and_catalog(db_session)
    url = "/api/krs/20260010001/20261/courses"
    added = client.post(url, json={"kode_mk": "SI101"}, headers=STUDENT_HEADERS)
    assert added.status_code == 201
    validation = client.get("/api/krs/20260010001/20261/validate")
    assert validation.status_code == 200
    assert validation.json()["valid"] is True
    removed = client.delete(url + "/SI101", headers=STUDENT_HEADERS)
    assert removed.status_code == 204
    assert client.get("/api/krs/20260010001/20261").json()["total_sks"] == 0


def test_prerequisite_with_grade_c_in_previous_semester_passes(client, db_session):
    student = setup_student_and_catalog(db_session)
    previous = KRS(nim=student.nim, semester="20252", status="approved")
    db_session.add(previous)
    db_session.flush()
    db_session.add(KRSDetail(krs_id=previous.id, kode_mk="IF101", nilai="C"))
    db_session.commit()
    response = client.post("/api/krs/20260010001/20261/courses", json={"kode_mk": "IF201"}, headers=STUDENT_HEADERS)
    assert response.status_code == 201, response.text

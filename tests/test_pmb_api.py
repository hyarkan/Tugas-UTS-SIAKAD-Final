def register(client, data):
    response = client.post("/api/pmb/register", json=data)
    assert response.status_code == 201
    return response.json()


def test_register_success(client, register_data):
    result = register(client, register_data)
    assert result["status"] == "pending"
    assert result["nim"] is None


def test_register_duplicate_email(client, register_data):
    register(client, register_data)
    response = client.post("/api/pmb/register", json=register_data)
    assert response.status_code == 409


def test_register_invalid_phone(client, register_data):
    register_data["phone"] = "08123"
    response = client.post("/api/pmb/register", json=register_data)
    # Pydantic/FastAPI menggunakan 422 untuk kegagalan validasi request.
    assert response.status_code == 422


def test_register_invalid_reference(client, register_data):
    register_data["program_studi_id"] = 999
    response = client.post("/api/pmb/register", json=register_data)
    assert response.status_code == 400


def test_approve_generates_sequential_nim(client, register_data):
    first = register(client, register_data)
    second_data = {**register_data, "nama_lengkap": "Budi Santoso", "email": "budi@example.com"}
    second = register(client, second_data)

    approved_first = client.put(f"/api/pmb/{first['id']}/approve")
    approved_second = client.put(f"/api/pmb/{second['id']}/approve")

    assert approved_first.status_code == 200
    assert approved_second.status_code == 200
    nim1 = approved_first.json()["nim"]
    nim2 = approved_second.json()["nim"]
    assert len(nim1) == 11 and nim1.isdigit()
    assert nim1[4:7] == "001"
    assert int(nim2[-4:]) == int(nim1[-4:]) + 1


def test_approve_is_idempotent_and_does_not_consume_counter(client, register_data):
    first = register(client, register_data)
    approved1 = client.put(f"/api/pmb/{first['id']}/approve")
    approved2 = client.put(f"/api/pmb/{first['id']}/approve")
    assert approved1.status_code == approved2.status_code == 200
    assert approved1.json()["nim"] == approved2.json()["nim"]

    next_data = {**register_data, "email": "next@example.com", "nama_lengkap": "Mahasiswa Kedua"}
    second = register(client, next_data)
    approved_next = client.put(f"/api/pmb/{second['id']}/approve")
    assert int(approved_next.json()["nim"][-4:]) == int(approved1.json()["nim"][-4:]) + 1


def test_approve_not_found(client):
    response = client.put("/api/pmb/999/approve")
    assert response.status_code == 404


def test_approve_rejected_candidate_conflict(client, register_data):
    candidate = register(client, register_data)
    rejected = client.put(f"/api/pmb/{candidate['id']}/reject")
    assert rejected.status_code == 200
    response = client.put(f"/api/pmb/{candidate['id']}/approve")
    assert response.status_code == 409


def test_approve_invalid_program_code(client, db_session, register_data):
    from app.models import ProgramStudi
    db_session.query(ProgramStudi).filter_by(id=1).update({"kode": "SIF"})
    db_session.commit()
    candidate = register(client, register_data)
    response = client.put(f"/api/pmb/{candidate['id']}/approve")
    assert response.status_code == 400


def test_reject_approved_candidate_conflict(client, register_data):
    candidate = register(client, register_data)
    assert client.put(f"/api/pmb/{candidate['id']}/approve").status_code == 200
    response = client.put(f"/api/pmb/{candidate['id']}/reject")
    assert response.status_code == 409


def test_status_endpoint(client, register_data):
    candidate = register(client, register_data)
    response = client.get(f"/api/pmb/status/{candidate['id']}")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_status_not_found(client):
    assert client.get("/api/pmb/status/999").status_code == 404


def test_stats_grouped_counts(client, register_data):
    register(client, register_data)
    second = {**register_data, "email": "second@example.com", "jalur_masuk_id": 2}
    register(client, second)
    stats = client.get("/api/pmb/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["total_pendaftar"] == 2
    assert body["berdasarkan_status"]["pending"] == 2
    assert {item["nama"] for item in body["berdasarkan_program_studi"]} == {"Sistem Informasi", "Teknik Informatika"}


def test_approve_sequence_exhausted_returns_conflict(client, db_session, register_data):
    from datetime import datetime, timezone
    from app.models import NIMCounter

    candidate = register(client, register_data)
    db_session.add(
        NIMCounter(
            tahun=datetime.now(timezone.utc).year,
            kode_prodi="001",
            last_number=9999,
        )
    )
    db_session.commit()
    response = client.put(f"/api/pmb/{candidate['id']}/approve")
    assert response.status_code == 409


def test_reject_not_found(client):
    response = client.put("/api/pmb/999/reject")
    assert response.status_code == 404

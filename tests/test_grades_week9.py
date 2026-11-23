"""Week 9: 14 parametrized GPA cases + 3 Hypothesis properties + integration."""
from decimal import Decimal
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from hypothesis import given, strategies as st, settings
from app.main import app
from app.routers.grades import get_presensi
from app.services.gpa import Skala, NilaiRecord as R, hitung_ips, hitung_ipk
from app.services.grade_service import GradeService, GradeError, PresensiStub
from app.services.nilai_repo import NilaiRepo, GPACalculator
from app.models import KRS, KRSDetail, KRSStatus, MataKuliah, SkalaNilai
from app.models.scheduling import Dosen, Kelas, Jadwal, Ruangan
from app.models.grades import GradeHistory
from datetime import time

_NO_PRESENSI_OVERRIDE = object()


@pytest.fixture
def grade_api_client(client):
    def put_grade(
        *,
        dosen_id=901,
        nilai="A",
        reason=None,
        attendance=_NO_PRESENSI_OVERRIDE,
    ):
        if attendance is _NO_PRESENSI_OVERRIDE:
            app.dependency_overrides.pop(get_presensi, None)
        else:
            app.dependency_overrides[get_presensi] = lambda: PresensiStub(
                {("9010001", 901): attendance}
            )

        try:
            return client.put(
                "/api/kelas/901/nilai/9010001",
                headers={
                    "x-actor-role": "dosen",
                    "x-dosen-id": str(dosen_id),
                },
                json={"nilai": nilai, "reason": reason},
            )
        finally:
            app.dependency_overrides.pop(get_presensi, None)

    return put_grade


S = {k: Skala(Decimal(str(n)), passed) for k, n, passed in [
    ("A", 4, True), ("B", 3, True), ("C", 2, True), ("D", 1, False), ("E", 0, False)]}
def r(k, sem, sks, grade): return R(k, sem, sks, grade)

@pytest.mark.parametrize('records,expected', [
    ([r('a','20241',3,'A')], '4.00'),
    ([], '0.00'),
    ([r('a','20241',3,'E')], '0.00'),
    ([r('a','20241',3,'D')], '0.00'),
    ([r('a','20241',3,'C')], '2.00'),
    ([r('a','20241',3,'E'),r('a','20242',3,'B')], '3.00'),
    ([r('a','20241',3,'A'),r('a','20242',3,'C')], '4.00'),
    ([r('a','20241',3,'A'),r('a','20242',3,'A')], '4.00'),
    ([r('a','20241',3,'A'),r('b','20241',3,'B')], '3.50'),
    ([r('a','20241',3,'A'),r('b','20241',1,'B')], '3.75'),
    ([r('a','20241',1,'A'),r('b','20241',2,'B')], '3.33'),
    ([r('a','20241',3,'D'),r('b','20241',3,'A')], '4.00'),
    ([r('a','20241',1,'C'),r('b','20241',3,'A')], '3.50'),
    ([r('a','20241',3,'C'),r('b','20241',3,'B'),r('c','20241',3,'A')], '3.00'),
])
def test_ipk_parametrized(records, expected):
    assert hitung_ipk(records, S) == Decimal(expected)

@pytest.mark.parametrize('records,semester,expected', [
    ([], '20241', '0.00'),
    ([r('a','20241',3,'E'),r('b','20241',3,'A')], '20241', '2.00'),
    ([r('a','20241',3,'A'),r('b','20242',3,'B')], '20241', '4.00'),
    ([r('a','20241',1,'C'),r('b','20241',2,'B')], '20241', '2.67'),
])
def test_ips_parametrized(records, semester, expected):
    assert hitung_ips(records, S, semester) == Decimal(expected)

def test_round_half_up_once():
    special = {'X':Skala(Decimal('3.125'), True)}
    assert hitung_ipk([r('x','20241',1,'X')], special) == Decimal('3.13')

def test_lulus_is_data():
    scale = dict(S)
    scale['D'] = Skala(Decimal('1'), True)
    assert hitung_ipk([r('a','20241',3,'D')], scale) == Decimal('1.00')

@given(st.lists(st.tuples(st.integers(min_value=1,max_value=4), st.sampled_from(list(S))), max_size=30))
def test_property_gpa_bounds(items):
    rows = [r(str(i),'20241',s,g) for i,(s,g) in enumerate(items)]
    assert Decimal('0') <= hitung_ipk(rows,S) <= Decimal('4')

@given(st.lists(st.tuples(st.integers(min_value=1,max_value=4), st.sampled_from(['A','B','C'])),max_size=30))
def test_property_adding_new_a_never_lowers_gpa(items):
    rows = [r(str(i),'20241',s,g) for i,(s,g) in enumerate(items)]
    assert hitung_ipk(rows+[r('new','20242',3,'A')],S) >= hitung_ipk(rows,S)

@given(st.lists(st.tuples(st.integers(min_value=0,max_value=7), st.sampled_from(list(S))), max_size=40))
def test_property_record_order_irrelevant(items):
    rows = [r(str(i),'20241',3,g) for i,g in items]
    assert hitung_ipk(rows,S) == hitung_ipk(list(reversed(rows)),S)

def setup_grade_data(
    db,
    krs_status=KRSStatus.approved.value,
    initial_grade=None,
):
    db.add_all([SkalaNilai(nilai=k,bobot=v.bobot,lulus=v.lulus) for k,v in S.items()])
    db.add(MataKuliah(kode_mk='T901',nama='Demo',sks=3,hari=1,jam_mulai=time(8),jam_selesai=time(10)))
    db.add(Ruangan(kode='R901',kapasitas=30))
    db.add(Dosen(id=901,nidn='D901',nama='Dosen Demo'))
    db.add(Dosen(id=902,nidn='D902',nama='Dosen Lain'))
    db.flush()
    db.add(Kelas(id=901,kode_mk='T901',nama='A',kuota=30,semester='20241'))
    db.flush()
    db.add(Jadwal(kelas_id=901,hari=1,jam_mulai=time(8),jam_selesai=time(10),ruangan_kode='R901',dosen_id=901))
    # NIM belongs to a registered PMB applicant, fixture only uses dummy data.
    from app.models import CalonMahasiswa
    import inspect
    # The existing API registration flow creates the approved applicant below.
    # Construct via existing model fields to avoid any external API calls.
    db.add(CalonMahasiswa(nama_lengkap='Mahasiswa Dummy',email='dummy901@example.com',phone='081234567890',tanggal_lahir=__import__('datetime').date(2005,1,1),alamat='Dummy',program_studi_id=1,jalur_masuk_id=1,status='approve',nim='9010001'))
    db.flush()
    krs=KRS(nim='9010001',semester='20241',status=krs_status)
    db.add(krs);db.flush()
    detail=KRSDetail(
        krs_id=krs.id,
        kode_mk='T901',
        kelas_id=901,
        nilai=initial_grade,
    )
    db.add(detail);db.commit()
    return detail.id

def test_grade_transaction_and_history(db_session):
    detail_id=setup_grade_data(db_session)
    svc=GradeService(db_session, PresensiStub({('9010001',901):75}))
    with pytest.raises(GradeError) as err:
        svc.input_nilai(dosen_id=902,kelas_id=901,nim='9010001',nilai='A')
    assert err.value.status_code==403
    assert svc.input_nilai(dosen_id=901,kelas_id=901,nim='9010001',nilai='B')['changed']
    assert GPACalculator(NilaiRepo(db_session)).calculate_ipk('9010001')==Decimal('3.00')
    assert not svc.input_nilai(dosen_id=901,kelas_id=901,nim='9010001',nilai='B')['changed']
    with pytest.raises(GradeError):
        svc.input_nilai(dosen_id=901,kelas_id=901,nim='9010001',nilai='A')
    svc.input_nilai(dosen_id=901,kelas_id=901,nim='9010001',nilai='A',reason='Koreksi penilaian')
    assert GPACalculator(NilaiRepo(db_session)).calculate_ipk('9010001')==Decimal('4.00')
    history=NilaiRepo(db_session).history('9010001')
    assert [(h['old_value'],h['new_value']) for h in history]==[(None,'B'),('B','A')]
    assert db_session.query(GradeHistory).filter_by(grade_id=detail_id).count()==2

def test_grade_form_is_available(client):
    response = client.get("/nilai/form")

    assert response.status_code == 200
    assert "Input Nilai Mahasiswa" in response.text
    assert "/api/kelas/" in response.text

def test_grade_api_accepts_valid_pengampu(db_session, grade_api_client):
    detail_id = setup_grade_data(db_session)

    response = grade_api_client(attendance=80)

    assert response.status_code == 200
    assert response.json()["changed"] is True
    assert db_session.query(GradeHistory).filter_by(grade_id=detail_id).count() == 1

def test_grade_api_rejects_non_pengampu(db_session, grade_api_client):
    detail_id = setup_grade_data(db_session)

    response = grade_api_client(dosen_id=902, attendance=80)

    assert response.status_code == 403
    assert db_session.get(KRSDetail, detail_id).nilai is None
    assert db_session.query(GradeHistory).filter_by(grade_id=detail_id).count() == 0

def test_grade_api_rejects_unapproved_krs(db_session, grade_api_client):
    detail_id = setup_grade_data(db_session, KRSStatus.revision.value)

    response = grade_api_client(attendance=80)

    assert response.status_code == 409
    assert db_session.get(KRSDetail, detail_id).nilai is None
    assert db_session.query(GradeHistory).filter_by(grade_id=detail_id).count() == 0

def test_grade_api_rejects_attendance_below_75(db_session, grade_api_client):
    detail_id = setup_grade_data(db_session)

    response = grade_api_client(attendance=74.99)

    assert response.status_code == 403
    assert db_session.get(KRSDetail, detail_id).nilai is None
    assert db_session.query(GradeHistory).filter_by(grade_id=detail_id).count() == 0

def test_grade_api_accepts_attendance_at_75(db_session, grade_api_client):
    detail_id = setup_grade_data(db_session)

    response = grade_api_client(attendance=75)

    assert response.status_code == 200
    assert response.json()["changed"] is True
    assert db_session.query(GradeHistory).filter_by(grade_id=detail_id).count() == 1

def test_grade_api_rejects_missing_attendance(db_session, grade_api_client):
    detail_id = setup_grade_data(db_session)

    response = grade_api_client()

    assert response.status_code == 409
    assert db_session.get(KRSDetail, detail_id).nilai is None
    assert db_session.query(GradeHistory).filter_by(grade_id=detail_id).count() == 0

def test_grade_api_requires_reason_for_correction(db_session, grade_api_client):
    detail_id = setup_grade_data(db_session, initial_grade="B")

    response = grade_api_client(attendance=75, nilai="A")

    assert response.status_code == 422
    assert db_session.get(KRSDetail, detail_id).nilai == "B"
    assert db_session.query(GradeHistory).filter_by(grade_id=detail_id).count() == 0

def test_grade_api_correction_with_reason_creates_one_history(db_session, grade_api_client):
    detail_id = setup_grade_data(db_session, initial_grade="B")

    response = grade_api_client(
        attendance=75,
        nilai="A",
        reason="Koreksi penilaian",
    )

    history = db_session.query(GradeHistory).filter_by(grade_id=detail_id).all()
    assert response.status_code == 200
    assert len(history) == 1
    assert (history[0].old_value, history[0].new_value) == ("B", "A")
    assert history[0].reason == "Koreksi penilaian"

def test_grade_api_creates_one_history_per_change(db_session, grade_api_client):
    detail_id = setup_grade_data(db_session)

    first = grade_api_client(attendance=75, nilai="B")
    second = grade_api_client(
        attendance=75,
        nilai="A",
        reason="Koreksi penilaian",
    )

    history = (
        db_session.query(GradeHistory)
        .filter_by(grade_id=detail_id)
        .order_by(GradeHistory.id)
        .all()
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert [(row.old_value, row.new_value) for row in history] == [
        (None, "B"),
        ("B", "A"),
    ]

@pytest.mark.parametrize(
    "krs_status",
    [KRSStatus.draft.value, KRSStatus.submitted.value, KRSStatus.revision.value],
)
@pytest.mark.parametrize("initial_grade", [None, "B"])
def test_grade_input_requires_approved_krs(db_session, krs_status, initial_grade):
    detail_id = setup_grade_data(db_session, krs_status, initial_grade)
    service = GradeService(db_session, PresensiStub({("9010001", 901): 75}))

    with pytest.raises(GradeError) as err:
        service.input_nilai(
            dosen_id=901,
            kelas_id=901,
            nim="9010001",
            nilai="A",
            reason="Koreksi penilaian" if initial_grade else None,
        )

    assert err.value.status_code == 409
    assert db_session.get(KRSDetail, detail_id).nilai == initial_grade
    assert db_session.query(GradeHistory).filter_by(grade_id=detail_id).count() == 0
    assert db_session.execute(
        text("SELECT COUNT(*) FROM grade_audit_context")
    ).scalar_one() == 0

def test_grade_audit_triggers_enforce_and_clear_context(db_session):
    detail_id = setup_grade_data(db_session)

    with pytest.raises(IntegrityError):
        db_session.execute(
            text("UPDATE krs_detail SET nilai = 'A' WHERE id = :grade_id"),
            {"grade_id": detail_id},
        )
    db_session.rollback()

    db_session.execute(
        text("""
            INSERT INTO grade_audit_context (grade_id, changed_by, reason)
            VALUES (:grade_id, :changed_by, :reason)
        """),
        {
            "grade_id": detail_id,
            "changed_by": 901,
            "reason": "Koreksi penilaian",
        },
    )
    db_session.execute(
        text("UPDATE krs_detail SET nilai = 'A' WHERE id = :grade_id"),
        {"grade_id": detail_id},
    )
    db_session.commit()

    history = db_session.query(GradeHistory).filter_by(grade_id=detail_id).all()
    assert len(history) == 1
    assert (history[0].old_value, history[0].new_value) == (None, "A")
    assert db_session.execute(
        text("SELECT COUNT(*) FROM grade_audit_context")
    ).scalar_one() == 0

def test_presensi_fail_closed(db_session):
    setup_grade_data(db_session)
    with pytest.raises(GradeError) as err:
        GradeService(db_session, PresensiStub()).input_nilai(dosen_id=901,kelas_id=901,nim='9010001',nilai='A')
    assert err.value.status_code == 409
    with pytest.raises(GradeError) as err:
        GradeService(db_session, PresensiStub({('9010001',901):74.99})).input_nilai(dosen_id=901,kelas_id=901,nim='9010001',nilai='A')
    assert err.value.status_code == 403


def test_ipk_memilih_nilai_tertinggi_yang_lulus():
    """Mata kuliah berulang harus memakai nilai tertinggi yang lulus."""
    skala = {
        "A": Skala(Decimal("4.00"), False),
        "B": Skala(Decimal("3.00"), True),
    }

    records = [
        R("MK001", "20241", 3, "A"),
        R("MK001", "20242", 3, "B"),
    ]

    assert hitung_ipk(records, skala) == Decimal("3.00")

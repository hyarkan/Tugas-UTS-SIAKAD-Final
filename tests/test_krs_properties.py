from datetime import time
from hypothesis import given, settings, strategies as st

from app.services.krs_validators import KRSContext, MAX_SKS, SKSValidator, ConflictValidator
from app.models import KRS, KRSStatus
from app.services.krs_service import KRSForbidden, TransitionError


class DummyCourse:
    def __init__(self, kode_mk, sks=1, hari=1, mulai=8, durasi=1):
        self.kode_mk = kode_mk
        self.nama = kode_mk
        self.sks = sks
        self.hari = hari
        self.jam_mulai = time(mulai)
        self.jam_selesai = time(mulai + durasi)


class DummySession:
    pass


@given(course_sks=st.lists(st.integers(min_value=1, max_value=4), max_size=40))
@settings(max_examples=1000, deadline=None)
def test_property_total_sks_never_exceeds_24_when_courses_are_added(course_sks):
    accepted = []
    total = 0
    validator = SKSValidator()
    for index, sks in enumerate(course_sks):
        candidate = DummyCourse(f"MK{index}", sks=sks)
        result = validator.check(KRSContext("20260010001", "20261", accepted, candidate, DummySession()))
        if result.oke:
            accepted.append(candidate)
            total += sks
        else:
            assert total + sks > MAX_SKS, "Validator menolak mata kuliah tanpa alasan batas SKS."
        assert total <= MAX_SKS, "KRS menerima mata kuliah sehingga total SKS melewati 24."


@given(schedules=st.lists(
    st.tuples(st.integers(1, 3), st.integers(8, 17), st.integers(1, 3)),
    max_size=20,
))
@settings(max_examples=1000, deadline=None)
def test_property_accepted_courses_never_have_overlapping_time_slots(schedules):
    accepted = []
    occupied_slots = set()  # Oracle independen: himpunan slot jam, bukan rumus validator.
    validator = ConflictValidator()
    for index, (day, start, duration) in enumerate(schedules):
        candidate = DummyCourse(f"MK{index}", hari=day, mulai=start, durasi=duration)
        context = KRSContext("20260010001", "20261", accepted, candidate, DummySession())
        result = validator.check(context)
        candidate_slots = {(day, hour) for hour in range(start, start + duration)}
        independently_conflicts = bool(candidate_slots & occupied_slots)
        assert result.oke is (not independently_conflicts)
        if result.oke:
            accepted.append(candidate)
            occupied_slots.update(candidate_slots)
        assert not any(
            a.hari == b.hari and a.jam_mulai < b.jam_selesai and b.jam_mulai < a.jam_selesai
            for i, a in enumerate(accepted) for b in accepted[i + 1:]
        )


LEGAL_TRANSITIONS = {
    ("draft", "submitted", "mahasiswa"),
    ("submitted", "approved", "dosen_pa"),
    ("submitted", "revision", "dosen_pa"),
    ("revision", "submitted", "mahasiswa"),
}


@given(source=st.sampled_from([s.value for s in KRSStatus]),
       target=st.sampled_from([s.value for s in KRSStatus]),
       actor=st.sampled_from(["mahasiswa", "dosen_pa"]))
@settings(max_examples=32, deadline=None)
def test_state_machine_only_allows_four_explicit_transitions(source, target, actor):
    krs = KRS(nim="20260010001", semester="20261", status=source)
    before = krs.status
    if (source, target, actor) in LEGAL_TRANSITIONS:
        krs.transition(target, actor)
        assert krs.status == target
    else:
        try:
            krs.transition(target, actor)
        except (TransitionError, KRSForbidden):
            assert krs.status == before
        else:
            raise AssertionError(f"Transisi ilegal lolos: {source} -> {target} oleh {actor}")

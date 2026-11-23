"""Dua properti Hypothesis: kesetaraan detektor dan invariant jadwal diterima."""
from collections import Counter
from datetime import time
from hypothesis import given, settings, strategies as st
from app.services.schedule_conflicts import ScheduleSlot, detect_naive, detect_schedule_conflict

@st.composite
def schedules(draw):
    count = draw(st.integers(min_value=0,max_value=22))
    result=[]
    for i in range(count):
        day=draw(st.integers(1,3)); start=draw(st.integers(7,16)); duration=draw(st.integers(1,3))
        room=draw(st.integers(1,2)); lecturer=draw(st.integers(1,3))
        result.append(ScheduleSlot(i+1,day,time(start),time(start+duration),f"A{room}",lecturer))
    return result

@given(schedules())
@settings(max_examples=100,deadline=None)
def test_sweep_equals_naive(items):
    assert set(detect_schedule_conflict(items)) == set(detect_naive(items))

@given(schedules())
@settings(max_examples=100,deadline=None)
def test_accepted_schedule_never_overlaps(items):
    accepted=[]
    for item in items:
        if not detect_schedule_conflict([*accepted,item]):
            accepted.append(item)
    room_slots=Counter(); lecturer_slots=Counter()
    for item in accepted:
        for hour in range(item.jam_mulai.hour,item.jam_selesai.hour):
            room_slots[item.hari,hour,item.ruangan_kode]+=1
            lecturer_slots[item.hari,hour,item.dosen_id]+=1
    assert all(v<=1 for v in room_slots.values())
    assert all(v<=1 for v in lecturer_slots.values())

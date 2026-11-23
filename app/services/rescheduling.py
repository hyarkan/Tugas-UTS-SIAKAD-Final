"""Deterministic available slots, AI-compatible JSON suggestions and hard validation."""
from datetime import datetime, time, timedelta
from sqlalchemy import func, select
from app.models.krs import KRS, KRSDetail
from app.models.scheduling import Jadwal, Ruangan, Kelas
from app.schemas.scheduling import JadwalInput
from app.services.scheduling_service import SchedulingService, SchedulingError

DAYS = (1, 2, 3, 4, 5, 6)
START_HOURS = (8, 10, 13, 15)

def available_slots(db, schedule_id):
    current = db.get(Jadwal, schedule_id)
    if current is None:
        return []
    duration = datetime.combine(datetime.today(), current.jam_selesai) - datetime.combine(datetime.today(), current.jam_mulai)
    kelas = db.get(Kelas, current.kelas_id)
    enrolled = db.scalar(
        select(func.count(func.distinct(KRS.nim)))
        .join(KRSDetail, KRSDetail.krs_id == KRS.id)
        .where(
            KRSDetail.kelas_id == kelas.id,
            KRS.status.in_(["submitted", "approved"]),
        )
    ) or 0
    required = max(kelas.kuota, enrolled)
    rooms = db.scalars(select(Ruangan).where(Ruangan.kapasitas >= required).order_by(Ruangan.kode)).all()
    existing = db.scalars(select(Jadwal).where(Jadwal.id != schedule_id)).all()
    options = []
    for day in DAYS:
        for hour in START_HOURS:
            start = time(hour, 0)
            end_dt = datetime.combine(datetime.today(), start) + duration
            if end_dt.date() != datetime.today().date() or end_dt.time() > time(20):
                continue
            end = end_dt.time()
            for room in rooms:
                if (day, start, end, room.kode) == (current.hari, current.jam_mulai, current.jam_selesai, current.ruangan_kode):
                    continue
                if any(other.hari == day and other.jam_mulai < end and start < other.jam_selesai and
                       (other.ruangan_kode == room.kode or other.dosen_id == current.dosen_id) for other in existing):
                    continue
                options.append({"hari": day, "jam_mulai": start.isoformat(timespec="minutes"),
                                "jam_selesai": end.isoformat(timespec="minutes"), "ruangan_kode": room.kode})
    return options

def build_prompt(jadwal, slots):
    import json
    return ("Anda adalah scheduling assistant. Pilih maksimal 3 alternatif dari available_slots "
            "tanpa membuat slot baru. Prioritaskan pagi/siang dan minimalkan gangguan mahasiswa. "
            "Balas HANYA JSON array [{hari, jam_mulai, jam_selesai, ruangan_kode, reason}].\n"
            + json.dumps({"jadwal": jadwal, "available_slots": slots}, ensure_ascii=False))

def saring_saran(db, schedule_id, suggestions):
    """Whitelist against current slots; rerun validation when applying."""
    slots = available_slots(db, schedule_id)
    allowed = {(s["hari"], s["jam_mulai"], s["jam_selesai"], s["ruangan_kode"]) for s in slots}
    valid, seen = [], set()
    for suggestion in suggestions:
        try:
            key = (suggestion["hari"], suggestion["jam_mulai"], suggestion["jam_selesai"], suggestion["ruangan_kode"])
        except (TypeError, KeyError):
            continue
        if key in allowed and key not in seen:
            seen.add(key)
            valid.append({**dict(zip(("hari", "jam_mulai", "jam_selesai", "ruangan_kode"), key)),
                          "reason": str(suggestion.get("reason", "Slot tersedia dan lolos validasi"))[:300]})
        if len(valid) == 3:
            break
    return valid

def deterministic_suggestions(db, schedule_id):
    current = db.get(Jadwal, schedule_id)
    slots = available_slots(db, schedule_id)
    if current is None:
        return []

    def start_minute(slot):
        hour, minute = map(int, slot["jam_mulai"].split(":"))
        return hour * 60 + minute

    def rank(slot):
        same_day = 0 if slot["hari"] == current.hari else 1
        start_distance = abs(start_minute(slot) - (
            current.jam_mulai.hour * 60 + current.jam_mulai.minute
        ))
        same_room = 0 if slot["ruangan_kode"] == current.ruangan_kode else 1
        day_distance = abs(slot["hari"] - current.hari)
        return (
            same_day,
            start_distance,
            same_room,
            day_distance,
            slot["hari"],
            start_minute(slot),
            slot["ruangan_kode"],
        )

    ranked = sorted(slots, key=rank)
    return [{**slot, "reason": "Minimal disruption: mendekati hari, jam mulai, dan ruangan jadwal asli; kapasitas serta bentrokan divalidasi"}
            for slot in ranked[:3]]

def apply_suggestion(db, schedule_id, suggestion):
    current = db.get(Jadwal, schedule_id)
    if current is None:
        from app.services.scheduling_service import ScheduleNotFound
        raise ScheduleNotFound("Jadwal tidak ditemukan")
    valid = saring_saran(db, schedule_id, [suggestion])
    if not valid:
        raise SchedulingError("Saran tidak valid atau slot sudah digunakan; muat ulang saran")
    data = JadwalInput(kelas_id=current.kelas_id, dosen_id=current.dosen_id, **{
        key: valid[0][key] for key in ("hari", "jam_mulai", "jam_selesai", "ruangan_kode")})
    return SchedulingService(db).update(schedule_id, data)

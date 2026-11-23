"""RFC5545-style weekly semester calendar; course times use Asia/Jakarta."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import select
from app.models.scheduling import Jadwal, Kelas
from app.models.outbox import ScheduleOutbox


try:
    _JAKARTA = ZoneInfo("Asia/Jakarta")
except ZoneInfoNotFoundError:
    # Windows installations without the IANA database can still represent
    # Jakarta correctly: its current and 2026 offset is fixed at UTC+07:00.
    _JAKARTA = timezone(timedelta(hours=7), name="Asia/Jakarta")


def escape_ics(value):
    return (str(value).replace('\\', '\\\\').replace('\r\n', '\n')
            .replace('\r', '\n').replace('\n', '\\n')
            .replace(';', '\\;').replace(',', '\\,'))


def _fold_ics_line(line):
    """Fold a content line without splitting UTF-8 code points."""
    physical_lines = []
    current = ""
    limit = 75
    for character in line:
        encoded_length = len(character.encode("utf-8"))
        if current and len(current.encode("utf-8")) + encoded_length > limit:
            physical_lines.append(current)
            current = " "
            limit = 75
        current += character
    physical_lines.append(current)
    return physical_lines

def export_ics(db, semester_start: date, semester_end: date):
    if semester_end < semester_start:
        raise ValueError("Akhir semester harus setelah awal semester")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PMB KRS Minggu8//Jadwal//ID",
        "CALSCALE:GREGORIAN",
        "BEGIN:VTIMEZONE",
        "TZID:Asia/Jakarta",
        "X-LIC-LOCATION:Asia/Jakarta",
        "BEGIN:STANDARD",
        "DTSTART:19700101T000000",
        "TZOFFSETFROM:+0700",
        "TZOFFSETTO:+0700",
        "TZNAME:WIB",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]
    events = db.scalars(select(ScheduleOutbox).where(ScheduleOutbox.event_type == "SCHEDULE_CHANGED")).all()
    for item in db.scalars(select(Jadwal).order_by(Jadwal.id)).all():
        delta = (item.hari - 1 - semester_start.weekday()) % 7
        first = semester_start + timedelta(days=delta)
        if first > semester_end:
            continue
        kelas = db.get(Kelas, item.kelas_id)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        start = datetime.combine(first, item.jam_mulai).strftime("%Y%m%dT%H%M%S")
        end = datetime.combine(first, item.jam_selesai).strftime("%Y%m%dT%H%M%S")
        until_local = datetime.combine(semester_end, time(23, 59, 59), tzinfo=_JAKARTA)
        until = until_local.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        sequence = sum(1 for event in events if (event.payload.get("after") or {}).get("id") == item.id)
        lines += [
            "BEGIN:VEVENT",
            f"UID:jadwal-{item.id}@pmb-mini.local",
            f"SEQUENCE:{sequence}",
            f"DTSTAMP:{stamp}",
            f"DTSTART;TZID=Asia/Jakarta:{start}",
            f"DTEND;TZID=Asia/Jakarta:{end}",
            f"RRULE:FREQ=WEEKLY;UNTIL={until}",
            f"SUMMARY:{escape_ics(kelas.kode_mk + ' ' + kelas.nama)}",
            f"LOCATION:{escape_ics(item.ruangan_kode)}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(
        physical_line for line in lines for physical_line in _fold_ics_line(line)
    ) + "\r\n"

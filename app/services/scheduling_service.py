"""SchedulingService: validasi sebelum commit; tidak bergantung HTTP."""
from sqlalchemy import select, func, or_
import logging
from app.models.outbox import ScheduleOutbox
from app.services.schedule_observers import ScheduleEvent, OutboxDispatcher
from app.services.krs_invalidator import KRSInvalidator
from sqlalchemy.orm import Session
from app.models import KRS, KRSDetail
from app.models.scheduling import Ruangan, Dosen, Kelas, Jadwal
from app.services.schedule_conflicts import Conflict, detect_schedule_conflict

class SchedulingError(Exception):
    status_code = 409
    def __init__(self, message):
        super().__init__(message)
    def body(self):
        return {"message": str(self)}

class ScheduleNotFound(SchedulingError):
    status_code = 404

class ScheduleConflictError(SchedulingError):
    def __init__(self, conflicts):
        super().__init__("Jadwal bentrok dengan penggunaan ruangan dan/atau dosen.")
        self.conflicts = conflicts
    def body(self):
        return {"message": str(self), "conflicts": [{"type": c.type, "affected": list(c.affected)} for c in self.conflicts]}

class CapacityError(SchedulingError):
    pass

def snapshot(obj):
    return {"id": obj.id, "kelas_id": obj.kelas_id, "hari": obj.hari,
            "jam_mulai": obj.jam_mulai.isoformat(), "jam_selesai": obj.jam_selesai.isoformat(),
            "ruangan_kode": obj.ruangan_kode, "dosen_id": obj.dosen_id}

class SchedulingService:
    def __init__(self, db: Session):
        self.db = db

    def _begin_write(self):
        # SQLite tidak mendukung SELECT FOR UPDATE: BEGIN IMMEDIATE mengunci penulis
        # sebelum pembacaan konflik. PostgreSQL/MySQL memakai row lock di bawah.
        if self.db.bind.dialect.name == "sqlite" and not self.db.in_transaction():
            self.db.connection().exec_driver_sql("BEGIN IMMEDIATE")

    def _lock_resources(self, kode, dosen_id):
        # Urutan deterministik: ruangan dahulu, dosen kemudian.
        room = self.db.execute(select(Ruangan).where(Ruangan.kode == kode).with_for_update()).scalar_one_or_none()
        if room is None:
            raise ScheduleNotFound(f"Ruangan {kode} tidak ditemukan.")
        lecturer = self.db.execute(select(Dosen).where(Dosen.id == dosen_id).with_for_update()).scalar_one_or_none()
        if lecturer is None:
            raise ScheduleNotFound(f"Dosen {dosen_id} tidak ditemukan.")
        return room

    def _check_capacity(self, room, kelas):
        # Satu mahasiswa dihitung sekali per kelas, meskipun memiliki beberapa jadwal mingguan.
        enrolled = self.db.scalar(select(func.count(func.distinct(KRS.nim))).join(KRSDetail, KRSDetail.krs_id == KRS.id).where(KRSDetail.kelas_id == kelas.id, KRS.status.in_(["submitted", "approved"]))) or 0
        required = max(kelas.kuota, enrolled)
        if required > room.kapasitas:
            raise CapacityError(f"Ruangan {room.kode} berkapasitas {room.kapasitas}; dibutuhkan {required} kursi (kuota {kelas.kuota}, terdaftar {enrolled}).")

    def _find_conflicts(self, data, exclude_id=None):
        stmt = select(Jadwal).where(
            Jadwal.hari == data.hari,
            Jadwal.jam_mulai < data.jam_selesai,
            Jadwal.jam_selesai > data.jam_mulai,
            or_(Jadwal.ruangan_kode == data.ruangan_kode, Jadwal.dosen_id == data.dosen_id),
        )
        if exclude_id is not None:
            stmt = stmt.where(Jadwal.id != exclude_id)
        matches = self.db.scalars(stmt).all()
        conflicts = []
        for other in matches:
            pair = (other.id, exclude_id if exclude_id is not None else 0)
            if other.ruangan_kode == data.ruangan_kode:
                conflicts.append(Conflict("room_conflict", pair))
            if other.dosen_id == data.dosen_id:
                conflicts.append(Conflict("lecturer_conflict", pair))
        return conflicts

    def _save(self, data, obj, before=None):
        try:
            room = self._lock_resources(data.ruangan_kode, data.dosen_id)
            kelas = self.db.get(Kelas, data.kelas_id)
            if kelas is None:
                raise ScheduleNotFound(f"Kelas {data.kelas_id} tidak ditemukan.")
            conflicts = self._find_conflicts(data, obj.id)
            if conflicts:
                raise ScheduleConflictError(conflicts)
            self._check_capacity(room, kelas)
            for field, value in data.model_dump().items():
                setattr(obj, field, value)
            self.db.add(obj)
            self.db.flush()
            if before is not None:
                after = snapshot(obj)
                if before != after:
                    KRSInvalidator(self.db).invalidate({before["kelas_id"], after["kelas_id"]})
                    event = ScheduleEvent.new("SCHEDULE_CHANGED", before, after)
                    self.db.add(ScheduleOutbox(event_id=event.event_id, event_type=event.event_type,
                                               payload={"before": before, "after": after}))
            self.db.commit()
            self.db.refresh(obj)
            if before is not None and before != snapshot(obj):
                self._dispatch_safely()
            return obj
        except Exception:
            self.db.rollback()
            raise

    def create(self, data):
        self._begin_write()
        return self._save(data, Jadwal())

    def update(self, jadwal_id, data):
        self._begin_write()
        obj = self.db.get(Jadwal, jadwal_id)
        if obj is None:
            raise ScheduleNotFound(f"Jadwal {jadwal_id} tidak ditemukan.")
        return self._save(data, obj, snapshot(obj))

    def delete(self, jadwal_id):
        self._begin_write()
        try:
            obj = self.db.get(Jadwal, jadwal_id)
            if obj is None:
                raise ScheduleNotFound(f"Jadwal {jadwal_id} tidak ditemukan.")
            before = snapshot(obj)
            KRSInvalidator(self.db).invalidate({obj.kelas_id}, "Jadwal kelas dihapus")
            event = ScheduleEvent.new("SCHEDULE_DELETED", before, None)
            self.db.add(ScheduleOutbox(event_id=event.event_id, event_type=event.event_type,
                                       payload={"before": before, "after": None}))
            self.db.delete(obj)
            self.db.commit()
            self._dispatch_safely()
        except Exception:
            self.db.rollback()
            raise

    def _dispatch_safely(self):
        try:
            OutboxDispatcher(self.db).run()
        except Exception:
            logging.getLogger(__name__).exception("Pengiriman outbox tertunda; perubahan jadwal tetap tersimpan")
            self.db.rollback()

    def conflicts(self):
        return detect_schedule_conflict(self.db.scalars(select(Jadwal)).all())

"""Observer (in-process), interchangeable simulated channels and post-commit dispatcher."""
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import KRS, KRSDetail
from app.models.scheduling import Kelas
from app.models.outbox import ScheduleOutbox, DeliveryReceipt

logger = logging.getLogger("app.schedule.notifications")

@dataclass(frozen=True)
class ScheduleEvent:
    event_id: str
    event_type: str
    before: dict | None
    after: dict | None

    @classmethod
    def new(cls, event_type, before, after):
        return cls(str(uuid4()), event_type, before, after)

class Observer(Protocol):
    def update(self, event: ScheduleEvent, db: Session) -> None: ...

class ScheduleSubject:
    def __init__(self):
        self.observers = []

    def attach(self, observer):
        if observer not in self.observers:
            self.observers.append(observer)

    def detach(self, observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def notify(self, event, db=None):
        failures = []
        for observer in tuple(self.observers):
            try:
                observer.update(event, db)
            except Exception:
                name = type(observer).__name__
                logger.exception("Observer gagal: %s", name)
                failures.append(name)
        return failures

class LogChannel:
    """Deduplication persisted in DB; not an external email/SMS/push gateway."""
    def __init__(self, name):
        if name not in {"email", "sms", "push"}:
            raise ValueError("Kanal tidak dikenal")
        self.name = name

    def send(self, db, recipient, message, key):
        if db.get(DeliveryReceipt, key) is not None:
            return False
        # Flush receipt before logging; a failed transaction can retry on next run.
        db.add(DeliveryReceipt(key=key))
        db.flush()
        logger.info("[%s] kepada=%s key=%s pesan=%s", self.name.upper(), recipient, key, message)
        return True

class StudentObserver:
    def __init__(self, channels):
        self.channels = channels

    def update(self, event, db):
        snapshot = event.after or event.before
        if not snapshot:
            return
        kelas_id = snapshot["kelas_id"]
        recipients = db.scalars(select(KRS.nim).join(KRSDetail, KRSDetail.krs_id == KRS.id).where(
            KRSDetail.kelas_id == kelas_id).distinct()).all()
        for nim in recipients:
            for channel in self.channels:
                channel.send(db, nim, f"{event.event_type}: {event.before} -> {event.after}",
                             f"{event.event_id}:student:{nim}:{channel.name}")

class LecturerObserver:
    def __init__(self, channels):
        self.channels = channels

    def update(self, event, db):
        lecturers = {x["dosen_id"] for x in (event.before, event.after) if x}
        for lecturer in lecturers:
            for channel in self.channels:
                channel.send(db, f"dosen:{lecturer}", f"{event.event_type}: jadwal berubah",
                             f"{event.event_id}:lecturer:{lecturer}:{channel.name}")

class AdminObserver:
    def __init__(self, channels):
        self.channels = channels

    def update(self, event, db):
        for channel in self.channels:
            channel.send(db, "admin_akademik", f"{event.event_type}: {event.before} -> {event.after}",
                         f"{event.event_id}:admin:{channel.name}")

def build_subject():
    subject = ScheduleSubject()
    subject.attach(StudentObserver([LogChannel("email"), LogChannel("push")]))
    subject.attach(LecturerObserver([LogChannel("sms"), LogChannel("email")]))
    subject.attach(AdminObserver([LogChannel("push")]))
    return subject

# One subject wired once per application process; no per-request attachments.
SUBJECT = build_subject()

class OutboxDispatcher:
    def __init__(self, db: Session, subject=None):
        self.db = db
        self.subject = subject if subject is not None else SUBJECT

    def run(self, limit=50):
        """Process pending events after commit. SQLite: single worker recommended.

        Observer failures are isolated; receipts for successful channels are committed
        before retry. For real external gateways, use provider-side idempotency.
        """
        results = []
        rows = self.db.scalars(select(ScheduleOutbox).where(ScheduleOutbox.status == "pending")
                               .order_by(ScheduleOutbox.id).limit(limit).with_for_update(skip_locked=True)).all()
        for row in rows:
            event = ScheduleEvent(row.event_id, row.event_type, row.payload.get("before"), row.payload.get("after"))
            try:
                # Save receipts even if a different observer fails, enabling deduplication on retry.
                failures = self.subject.notify(event, self.db)
                row.attempts += 1
                if failures:
                    row.last_error = ", ".join(failures)
                    if row.attempts >= 5:
                        row.status = "failed"
                else:
                    row.status = "sent"
                    row.last_error = None
                self.db.commit()
                results.append({"event_id": row.event_id, "status": row.status, "failures": failures})
            except Exception:
                self.db.rollback()
                logger.exception("Dispatcher gagal memproses event %s", event.event_id)
                # A DB failure cannot be reliably persisted; leave pending for later retry.
                results.append({"event_id": event.event_id, "status": "pending", "failures": ["dispatcher"]})
        return results

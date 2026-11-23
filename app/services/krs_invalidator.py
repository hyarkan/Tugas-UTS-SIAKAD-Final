"""Invalidate only KRS referencing an affected class; never commit here."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import KRS, KRSDetail, KRSLog, KRSNotification

class KRSInvalidator:
    def __init__(self, db: Session):
        self.db = db

    def invalidate(self, kelas_ids, reason="Jadwal kelas berubah"):
        ids = set(kelas_ids)
        if not ids:
            return []
        stmt = (select(KRS).join(KRSDetail, KRSDetail.krs_id == KRS.id)
                .where(KRSDetail.kelas_id.in_(ids), KRS.status.in_(["submitted", "approved"]))
                .distinct().with_for_update())
        changed = []
        for krs in self.db.scalars(stmt).all():
            before = krs.status
            krs.transition("revision", "sistem")
            krs.revision_note = reason
            self.db.add(KRSLog(krs_id=krs.id, actor_role="sistem", actor_id="scheduler",
                               action="invalidate_schedule", from_status=before,
                               to_status="revision", note=reason))
            self.db.add(KRSNotification(krs_id=krs.id, recipient_nim=krs.nim,
                                        message=f"KRS perlu revisi: {reason}", is_read=False))
            changed.append(krs.id)
        return changed

from decimal import Decimal
from decimal import Decimal
import enum
from datetime import datetime, time, timezone
from sqlalchemy import (CheckConstraint, ForeignKey, Integer, String, Numeric, Time,
                        UniqueConstraint, Table, Column, DateTime, Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class KRSStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    revision = "revision"


prerequisite = Table(
    "prerequisite", Base.metadata,
    Column("kode_mk", String(20), ForeignKey("matakuliah.kode_mk", ondelete="CASCADE"), primary_key=True),
    Column("kode_prasyarat", String(20), ForeignKey("matakuliah.kode_mk", ondelete="CASCADE"), primary_key=True),
    CheckConstraint("kode_mk <> kode_prasyarat", name="ck_prerequisite_not_self"),
)


class MataKuliah(Base):
    __tablename__ = "matakuliah"
    __table_args__ = (
        CheckConstraint("sks >= 1 AND sks <= 4", name="ck_matakuliah_sks_range"),
        CheckConstraint("hari >= 1 AND hari <= 6", name="ck_matakuliah_hari_range"),
        CheckConstraint("jam_mulai < jam_selesai", name="ck_matakuliah_valid_time"),
    )
    kode_mk: Mapped[str] = mapped_column(String(20), primary_key=True)
    nama: Mapped[str] = mapped_column(String(150), nullable=False)
    sks: Mapped[int] = mapped_column(Integer, nullable=False)
    hari: Mapped[int] = mapped_column(Integer, nullable=False, comment="1=Senin sampai 6=Sabtu")
    jam_mulai: Mapped[time] = mapped_column(Time, nullable=False)
    jam_selesai: Mapped[time] = mapped_column(Time, nullable=False)
    prasyarat: Mapped[list["MataKuliah"]] = relationship(
        "MataKuliah", secondary=prerequisite,
        primaryjoin=kode_mk == prerequisite.c.kode_mk,
        secondaryjoin=kode_mk == prerequisite.c.kode_prasyarat,
        backref="dibutuhkan_oleh",
    )


class KRS(Base):
    __tablename__ = "krs"
    __table_args__ = (
        UniqueConstraint("nim", "semester", name="uq_krs_nim_semester"),
        CheckConstraint("status IN ('draft','submitted','approved','revision')", name="ck_krs_status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    nim: Mapped[str] = mapped_column(String(20), ForeignKey("calon_mahasiswa.nim", ondelete="RESTRICT"), nullable=False)
    semester: Mapped[str] = mapped_column(String(5), nullable=False, comment="YYYY1=ganjil, YYYY2=genap")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=KRSStatus.draft.value, server_default="draft")
    dosen_pa_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    details: Mapped[list["KRSDetail"]] = relationship(back_populates="krs", cascade="all, delete-orphan")

    __mapper_args__ = {"version_id_col": version}

    ALLOWED_TRANSITIONS = {
        (KRSStatus.draft.value, "mahasiswa"): {KRSStatus.submitted.value},
        (KRSStatus.submitted.value, "dosen_pa"): {KRSStatus.approved.value, KRSStatus.revision.value},
        (KRSStatus.revision.value, "mahasiswa"): {KRSStatus.submitted.value},
        (KRSStatus.submitted.value, "sistem"): {KRSStatus.revision.value},
        (KRSStatus.approved.value, "sistem"): {KRSStatus.revision.value},
    }

    def check_transition(self, target: str, actor_role: str) -> None:
        from app.services.krs_service import KRSForbidden, TransitionError
        allowed = self.ALLOWED_TRANSITIONS.get((self.status, actor_role), set())
        if target in allowed:
            return
        allowed_for_any_actor = set().union(*(
            targets for (source, _role), targets in self.ALLOWED_TRANSITIONS.items()
            if source == self.status
        )) if any(source == self.status for source, _role in self.ALLOWED_TRANSITIONS) else set()
        if target in allowed_for_any_actor:
            raise KRSForbidden("Peran Anda tidak berwenang melakukan transisi status KRS ini.")
        raise TransitionError(f"Transisi status KRS tidak diizinkan: {self.status} → {target}.")

    def transition(self, target: str, actor_role: str) -> None:
        self.check_transition(target, actor_role)
        self.status = target
        self.updated_at = datetime.now(timezone.utc)


class KRSDetail(Base):
    __tablename__ = "krs_detail"
    __table_args__ = (UniqueConstraint("krs_id", "kode_mk", name="uq_krs_detail_krs_mk"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    krs_id: Mapped[int] = mapped_column(ForeignKey("krs.id", ondelete="CASCADE"), nullable=False)
    kode_mk: Mapped[str] = mapped_column(String(20), ForeignKey("matakuliah.kode_mk", ondelete="RESTRICT"), nullable=False)
    kelas_id: Mapped[int | None] = mapped_column(ForeignKey("kelas.id", ondelete="RESTRICT"), nullable=True)
    nilai: Mapped[str | None] = mapped_column(String(2), ForeignKey("skala_nilai.nilai", ondelete="RESTRICT"), nullable=True)
    krs: Mapped[KRS] = relationship(back_populates="details")
    mata_kuliah: Mapped[MataKuliah] = relationship()


class SkalaNilai(Base):
    __tablename__ = "skala_nilai"
    nilai: Mapped[str] = mapped_column(String(2), primary_key=True)
    bobot: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False, unique=True)
    lulus: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="0")
    __table_args__ = (CheckConstraint("bobot >= 0 AND bobot <= 4", name="ck_skala_nilai_bobot"),)


class KRSLog(Base):
    __tablename__ = "krs_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    krs_id: Mapped[int] = mapped_column(ForeignKey("krs.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(30), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    from_status: Mapped[str] = mapped_column(String(20), nullable=False)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class KRSNotification(Base):
    __tablename__ = "krs_notification"
    id: Mapped[int] = mapped_column(primary_key=True)
    krs_id: Mapped[int] = mapped_column(ForeignKey("krs.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_nim: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(default=False, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

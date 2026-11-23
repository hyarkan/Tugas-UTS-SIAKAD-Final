from datetime import datetime, timezone
import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models import (
    CalonMahasiswa, JalurMasuk, NIMCounter, ProgramStudi, StatusPMB
)
from app.schemas.register import RegisterRequest


class EmailAlreadyRegistered(Exception):
    pass


class InvalidReference(Exception):
    pass


class CandidateNotFound(Exception):
    pass


class InvalidNIMData(Exception):
    pass


class CandidateStateConflict(Exception):
    pass


class NIMSequenceExhausted(Exception):
    pass


def register_candidate(db: Session, payload: RegisterRequest) -> CalonMahasiswa:
    if db.scalar(select(CalonMahasiswa.id).where(CalonMahasiswa.email == str(payload.email))):
        raise EmailAlreadyRegistered

    if db.get(ProgramStudi, payload.program_studi_id) is None:
        raise InvalidReference("Program studi tidak ditemukan.")
    if db.get(JalurMasuk, payload.jalur_masuk_id) is None:
        raise InvalidReference("Jalur masuk tidak ditemukan.")

    candidate = CalonMahasiswa(
        nama_lengkap=payload.nama_lengkap,
        email=str(payload.email),
        phone=payload.phone,
        tanggal_lahir=payload.tanggal_lahir,
        alamat=payload.alamat,
        program_studi_id=payload.program_studi_id,
        jalur_masuk_id=payload.jalur_masuk_id,
        status=StatusPMB.pending,
    )
    db.add(candidate)
    try:
        db.commit()
        db.refresh(candidate)
    except IntegrityError as exc:
        db.rollback()
        if "email" in str(exc).lower() or "unique" in str(exc).lower():
            raise EmailAlreadyRegistered from exc
        raise InvalidReference("Referensi data tidak valid.") from exc
    return candidate


def generate_nim(db: Session, candidate: CalonMahasiswa, tahun: int) -> str:
    """Naikkan counter dalam transaksi milik pemanggil; fungsi ini tidak commit."""
    program = db.get(ProgramStudi, candidate.program_studi_id)
    if program is None:
        raise InvalidNIMData("Program studi tidak ditemukan.")
    if not re.fullmatch(r"\d{3}", program.kode or ""):
        raise InvalidNIMData("Kode program studi harus terdiri dari tepat 3 digit angka.")

    stmt = (
        select(NIMCounter)
        .where(
            NIMCounter.tahun == tahun,
            NIMCounter.kode_prodi == program.kode,
        )
        .with_for_update()
    )
    counter = db.scalar(stmt)
    if counter is None:
        counter = NIMCounter(tahun=tahun, kode_prodi=program.kode, last_number=0)
        db.add(counter)
        db.flush()

    next_number = counter.last_number + 1
    if next_number > 9999:
        raise NIMSequenceExhausted("Nomor urut NIM untuk tahun dan program studi ini sudah mencapai 9999.")

    counter.last_number = next_number
    db.flush()
    return f"{tahun:04d}{program.kode}{next_number:04d}"


def approve_candidate(db: Session, candidate_id: int) -> CalonMahasiswa:
    # SQLite tidak mendukung SELECT FOR UPDATE. BEGIN IMMEDIATE mengambil
    # write reservation sebelum pembacaan sehingga approve bersamaan terserialisasi.
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")

    candidate = db.scalar(
        select(CalonMahasiswa)
        .where(CalonMahasiswa.id == candidate_id)
        .with_for_update()
    )
    if candidate is None:
        db.rollback()
        raise CandidateNotFound("Pendaftar tidak ditemukan.")

    if candidate.status == StatusPMB.approve:
        # Idempotent: kembalikan NIM yang sudah ada tanpa menyentuh counter.
        db.commit()
        return candidate

    if candidate.status == StatusPMB.rejected:
        db.rollback()
        raise CandidateStateConflict("Pendaftar yang sudah rejected tidak dapat di-approve.")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    year = now.year

    # Retry membantu menghadapi benturan UNIQUE saat pembuatan counter pertama
    # pada database multi-worker. SQLite diserialisasi oleh BEGIN IMMEDIATE.
    for attempt in range(3):
        try:
            nim = generate_nim(db, candidate, year)
            candidate.nim = nim
            candidate.status = StatusPMB.approve
            candidate.approve_at = now
            db.commit()
            db.refresh(candidate)
            return candidate
        except (IntegrityError, OperationalError):
            db.rollback()
            if attempt == 2:
                raise
            if db.get_bind().dialect.name == "sqlite":
                db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            candidate = db.scalar(
                select(CalonMahasiswa)
                .where(CalonMahasiswa.id == candidate_id)
                .with_for_update()
            )
            if candidate is None:
                raise CandidateNotFound("Pendaftar tidak ditemukan.")
            if candidate.status == StatusPMB.approve:
                db.commit()
                return candidate
    raise RuntimeError("Gagal membuat NIM setelah percobaan ulang.")


def reject_candidate(db: Session, candidate_id: int) -> CalonMahasiswa:
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    candidate = db.scalar(
        select(CalonMahasiswa)
        .where(CalonMahasiswa.id == candidate_id)
        .with_for_update()
    )
    if candidate is None:
        raise CandidateNotFound("Pendaftar tidak ditemukan.")
    if candidate.status != StatusPMB.pending:
        raise CandidateStateConflict("Hanya pendaftar berstatus pending yang dapat ditolak.")
    candidate.status = StatusPMB.rejected
    db.commit()
    db.refresh(candidate)
    return candidate


def get_candidate_status(db: Session, candidate_id: int) -> CalonMahasiswa:
    candidate = db.get(CalonMahasiswa, candidate_id)
    if candidate is None:
        raise CandidateNotFound("Pendaftar tidak ditemukan.")
    return candidate


def get_pmb_stats(db: Session) -> dict:
    total = db.scalar(select(func.count(CalonMahasiswa.id))) or 0
    status_rows = db.execute(
        select(CalonMahasiswa.status, func.count(CalonMahasiswa.id))
        .group_by(CalonMahasiswa.status)
    ).all()
    status_counts = {status.value: count for status, count in status_rows}
    for item in StatusPMB:
        status_counts.setdefault(item.value, 0)

    prodi_rows = db.execute(
        select(ProgramStudi.nama, func.count(CalonMahasiswa.id))
        .outerjoin(CalonMahasiswa, CalonMahasiswa.program_studi_id == ProgramStudi.id)
        .group_by(ProgramStudi.id, ProgramStudi.nama)
        .order_by(ProgramStudi.nama)
    ).all()
    jalur_rows = db.execute(
        select(JalurMasuk.nama, func.count(CalonMahasiswa.id))
        .outerjoin(CalonMahasiswa, CalonMahasiswa.jalur_masuk_id == JalurMasuk.id)
        .group_by(JalurMasuk.id, JalurMasuk.nama)
        .order_by(JalurMasuk.nama)
    ).all()

    return {
        "total_pendaftar": total,
        "berdasarkan_status": status_counts,
        "berdasarkan_program_studi": [
            {"nama": nama, "jumlah": jumlah} for nama, jumlah in prodi_rows
        ],
        "berdasarkan_jalur_masuk": [
            {"nama": nama, "jumlah": jumlah} for nama, jumlah in jalur_rows
        ],
    }

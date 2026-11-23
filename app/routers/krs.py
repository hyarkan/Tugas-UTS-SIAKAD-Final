from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import KRS, KRSDetail, MataKuliah
from app.schemas.krs import (AddCourseRequest, KRSDetailResponse, KRSResponse,
    KRSValidationResponse, SubmitKRSRequest, ApproveKRSRequest, ReviseKRSRequest)
from app.services.krs_service import (KRSError, KRSManager)

router = APIRouter(prefix="/api/krs", tags=["KRS"])


def _require_student(role: str | None, actor_nim: str | None, nim: str) -> None:
    if role != "mahasiswa":
        raise HTTPException(status_code=403, detail="Aksi ini hanya dapat dilakukan oleh mahasiswa.")
    if actor_nim != nim:
        raise HTTPException(status_code=403, detail="Mahasiswa hanya boleh mengakses dan mengubah KRS miliknya sendiri.")


def _raise_http(exc: Exception):
    if isinstance(exc, KRSError):
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    raise exc


@router.post("/{nim}/{semester}/courses", response_model=KRSDetailResponse, status_code=201,
             summary="Menambahkan mata kuliah ke KRS milik mahasiswa")
def add_course_endpoint(nim: str, semester: str, payload: AddCourseRequest,
    x_actor_role: str | None = Header(default=None), x_actor_nim: str | None = Header(default=None),
    db: Session = Depends(get_db)):
    _require_student(x_actor_role, x_actor_nim, nim)
    if len(semester) != 5 or not semester[:4].isdigit() or semester[4] not in "12":
        raise HTTPException(status_code=422, detail="Format semester harus YYYY1 (ganjil) atau YYYY2 (genap).")
    try:
        return KRSManager(db, semester).add_course(nim, payload.kode_mk)
    except Exception as exc:
        _raise_http(exc)


@router.delete("/{nim}/{semester}/courses/{kode_mk}", status_code=204,
               summary="Menghapus mata kuliah dari KRS milik mahasiswa")
def remove_course_endpoint(nim: str, semester: str, kode_mk: str,
    x_actor_role: str | None = Header(default=None), x_actor_nim: str | None = Header(default=None),
    db: Session = Depends(get_db)):
    _require_student(x_actor_role, x_actor_nim, nim)
    try:
        KRSManager(db, semester).remove_course(nim, kode_mk)
        return None
    except Exception as exc:
        _raise_http(exc)


@router.get("/{nim}/{semester}/validate", response_model=KRSValidationResponse)
def validate_krs_endpoint(nim: str, semester: str, db: Session = Depends(get_db)):
    try:
        errors = KRSManager(db, semester).validate_krs(nim)
        return {"valid": not errors, "errors": errors}
    except Exception as exc:
        _raise_http(exc)


@router.post("/{nim}/{semester}/submit", response_model=KRSResponse, summary="Mahasiswa mengajukan KRS")
def submit_krs_endpoint(nim: str, semester: str, payload: SubmitKRSRequest,
    x_actor_role: str | None = Header(default=None), x_actor_nim: str | None = Header(default=None),
    db: Session = Depends(get_db)):
    _require_student(x_actor_role, x_actor_nim, nim)
    try:
        krs = KRSManager(db, semester).submit_krs(nim, x_actor_nim, payload.version)
        return _serialize_krs(db, krs)
    except Exception as exc:
        _raise_http(exc)


@router.post("/{nim}/{semester}/approve", response_model=KRSResponse, summary="Dosen PA menyetujui KRS")
def approve_krs_endpoint(nim: str, semester: str, payload: ApproveKRSRequest,
    x_actor_role: str | None = Header(default=None), x_actor_id: int | None = Header(default=None),
    db: Session = Depends(get_db)):
    if x_actor_role != "dosen_pa" or x_actor_id is None or x_actor_id != payload.dosen_pa_id:
        raise HTTPException(status_code=403, detail="Identitas aktor harus merupakan dosen PA yang melakukan approval.")
    try:
        krs = KRSManager(db, semester).approve_krs(nim, x_actor_id, payload.version)
        return _serialize_krs(db, krs)
    except Exception as exc:
        _raise_http(exc)


@router.post("/{nim}/{semester}/revise", response_model=KRSResponse, summary="Dosen PA meminta revisi KRS")
def revise_krs_endpoint(nim: str, semester: str, payload: ReviseKRSRequest,
    x_actor_role: str | None = Header(default=None), x_actor_id: int | None = Header(default=None),
    db: Session = Depends(get_db)):
    if x_actor_role != "dosen_pa" or x_actor_id is None or x_actor_id != payload.dosen_pa_id:
        raise HTTPException(status_code=403, detail="Identitas aktor harus merupakan dosen PA yang meminta revisi.")
    try:
        krs = KRSManager(db, semester).revise_krs(nim, x_actor_id, payload.version, payload.catatan)
        return _serialize_krs(db, krs)
    except Exception as exc:
        _raise_http(exc)


def _serialize_krs(db: Session, krs: KRS):
    rows = db.execute(select(MataKuliah.nama, MataKuliah.sks)
        .join(KRSDetail, KRSDetail.kode_mk == MataKuliah.kode_mk)
        .where(KRSDetail.krs_id == krs.id)).all()
    return {"id": krs.id, "nim": krs.nim, "semester": krs.semester,
        "status": krs.status, "total_sks": sum(row.sks for row in rows),
        "mata_kuliah": [row.nama for row in rows], "dosen_pa_id": krs.dosen_pa_id,
        "version": krs.version,
        "submitted_at": krs.submitted_at.isoformat() if krs.submitted_at else None,
        "approved_at": krs.approved_at.isoformat() if krs.approved_at else None,
        "revision_note": krs.revision_note}


@router.get("/{nim}/{semester}", response_model=KRSResponse, summary="Melihat KRS mahasiswa")
def get_krs_endpoint(nim: str, semester: str, db: Session = Depends(get_db)):
    krs = db.scalar(select(KRS).where(KRS.nim == nim, KRS.semester == semester))
    if krs is None:
        raise HTTPException(status_code=404, detail="KRS tidak ditemukan.")
    return _serialize_krs(db, krs)

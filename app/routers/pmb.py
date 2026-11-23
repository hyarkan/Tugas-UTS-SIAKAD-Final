from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.register import RegisterRequest, RegisterResponse
from app.schemas.pmb import (
    ApproveResponse, CandidateStatusResponse, RejectResponse, StatsResponse
)
from app.services.pmb_service import (
    CandidateNotFound, CandidateStateConflict, EmailAlreadyRegistered,
    InvalidNIMData, InvalidReference, NIMSequenceExhausted,
    approve_candidate, get_candidate_status, get_pmb_stats,
    register_candidate, reject_candidate,
)

router = APIRouter(prefix="/api/pmb", tags=["PMB"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mendaftarkan calon mahasiswa",
    responses={400: {"description": "Program studi atau jalur masuk tidak valid"},
               409: {"description": "Email sudah terdaftar"}},
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return register_candidate(db, payload)
    except EmailAlreadyRegistered:
        raise HTTPException(status_code=409, detail="Email sudah terdaftar.")
    except InvalidReference as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put(
    "/{candidate_id}/approve",
    response_model=ApproveResponse,
    summary="Menyetujui pendaftaran dan membuat NIM",
    responses={
        400: {"description": "Kode program studi tidak valid untuk NIM"},
        404: {"description": "Pendaftar tidak ditemukan"},
        409: {"description": "Pendaftar sudah ditolak"},
    },
)
def approve(candidate_id: int, db: Session = Depends(get_db)):
    try:
        candidate = approve_candidate(db, candidate_id)
        return {
            "id": candidate.id,
            "nama_lengkap": candidate.nama_lengkap,
            "status": candidate.status.value,
            "nim": candidate.nim,
        }
    except CandidateNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidNIMData as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except CandidateStateConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except NIMSequenceExhausted as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.put(
    "/{candidate_id}/reject",
    response_model=RejectResponse,
    summary="Menolak pendaftaran yang masih pending",
    responses={404: {"description": "Pendaftar tidak ditemukan"},
               409: {"description": "Status pendaftar tidak memungkinkan penolakan"}},
)
def reject(candidate_id: int, db: Session = Depends(get_db)):
    try:
        candidate = reject_candidate(db, candidate_id)
        return {
            "id": candidate.id,
            "nama_lengkap": candidate.nama_lengkap,
            "status": candidate.status.value,
        }
    except CandidateNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except CandidateStateConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get(
    "/status/{candidate_id}",
    response_model=CandidateStatusResponse,
    summary="Memeriksa status pendaftaran",
    responses={404: {"description": "Pendaftar tidak ditemukan"}},
)
def status_pendaftaran(candidate_id: int, db: Session = Depends(get_db)):
    try:
        return get_candidate_status(db, candidate_id)
    except CandidateNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Melihat statistik pendaftaran PMB",
)
def stats(db: Session = Depends(get_db)):
    return get_pmb_stats(db)

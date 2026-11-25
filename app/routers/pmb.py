# ==================================================
# ROUTER PMB — ENDPOINT DAN KONTRAK HTTP
# ==================================================
# APIRouter, Depends, dan HTTPException dipakai untuk mendaftarkan endpoint, menyediakan dependency, serta membentuk respons error HTTP.
# Session adalah tipe session ORM yang diterima handler endpoint.
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# get_db menyediakan session database per request; schema menentukan bentuk request dan response PMB.
from app.database import get_db
from app.schemas.register import RegisterRequest, RegisterResponse
from app.schemas.pmb import (
    ApproveResponse, CandidateStatusResponse, RejectResponse, StatsResponse
)
# Router memanggil fungsi service dan menerjemahkan exception bisnis menjadi status HTTP.
from app.services.pmb_service import (
    CandidateNotFound, CandidateStateConflict, EmailAlreadyRegistered,
    InvalidNIMData, InvalidReference, NIMSequenceExhausted,
    approve_candidate, get_candidate_status, get_pmb_stats,
    register_candidate, reject_candidate,
)

# Semua endpoint di router ini memakai prefix /api/pmb dan dikelompokkan di tag PMB pada dokumentasi API.
router = APIRouter(prefix="/api/pmb", tags=["PMB"])


# >>> FOKUS PRESENTASI UTS <<<
# POST /register menerima pendaftaran baru. response_model menetapkan bentuk output, sedangkan status_code menyatakan hasil sukses 201 Created.
@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mendaftarkan calon mahasiswa",
    # Daftar responses mendokumentasikan kemungkinan error yang dapat diterima klien selain hasil sukses.
    responses={400: {"description": "Program studi atau jalur masuk tidak valid"},
               409: {"description": "Email sudah terdaftar"}},
)
# Handler menerima body yang sudah divalidasi sebagai RegisterRequest dan memperoleh session melalui dependency FastAPI.
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        # Pemanggilan service menjalankan aturan bisnis; handler menyerahkan data dan session tanpa memindahkan aturan tersebut ke router.
        return register_candidate(db, payload)
    # EmailAlreadyRegistered dipetakan menjadi HTTP 409 agar klien tahu konflik karena alamat email telah dipakai.
    except EmailAlreadyRegistered:
        raise HTTPException(status_code=409, detail="Email sudah terdaftar.")
    # Referensi program studi atau jalur masuk yang tidak valid menjadi HTTP 400 Bad Request.
    except InvalidReference as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# PUT /{candidate_id}/approve menjalankan persetujuan untuk satu pendaftar; detail transaksi dan NIM dibahas pada kelompok berikutnya.
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
# Handler approval menerima ID dari path dan session database yang diinjeksi FastAPI.
def approve(candidate_id: int, db: Session = Depends(get_db)):
    try:
        # Service menjalankan proses approval; router menyiapkan bentuk response setelah service mengembalikan objek pendaftar.
        candidate = approve_candidate(db, candidate_id)
        # Response mengirim identitas, status enum sebagai string, dan NIM yang dihasilkan service.
        return {
            "id": candidate.id,
            "nama_lengkap": candidate.nama_lengkap,
            "status": candidate.status.value,
            "nim": candidate.nim,
        }
    # Exception bisnis dibedakan menurut penyebabnya agar API mengembalikan status HTTP yang sesuai.
    except CandidateNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    # Data program studi yang tidak dapat dipakai untuk NIM dipetakan sebagai HTTP 400.
    except InvalidNIMData as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    # Konflik status pendaftar dipetakan menjadi HTTP 409 Conflict.
    except CandidateStateConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    # Kapasitas urutan NIM yang habis juga merupakan konflik yang dapat ditindaklanjuti oleh klien.
    except NIMSequenceExhausted as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# PUT /{candidate_id}/reject menolak pendaftar melalui fungsi service dan memakai schema response khusus.
@router.put(
    "/{candidate_id}/reject",
    response_model=RejectResponse,
    summary="Menolak pendaftaran yang masih pending",
    responses={404: {"description": "Pendaftar tidak ditemukan"},
               409: {"description": "Status pendaftar tidak memungkinkan penolakan"}},
)
# ID pendaftar berasal dari path; session kembali disediakan sebagai dependency request.
def reject(candidate_id: int, db: Session = Depends(get_db)):
    try:
        # Service memeriksa keberadaan dan status pendaftar sebelum mengubah statusnya.
        candidate = reject_candidate(db, candidate_id)
        # Hanya atribut yang dibutuhkan kontrak RejectResponse yang dikirim kembali.
        return {
            "id": candidate.id,
            "nama_lengkap": candidate.nama_lengkap,
            "status": candidate.status.value,
        }
    # Pendaftar yang tidak ada menjadi HTTP 404 Not Found.
    except CandidateNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    # Status yang tidak mengizinkan penolakan dipetakan menjadi HTTP 409 Conflict.
    except CandidateStateConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# GET /status/{candidate_id} menyediakan pemeriksaan status pendaftaran tanpa mengubah data.
@router.get(
    "/status/{candidate_id}",
    response_model=CandidateStatusResponse,
    summary="Memeriksa status pendaftaran",
    responses={404: {"description": "Pendaftar tidak ditemukan"}},
)
# Handler meminta data status dari service dan mengembalikan schema CandidateStatusResponse.
def status_pendaftaran(candidate_id: int, db: Session = Depends(get_db)):
    try:
        # Service mengembalikan objek pendaftar; FastAPI/Pydantic membentuk response sesuai schema.
        return get_candidate_status(db, candidate_id)
    # ID yang tidak ditemukan dikembalikan kepada klien sebagai HTTP 404.
    except CandidateNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# GET /stats mengirim ringkasan agregat sesuai kontrak StatsResponse.
@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Melihat statistik pendaftaran PMB",
)
# Dependency get_db menyediakan session untuk query agregat statistik.
def stats(db: Session = Depends(get_db)):
    # Penghitungan dan pengelompokan data tetap menjadi tanggung jawab service.
    return get_pmb_stats(db)

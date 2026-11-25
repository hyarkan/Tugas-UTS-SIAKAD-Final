# ==================================================
# SCHEMA PMB — STATUS, APPROVAL, REJECTION, DAN STATISTIK
# ==================================================
# datetime dipakai untuk waktu persetujuan; BaseModel menyusun kontrak response API.
from datetime import datetime
from pydantic import BaseModel, ConfigDict


# CandidateStatusResponse membatasi bentuk data yang dikirim saat status pendaftar diminta.
class CandidateStatusResponse(BaseModel):
    # Konfigurasi ini mengizinkan response dibuat dari atribut model SQLAlchemy.
    model_config = ConfigDict(from_attributes=True)

    # Informasi inti pendaftar dikirim bersama status dan NIM bila sudah tersedia.
    id: int
    nama_lengkap: str
    status: str
    nim: str | None
    # approve_at bersifat opsional karena pendaftar pending atau rejected belum tentu pernah disetujui.
    approve_at: datetime | None


# ApproveResponse adalah kontrak khusus respons endpoint approval.
class ApproveResponse(BaseModel):
    # Endpoint menyertakan identitas calon dan status terbaru setelah proses approval.
    id: int
    nama_lengkap: str
    status: str
    # NIM wajib tersedia pada response ini karena kontrak tersebut digunakan untuk hasil approval.
    nim: str


# RejectResponse berisi hasil penolakan tanpa memasukkan field NIM yang tidak diperlukan.
class RejectResponse(BaseModel):
    # ID, nama, dan status memungkinkan klien mengenali pendaftar serta hasil perubahan status.
    id: int
    nama_lengkap: str
    status: str


# CountItem menjadi bentuk satu item agregat statistik, misalnya jumlah menurut nama program studi.
class CountItem(BaseModel):
    # Nama adalah label kelompok dan jumlah adalah banyak data pada kelompok tersebut.
    nama: str
    jumlah: int


# StatsResponse membentuk kontrak ringkasan statistik PMB untuk endpoint statistik.
class StatsResponse(BaseModel):
    # Total pendaftar mencakup jumlah keseluruhan record yang dihitung service.
    total_pendaftar: int
    # Pemetaan status-ke-jumlah menampung agregasi untuk status PMB.
    berdasarkan_status: dict[str, int]
    # Daftar CountItem merangkum pendaftar berdasarkan program studi.
    berdasarkan_program_studi: list[CountItem]
    # Daftar terpisah ini merangkum pendaftar berdasarkan jalur masuk.
    berdasarkan_jalur_masuk: list[CountItem]

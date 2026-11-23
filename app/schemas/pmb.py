from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CandidateStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama_lengkap: str
    status: str
    nim: str | None
    approve_at: datetime | None


class ApproveResponse(BaseModel):
    id: int
    nama_lengkap: str
    status: str
    nim: str


class RejectResponse(BaseModel):
    id: int
    nama_lengkap: str
    status: str


class CountItem(BaseModel):
    nama: str
    jumlah: int


class StatsResponse(BaseModel):
    total_pendaftar: int
    berdasarkan_status: dict[str, int]
    berdasarkan_program_studi: list[CountItem]
    berdasarkan_jalur_masuk: list[CountItem]

from datetime import time
from pydantic import BaseModel, ConfigDict, Field, model_validator

class JadwalInput(BaseModel):
    kelas_id: int = Field(gt=0)
    hari: int = Field(ge=1, le=6)
    jam_mulai: time
    jam_selesai: time
    ruangan_kode: str = Field(min_length=1, max_length=20)
    dosen_id: int = Field(gt=0)

    @model_validator(mode="after")
    def check_times(self):
        if self.jam_mulai >= self.jam_selesai:
            raise ValueError("jam_mulai harus lebih awal daripada jam_selesai")
        if self.jam_mulai.tzinfo or self.jam_selesai.tzinfo:
            raise ValueError("jam harus berupa waktu lokal tanpa zona waktu")
        return self

class JadwalResponse(JadwalInput):
    model_config = ConfigDict(from_attributes=True)
    id: int

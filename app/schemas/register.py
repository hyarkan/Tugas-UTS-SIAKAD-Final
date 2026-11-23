from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints
from typing import Annotated

Phone = Annotated[
    str,
    StringConstraints(
        pattern=r"^(?:\+62|62|0)8[1-9][0-9]{6,10}$",
        min_length=10,
        max_length=15,
    ),
]

class RegisterRequest(BaseModel):
    nama_lengkap: str = Field(min_length=3, max_length=150)
    email: EmailStr
    phone: Phone
    tanggal_lahir: date
    alamat: str = Field(min_length=1, max_length=300)
    program_studi_id: int = Field(gt=0)
    jalur_masuk_id: int = Field(gt=0)

class RegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama_lengkap: str
    email: EmailStr
    phone: str
    program_studi_id: int
    jalur_masuk_id: int
    status: str
    created_at: datetime
    nim: str | None

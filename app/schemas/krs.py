from pydantic import BaseModel, ConfigDict, Field

class AddCourseRequest(BaseModel):
    kode_mk: str = Field(min_length=1, max_length=20)

class KRSDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    krs_id: int
    kode_mk: str
    nilai: str | None

class KRSResponse(BaseModel):
    id: int
    nim: str
    semester: str
    status: str
    total_sks: int
    mata_kuliah: list[str]
    dosen_pa_id: int | None = None
    version: int = 1
    submitted_at: str | None = None
    approved_at: str | None = None
    revision_note: str | None = None

class KRSValidationResponse(BaseModel):
    valid: bool
    errors: list[str]

class SubmitKRSRequest(BaseModel):
    version: int = Field(ge=1)

class ApproveKRSRequest(BaseModel):
    dosen_pa_id: int = Field(gt=0)
    version: int = Field(ge=1)

class ReviseKRSRequest(BaseModel):
    dosen_pa_id: int = Field(gt=0)
    version: int = Field(ge=1)
    catatan: str = Field(min_length=1, max_length=2000)

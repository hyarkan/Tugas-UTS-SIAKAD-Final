# ==================================================
# SCHEMA KRS — KONTRAK REQUEST DAN RESPONSE API
# ==================================================
# BaseModel membentuk schema Pydantic, ConfigDict mengatur serialisasi, dan Field menetapkan batas/aturan nilai.
from pydantic import BaseModel, ConfigDict, Field

# Request ini menjadi kontrak payload untuk menambahkan mata kuliah.
class AddCourseRequest(BaseModel):
    # Kode mata kuliah wajib diisi dan dibatasi sesuai panjang kode pada model.
    kode_mk: str = Field(min_length=1, max_length=20)

# Response ini mewakili satu detail mata kuliah dalam KRS.
class KRSDetailResponse(BaseModel):
    # Pydantic dapat membaca atribut objek ORM untuk membentuk response detail.
    model_config = ConfigDict(from_attributes=True)
    # ID detail dan ID KRS mengidentifikasi record serta KRS induknya.
    id: int
    krs_id: int
    # Kode mata kuliah dan nilai merupakan bagian data detail yang dikembalikan.
    kode_mk: str
    # Nilai None berarti nilai belum dicatat.
    nilai: str | None

# >>> FOKUS PRESENTASI UTS <<<
# KRSResponse menetapkan bentuk ringkasan KRS yang dikirim ke klien.
class KRSResponse(BaseModel):
    # ID, NIM, semester, dan status mengidentifikasi KRS yang ditampilkan.
    id: int
    nim: str
    semester: str
    status: str
    # Total SKS dan daftar nama mata kuliah merupakan ringkasan isi KRS.
    total_sks: int
    mata_kuliah: list[str]
    # Dosen PA opsional karena penugasannya dapat belum tersedia.
    dosen_pa_id: int | None = None
    # Version dikirim agar klien dapat menyertakan versi data saat mengajukan perubahan status.
    version: int = 1
    # Timestamp response dapat kosong sebelum KRS dikirim atau disetujui.
    submitted_at: str | None = None
    approved_at: str | None = None
    # Catatan revisi opsional dan diisi bila dosen meminta perbaikan.
    revision_note: str | None = None

# Response validasi menyampaikan status keseluruhan dan daftar masalah yang ditemukan.
class KRSValidationResponse(BaseModel):
    # valid bernilai boolean agar klien dapat membedakan hasil lulus/gagal validasi.
    valid: bool
    # errors memuat penjelasan setiap masalah validasi.
    errors: list[str]

# Request submit mewajibkan klien mengirim versi KRS yang sedang dilihatnya.
class SubmitKRSRequest(BaseModel):
    # Versi minimal satu mencegah nilai versi yang tidak valid sebelum masuk ke service.
    version: int = Field(ge=1)

# Request approval membawa identitas dosen PA dan versi KRS yang diharapkan.
class ApproveKRSRequest(BaseModel):
    # ID dosen PA harus positif; pemeriksaan kecocokan aktor dengan KRS dilakukan pada lapisan aplikasi.
    dosen_pa_id: int = Field(gt=0)
    # Versi dipakai untuk menolak approval terhadap data KRS yang sudah berubah.
    version: int = Field(ge=1)

# Request revision membawa data aktor, versi, dan catatan yang akan menjelaskan perbaikan kepada mahasiswa.
class ReviseKRSRequest(BaseModel):
    # ID dosen PA harus berupa nilai positif.
    dosen_pa_id: int = Field(gt=0)
    # Versi memungkinkan sistem mendeteksi permintaan revisi berdasarkan data yang sudah usang.
    version: int = Field(ge=1)
    # Catatan wajib memiliki isi dan dibatasi panjangnya.
    catatan: str = Field(min_length=1, max_length=2000)

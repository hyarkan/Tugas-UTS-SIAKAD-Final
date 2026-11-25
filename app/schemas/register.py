# ==================================================
# SCHEMA PMB — KONTRAK REGISTRASI
# ==================================================
# date dan datetime menetapkan tipe tanggal pada kontrak API.
# Pydantic menyediakan validasi request/response; Annotated menggabungkan tipe Python dengan aturan validasi tambahan.
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints
from typing import Annotated

# Phone memberi satu alias tipe agar aturan format nomor telepon dapat digunakan pada field request.
Phone = Annotated[
    str,
    # StringConstraints memvalidasi nomor sebagai teks sebelum service menerima data registrasi.
    StringConstraints(
        # Pola ini menerima awalan nomor Indonesia yang ditentukan dan membatasi digit setelahnya.
        pattern=r"^(?:\+62|62|0)8[1-9][0-9]{6,10}$",
        # Panjang minimum membantu menolak nomor yang terlalu pendek.
        min_length=10,
        # Panjang maksimum diselaraskan dengan batas kolom phone pada model database.
        max_length=15,
    ),
]

# >>> FOKUS PRESENTASI UTS <<<
# RegisterRequest mendefinisikan bentuk data yang harus dikirim klien untuk mendaftar.
# FastAPI menggunakan schema ini untuk memvalidasi body sebelum memanggil fungsi router PMB.
class RegisterRequest(BaseModel):
    # Nama harus berada di antara batas panjang yang ditetapkan.
    nama_lengkap: str = Field(min_length=3, max_length=150)
    # EmailStr memeriksa format email; pemeriksaan apakah email sudah terdaftar tetap dilakukan oleh service.
    email: EmailStr
    # Field phone menggunakan alias Phone sehingga pemeriksaan pola dan panjang berlaku pada request.
    phone: Phone
    # Pydantic mengonversi tanggal yang valid menjadi objek date sebelum diteruskan ke service.
    tanggal_lahir: date
    # Alamat wajib memiliki setidaknya satu karakter dan tidak boleh melebihi panjang kolom model.
    alamat: str = Field(min_length=1, max_length=300)
    # ID program studi harus berupa bilangan positif; keberadaan ID tersebut diperiksa terpisah di service.
    program_studi_id: int = Field(gt=0)
    # ID jalur masuk juga harus positif, lalu service memeriksa apakah referensinya benar-benar ada.
    jalur_masuk_id: int = Field(gt=0)

# RegisterResponse menentukan data yang boleh dikembalikan setelah registrasi berhasil.
class RegisterResponse(BaseModel):
    # from_attributes memungkinkan Pydantic membentuk response dari atribut objek ORM, bukan hanya dictionary.
    model_config = ConfigDict(from_attributes=True)

    # ID dan field identitas menjadi bagian dari respons hasil registrasi.
    id: int
    nama_lengkap: str
    # Email tetap diserialisasi dan divalidasi sebagai alamat email pada response.
    email: EmailStr
    phone: str
    program_studi_id: int
    jalur_masuk_id: int
    # Status ditampilkan agar pemanggil mengetahui kondisi pendaftaran, misalnya pending.
    status: str
    # Waktu pembuatan bertipe datetime dan merepresentasikan waktu yang tersimpan pada model.
    created_at: datetime
    # NIM nullable karena pendaftar baru belum memperoleh NIM sebelum disetujui.
    nim: str | None

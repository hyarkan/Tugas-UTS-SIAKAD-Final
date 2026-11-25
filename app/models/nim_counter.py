# ==================================================
# MODEL PMB — COUNTER NOMOR NIM
# ==================================================
# CheckConstraint dan tipe kolom membatasi nilai yang dapat disimpan di database.
from sqlalchemy import CheckConstraint, Integer, String
# Mapped dan mapped_column menghubungkan atribut bertipe Python dengan kolom tabel.
from sqlalchemy.orm import Mapped, mapped_column

# Base menyatukan metadata model untuk pemetaan ORM.
from app.models.base import Base


# >>> FOKUS PRESENTASI UTS <<<
# NIMCounter menyimpan nomor urut terakhir untuk pasangan tahun dan kode program studi.
# Pada Class Diagram, counter ini mendukung penerbitan NIM; ia tidak memiliki foreign key langsung ke CalonMahasiswa.
class NIMCounter(Base):
    """Counter nomor urut NIM untuk setiap kombinasi tahun dan kode prodi."""

    __tablename__ = "nim_counter"
    # Dua kolom pembentuk primary key mencegah adanya lebih dari satu counter
    # untuk kombinasi tahun dan kode program studi yang sama.
    __table_args__ = (
        # Batas ini memastikan nomor urut yang tersimpan berada dalam rentang
        # yang dapat diformat sebagai empat digit NIM.
        CheckConstraint(
            "last_number >= 0 AND last_number <= 9999",
            name="ck_nim_counter_range",
        ),
    )

    # Tahun dan kode prodi bersama-sama menjadi composite primary key.
    # Karena keduanya primary key, masing-masing kombinasi pasangan harus unik.
    tahun: Mapped[int] = mapped_column(Integer, primary_key=True)
    kode_prodi: Mapped[str] = mapped_column(String(3), primary_key=True)
    # last_number menyimpan nomor terakhir; nilai awal 0 tersedia di sisi ORM
    # maupun sebagai default di database.
    last_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

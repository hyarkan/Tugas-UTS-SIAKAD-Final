# ==================================================
# DATABASE — ENGINE DAN SESSION
# ==================================================
# create_engine membuat penghubung SQLAlchemy ke database.
# event digunakan di bawah untuk menyiapkan perilaku SQLite saat koneksi dibuat.
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# URL ini menunjuk ke database SQLite bernama pmb.db
# dengan lokasi relatif terhadap direktori kerja aplikasi.
DATABASE_URL = "sqlite:///./pmb.db"

# Engine menjadi titik koneksi ORM ke database.
# SQLite menerima check_same_thread=False agar koneksi dapat dipakai
# pada pola request aplikasi yang melibatkan thread berbeda.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

# ==================================================
# DATABASE — AKTIFKAN FOREIGN KEY SQLITE
# ==================================================
# Pengaturan ini hanya dipasang untuk SQLite. SQLite memerlukan PRAGMA
# foreign_keys=ON secara eksplisit agar constraint foreign key diberlakukan.
if DATABASE_URL.startswith("sqlite"):
    # Listener berjalan setiap kali SQLAlchemy membuka koneksi baru.
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        # Perintah PRAGMA mengaktifkan pemeriksaan foreign key pada koneksi ini.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# ==================================================
# DATABASE — SESSION DAN DEPENDENCY REQUEST
# ==================================================
# sessionmaker membuat factory session yang terikat ke engine.
# autoflush=False berarti perubahan ORM tidak otomatis dikirim sebelum query,
# sedangkan autocommit=False membuat transaksi perlu dikendalikan secara eksplisit.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# >>> FOKUS PRESENTASI UTS <<<
# FastAPI memakai fungsi generator ini sebagai dependency database
# pada endpoint yang meminta Depends(get_db). Setiap request memperoleh session.
def get_db():
    # Session baru menyediakan konteks kerja ORM untuk pemanggil dependency.
    db = SessionLocal()
    try:
        # yield menyerahkan session ke endpoint selama request diproses.
        yield db
    finally:
        # Session selalu ditutup setelah pemrosesan, termasuk bila terjadi exception.
        # Fungsi ini menutup session; commit dan rollback ditangani oleh operasi layanan.
        db.close()

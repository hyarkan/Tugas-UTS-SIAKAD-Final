import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base, JalurMasuk, ProgramStudi


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE grade_audit_context (
                grade_id INTEGER PRIMARY KEY,
                changed_by INTEGER NOT NULL,
                reason TEXT,
                FOREIGN KEY (grade_id)
                    REFERENCES krs_detail(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (changed_by)
                    REFERENCES dosen(id)
                    ON DELETE RESTRICT
            )
        """))
        conn.execute(text("""
            CREATE TRIGGER trg_grade_audit_guard
            BEFORE UPDATE OF nilai ON krs_detail
            WHEN OLD.nilai IS NOT NEW.nilai
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'Perubahan nilai memerlukan konteks audit'
                )
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM grade_audit_context
                    WHERE grade_id = OLD.id
                );
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER trg_grade_audit_history
            AFTER UPDATE OF nilai ON krs_detail
            WHEN OLD.nilai IS NOT NEW.nilai
            BEGIN
                INSERT INTO grade_history (
                    grade_id,
                    old_value,
                    new_value,
                    changed_by,
                    changed_at,
                    reason
                )
                SELECT
                    NEW.id,
                    OLD.nilai,
                    NEW.nilai,
                    ctx.changed_by,
                    CURRENT_TIMESTAMP,
                    ctx.reason
                FROM grade_audit_context AS ctx
                WHERE ctx.grade_id = NEW.id;

                DELETE FROM grade_audit_context
                WHERE grade_id = NEW.id;
            END
        """))
        conn.execute(text("""
            CREATE VIEW v_grade_history AS
            SELECT gh.id, gh.grade_id, k.nim, kd.kode_mk,
                   gh.old_value, gh.new_value, gh.changed_by,
                   d.nama AS dosen_nama, gh.changed_at, gh.reason
            FROM grade_history gh
            JOIN krs_detail kd ON kd.id = gh.grade_id
            JOIN krs k ON k.id = kd.krs_id
            JOIN dosen d ON d.id = gh.changed_by
        """))
    db = TestingSessionLocal()
    db.add_all([
        ProgramStudi(kode="001", nama="Sistem Informasi", fakultas="FSTI"),
        ProgramStudi(kode="002", nama="Teknik Informatika", fakultas="FSTI"),
        JalurMasuk(nama="SNBP"),
        JalurMasuk(nama="SNBT"),
    ])
    db.commit()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def register_data():
    return {
        "nama_lengkap": "Sinta Aminah",
        "email": "sinta@example.com",
        "phone": "081234567890",
        "tanggal_lahir": "2007-04-12",
        "alamat": "Depok",
        "program_studi_id": 1,
        "jalur_masuk_id": 1,
    }

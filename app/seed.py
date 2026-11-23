from datetime import time
from app.database import SessionLocal
from app.models import (JalurMasuk, ProgramStudi, MataKuliah, SkalaNilai, prerequisite)


def seed_data():
    db = SessionLocal()
    try:
        program = db.query(ProgramStudi).filter_by(kode="001").first()
        if not program:
            program = db.query(ProgramStudi).filter_by(nama="Sistem Informasi").first()
            if program:
                program.kode = "001"
            else:
                db.add(ProgramStudi(kode="001", nama="Sistem Informasi", fakultas="FSTI"))

        for nama in ("SNBP", "SNBT", "Mandiri"):
            if not db.query(JalurMasuk).filter_by(nama=nama).first():
                db.add(JalurMasuk(nama=nama))

        grades = [("A", 4, True), ("B", 3, True), ("C", 2, True), ("D", 1, False), ("E", 0, False)]
        for nilai, bobot, lulus in grades:
            if db.get(SkalaNilai, nilai) is None:
                db.add(SkalaNilai(nilai=nilai, bobot=bobot, lulus=lulus))

        courses = [
            ("IF101", "Algoritma dan Pemrograman", 3, 1, time(8, 0), time(10, 0)),
            ("IF201", "Struktur Data", 3, 2, time(8, 0), time(10, 0)),
            ("MA101", "Kalkulus I", 3, 3, time(8, 0), time(10, 0)),
            ("MA201", "Kalkulus II", 3, 4, time(8, 0), time(10, 0)),
            ("SI101", "Pengantar Sistem Informasi", 2, 1, time(10, 0), time(12, 0)),
            ("SI201", "Basis Data", 3, 1, time(9, 0), time(11, 0)),
            ("SI202", "Statistika", 3, 1, time(9, 30), time(11, 30)),
        ]
        for kode, nama, sks, hari, mulai, selesai in courses:
            if db.get(MataKuliah, kode) is None:
                db.add(MataKuliah(kode_mk=kode, nama=nama, sks=sks, hari=hari,
                                  jam_mulai=mulai, jam_selesai=selesai))
        db.flush()
        for pair in (("IF201", "IF101"), ("MA201", "MA101")):
            exists_pair = db.execute(
                prerequisite.select().where(prerequisite.c.kode_mk == pair[0],
                                             prerequisite.c.kode_prasyarat == pair[1])
            ).first()
            if not exists_pair:
                db.execute(prerequisite.insert().values(kode_mk=pair[0], kode_prasyarat=pair[1]))
        db.commit()
        print("Data referensi PMB dan KRS berhasil disiapkan.")
        print(f"Mata kuliah: {db.query(MataKuliah).count()} | Skala nilai: {db.query(SkalaNilai).count()}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()

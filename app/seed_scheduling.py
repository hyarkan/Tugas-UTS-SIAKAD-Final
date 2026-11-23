"""Seed Minggu 7: 10 ruang, 15 dosen, 40 jadwal, 2 konflik impor opsional.
Jalankan setelah `alembic upgrade head` dan `python -m app.seed`.
"""
import argparse
from datetime import time
from sqlalchemy import select
from app.database import SessionLocal
from app.models import MataKuliah
from app.models.scheduling import Ruangan, Dosen, Kelas, Jadwal


def seed_scheduling(include_conflicts=False):
    with SessionLocal() as db:
        try:
            for n in range(1, 11):
                kode = f"A{n:03d}"
                if db.get(Ruangan, kode) is None:
                    db.add(Ruangan(kode=kode, kapasitas=40 if n < 9 else 60))
            for n in range(1, 16):
                nidn = f"000000{n:04d}"
                if not db.scalar(select(Dosen).where(Dosen.nidn == nidn)):
                    db.add(Dosen(nidn=nidn, nama=f"Dosen Simulasi {n:02d}"))
            db.flush()
            courses = db.scalars(select(MataKuliah).order_by(MataKuliah.kode_mk)).all()
            if not courses:
                raise RuntimeError("Mata kuliah belum tersedia. Jalankan python -m app.seed terlebih dahulu.")
            for n in range(40):
                course = courses[n % len(courses)]
                nama = f"M7-{n+1:02d}"
                kelas = db.scalar(select(Kelas).where(Kelas.kode_mk == course.kode_mk, Kelas.nama == nama, Kelas.semester == "20261"))
                if kelas is None:
                    kelas = Kelas(kode_mk=course.kode_mk, nama=nama, kuota=30, semester="20261")
                    db.add(kelas)
                    db.flush()
                # 8 slot berurutan per hari, 5 hari; tiap jadwal ruang & dosen terpisah.
                if not db.scalar(select(Jadwal).where(Jadwal.kelas_id == kelas.id)):
                    day = 1 + n // 8
                    hour = 8 + n % 8
                    dosen_id = db.scalar(select(Dosen.id).order_by(Dosen.id).offset(n % 15).limit(1))
                    db.add(Jadwal(kelas_id=kelas.id, hari=day, jam_mulai=time(hour), jam_selesai=time(hour+1), ruangan_kode=f"A{1+n%10:03d}", dosen_id=dosen_id))
            db.commit()
            if include_conflicts:
                # Simulasi data lama hasil impor yang melewati SchedulingService.
                base = db.scalar(select(Jadwal).order_by(Jadwal.id).limit(1))
                if base is not None:
                    for suffix, room, lecturer in (("ROOM", base.ruangan_kode, None), ("LECT", None, base.dosen_id)):
                        nama = f"IMPORT-{suffix}"
                        course = courses[0]
                        kelas = db.scalar(select(Kelas).where(Kelas.kode_mk == course.kode_mk, Kelas.nama == nama, Kelas.semester == "20261"))
                        if kelas is None:
                            kelas = Kelas(kode_mk=course.kode_mk, nama=nama, kuota=30, semester="20261")
                            db.add(kelas)
                            db.flush()
                        if not db.scalar(select(Jadwal).where(Jadwal.kelas_id == kelas.id)):
                            other_dosen = db.scalar(select(Dosen.id).where(Dosen.id != base.dosen_id).limit(1))
                            other_room = db.scalar(select(Ruangan.kode).where(Ruangan.kode != base.ruangan_kode).limit(1))
                            db.add(Jadwal(kelas_id=kelas.id, hari=base.hari, jam_mulai=base.jam_mulai, jam_selesai=base.jam_selesai, ruangan_kode=room or other_room, dosen_id=lecturer or other_dosen))
                    db.commit()
            print("Seed Minggu 7 selesai: >=10 ruang, >=15 dosen, >=40 jadwal; konflik impor:", include_conflicts)
        except Exception:
            db.rollback()
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-conflicts", action="store_true", help="Tambahkan bentrok data impor khusus demonstrasi GET /conflicts")
    seed_scheduling(parser.parse_args().with_conflicts)

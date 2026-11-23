from dataclasses import dataclass
from abc import ABC, abstractmethod
from sqlalchemy import select, exists, and_
from sqlalchemy.orm import Session
from app.models import KRS, KRSDetail, MataKuliah, SkalaNilai, prerequisite

MAX_SKS = 24


@dataclass(frozen=True)
class ValidationResult:
    oke: bool
    message: str = ""


@dataclass
class KRSContext:
    nim: str
    semester: str
    existing_courses: list[MataKuliah]
    new_course: MataKuliah
    session: Session
    krs_id: int | None = None


class Validator(ABC):
    def __init__(self):
        self.next_validator: Validator | None = None

    def set_next(self, validator: "Validator") -> "Validator":
        self.next_validator = validator
        return validator

    def validate(self, context: KRSContext) -> ValidationResult:
        result = self.check(context)
        if not result.oke or self.next_validator is None:
            return result
        return self.next_validator.validate(context)

    @abstractmethod
    def check(self, context: KRSContext) -> ValidationResult:
        raise NotImplementedError


class DuplicateValidator(Validator):
    def check(self, context):
        if any(course.kode_mk == context.new_course.kode_mk for course in context.existing_courses):
            return ValidationResult(False, f"Mata kuliah {context.new_course.nama} sudah ada di KRS.")
        return ValidationResult(True)


class SKSValidator(Validator):
    def check(self, context):
        total = sum(course.sks for course in context.existing_courses) + context.new_course.sks
        if total > MAX_SKS:
            return ValidationResult(False, f"Total SKS {total} melebihi batas maksimal {MAX_SKS} SKS.")
        return ValidationResult(True)


class PrerequisiteValidator(Validator):
    def check(self, context):
        missing = get_unfulfilled_prerequisites(
            context.session, context.nim, context.semester, context.new_course.kode_mk
        )
        if missing:
            return ValidationResult(False, "Prasyarat tidak terpenuhi: " + ", ".join(missing) + ".")
        return ValidationResult(True)


class ConflictValidator(Validator):
    def check(self, context):
        for current in context.existing_courses:
            overlaps = (
                current.hari == context.new_course.hari
                and current.jam_mulai < context.new_course.jam_selesai
                and context.new_course.jam_mulai < current.jam_selesai
            )
            if overlaps:
                return ValidationResult(
                    False,
                    f"Jadwal bentrok antara {context.new_course.nama} dan {current.nama}.",
                )
        return ValidationResult(True)


def build_chain() -> Validator:
    """Urutan dipilih: duplicate (murah), SKS, prasyarat, lalu konflik."""
    duplicate = DuplicateValidator()
    duplicate.set_next(SKSValidator()).set_next(PrerequisiteValidator()).set_next(ConflictValidator())
    return duplicate


def get_unfulfilled_prerequisites(session: Session, nim: str, semester: str, kode_mk: str) -> list[str]:
    """NOT EXISTS: daftar prasyarat yang belum terbukti lulus pada semester sebelumnya."""
    passed_grade = exists(
        select(1)
        .select_from(KRSDetail)
        .join(KRS, KRS.id == KRSDetail.krs_id)
        .join(SkalaNilai, SkalaNilai.nilai == KRSDetail.nilai)
        .where(
            KRS.nim == nim,
            KRS.semester < semester,
            KRSDetail.kode_mk == prerequisite.c.kode_prasyarat,
            SkalaNilai.lulus.is_(True),
            SkalaNilai.bobot >= 2,
        )
    )
    stmt = (
        select(MataKuliah.nama)
        .select_from(prerequisite)
        .join(MataKuliah, MataKuliah.kode_mk == prerequisite.c.kode_prasyarat)
        .where(prerequisite.c.kode_mk == kode_mk)
        .where(~passed_grade)
        .order_by(MataKuliah.nama)
    )
    return list(session.scalars(stmt).all())

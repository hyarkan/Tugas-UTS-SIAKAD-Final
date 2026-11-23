"""Pure deterministic GPA calculations, independent of database and I/O."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from collections.abc import Mapping, Iterable

ZERO = Decimal("0.00")
@dataclass(frozen=True)
class Skala:
    bobot: Decimal
    lulus: bool

@dataclass(frozen=True)
class NilaiRecord:
    kode_mk: str
    semester: str
    sks: int
    nilai: str

def _rata(records: Iterable[NilaiRecord], skala: Mapping[str, Skala]) -> Decimal:
    rows = list(records)
    total_sks = sum(r.sks for r in rows)
    if not total_sks:
        return ZERO
    mutu = sum((Decimal(r.sks) * skala[r.nilai].bobot for r in rows), Decimal("0"))
    return (mutu / Decimal(total_sks)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def hitung_ips(records: Iterable[NilaiRecord], skala: Mapping[str, Skala], semester: str) -> Decimal:
    return _rata((r for r in records if r.semester == semester), skala)

def hitung_ipk(records: Iterable[NilaiRecord], skala: Mapping[str, Skala]) -> Decimal:
    terbaik: dict[str, NilaiRecord] = {}
    for r in records:
        if not skala[r.nilai].lulus:
            continue
        old = terbaik.get(r.kode_mk)
        if old is None or skala[r.nilai].bobot > skala[old.nilai].bobot:
            terbaik[r.kode_mk] = r
    return _rata(terbaik.values(), skala)

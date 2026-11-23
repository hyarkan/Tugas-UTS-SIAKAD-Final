"""Detektor konflik.

``time_overlap`` adalah kondisi dasar bagi konflik ruangan maupun dosen, bukan
konflik sumber daya tersendiri karena soal tidak menetapkan aturan tambahannya.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import time
from itertools import combinations
from typing import Iterable, Literal, Optional

@dataclass(frozen=True)
class Conflict:
    type: Literal["room_conflict", "lecturer_conflict", "time_overlap"]
    affected: tuple[int, int]

@dataclass(frozen=True)
class ScheduleSlot:
    id: int
    hari: int
    jam_mulai: time
    jam_selesai: time
    ruangan_kode: str
    dosen_id: int

@dataclass(frozen=True)
class _IntervalEntry:
    slot: ScheduleSlot
    index: int

@dataclass(frozen=True)
class _IntervalNode:
    entry: _IntervalEntry
    max_end: time
    left: Optional["_IntervalNode"] = None
    right: Optional["_IntervalNode"] = None

class _IntervalTree:
    """Balanced interval BST augmented with each subtree's maximum end time."""

    def __init__(self, items: Iterable[ScheduleSlot]):
        entries = [
            _IntervalEntry(slot, index)
            for index, slot in enumerate(items)
        ]
        entries.sort(key=lambda entry: (
            entry.slot.jam_mulai,
            entry.slot.jam_selesai,
            entry.slot.id,
            entry.index,
        ))
        self._root = self._build(entries, 0, len(entries))

    def _build(self, entries, start, end):
        if start >= end:
            return None

        middle = (start + end) // 2
        entry = entries[middle]
        left = self._build(entries, start, middle)
        right = self._build(entries, middle + 1, end)
        max_end = entry.slot.jam_selesai
        if left is not None and left.max_end > max_end:
            max_end = left.max_end
        if right is not None and right.max_end > max_end:
            max_end = right.max_end
        return _IntervalNode(entry, max_end, left, right)

    def query(self, start: time, end: time) -> list[_IntervalEntry]:
        """Return entries overlapping [start, end), pruning by subtree max_end."""
        if start >= end:
            return []

        matches = []

        def visit(node):
            if node is None or node.max_end <= start:
                return

            if node.left is not None and node.left.max_end > start:
                visit(node.left)

            slot = node.entry.slot
            if slot.jam_mulai < end and slot.jam_selesai > start:
                matches.append(node.entry)

            if node.right is not None and slot.jam_mulai < end:
                visit(node.right)

        visit(self._root)
        return matches

def _pair(a, b):
    return tuple(sorted((a.id, b.id)))

def _overlap(a, b):
    return a.hari == b.hari and a.jam_mulai < b.jam_selesai and b.jam_mulai < a.jam_selesai

def detect_naive(jadwal):
    result = set()
    for a, b in combinations(jadwal, 2):
        if _overlap(a, b):
            if a.ruangan_kode == b.ruangan_kode:
                result.add(Conflict("room_conflict", _pair(a, b)))
            if a.dosen_id == b.dosen_id:
                result.add(Conflict("lecturer_conflict", _pair(a, b)))
    return sorted(result, key=lambda x: (x.affected, x.type))

def detect_schedule_conflict(jadwal):
    result = set()
    for typ, field in (("room_conflict", "ruangan_kode"), ("lecturer_conflict", "dosen_id")):
        groups = defaultdict(list)
        for item in jadwal:
            groups[(item.hari, getattr(item, field))].append(item)
        for items in groups.values():
            tree = _IntervalTree(items)
            for index, item in enumerate(items):
                for entry in tree.query(item.jam_mulai, item.jam_selesai):
                    if entry.index < index:
                        result.add(Conflict(typ, _pair(entry.slot, item)))
    return sorted(result, key=lambda x: (x.affected, x.type))

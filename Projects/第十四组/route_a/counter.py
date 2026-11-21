"""副旋律：一条与主旋律错开、贴着和声走的对位线。

原则：
* 只用和弦音，音域 G3–G4，尽量待在主旋律下方；
* 与主旋律同时发声时避免同度/小二度；
* 相邻音尽量级进，句尾落在主和弦的根音或三音上；
* 节奏比主旋律疏（每 2 拍一个音），起“对答”而不是“抢戏”的作用。
"""

from __future__ import annotations

from .analysis import phrase_ends
from .harmony import Harmonization, Slot
from .io import Melody, NoteEvent


def _active_pitches(melody: Melody, start: float, end: float) -> list[int]:
    return [n.pitch for n in melody.notes
            if n.start < end - 1e-6 and n.end > start + 1e-6]


def _clash_count(pitch: int, active: list[int]) -> int:
    return sum(1 for m in active if abs(pitch - m) % 12 in (0, 1, 11))


def _pick(candidates: list[int], prev: int | None, active: list[int]) -> int:
    safe = [p for p in candidates if _clash_count(p, active) == 0]
    pool = safe or candidates
    target = prev if prev is not None else 62
    return min(pool, key=lambda p: (_clash_count(p, active), abs(p - target), abs(p - 62)))


def make_counter(melody: Melody, harmony: Harmonization, low: int = 55,
                 high: int = 67, phrase_bars: int = 4) -> list[NoteEvent]:
    ends = phrase_ends(melody, phrase_bars)
    notes: list[NoteEvent] = []
    prev: int | None = None

    for slot in harmony.slots:
        if slot.chord is None:
            continue
        pcs = set(slot.chord.pcs)

        is_end = (slot.bar in ends
                  and abs(slot.end - (melody.grid_start + (slot.bar + 1) * melody.beats_per_bar)) < 1e-6)
        if is_end:
            points = [(0.0, max(1.2, slot.length * 0.95))]
        elif slot.length >= 3.5:
            points = [(0.0, 1.4), (2.0, 0.9), (3.0, 0.9)]
        else:
            points = [(0.0, max(0.8, slot.length * 0.9))]

        for offset, dur in points:
            at = slot.start + offset
            if is_end:
                tonic = {slot.chord.root_pc, (slot.chord.root_pc + 4) % 12,
                         (slot.chord.root_pc + 3) % 12}
                candidates = [p for p in range(low, high + 1)
                              if p % 12 in (pcs & tonic)] or \
                             [p for p in range(low, high + 1) if p % 12 in pcs]
            else:
                candidates = [p for p in range(low, high + 1) if p % 12 in pcs]
            if not candidates:
                continue
            if prev is not None:
                varied = [p for p in candidates if p % 12 != prev % 12]
                candidates = varied or candidates
            active = _active_pitches(melody, at, at + dur)
            pitch = _pick(candidates, prev, active)
            notes.append(NoteEvent(pitch, at, dur, 72))
            prev = pitch

    return notes

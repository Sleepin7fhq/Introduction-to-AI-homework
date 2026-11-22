"""低音线：转位与经过音。

* 转位：在根音/三音/五音里选低音，优先级进，终止处回根音；
* 经过音：两个低音相隔二度、且中间有空隙时，补一个级进经过音。
"""

from __future__ import annotations

from .harmony import Slot
from .io import Melody, NoteEvent


def _third(chord) -> int:
    root = chord.root_pc
    pcs = set(chord.pcs)
    if (root + 3) % 12 in pcs:
        return (root + 3) % 12
    if (root + 4) % 12 in pcs:
        return (root + 4) % 12
    return root


def _fifth(chord) -> int:
    root = chord.root_pc
    pcs = set(chord.pcs)
    if (root + 7) % 12 in pcs:
        return (root + 7) % 12
    if (root + 6) % 12 in pcs:
        return (root + 6) % 12
    return root


def _pitches(pc: int, low: int = 36, high: int = 52) -> list[int]:
    return [p for p in range(low, high + 1) if p % 12 == pc]


def choose(chord, prev: int | None, next_chord=None, final: bool = False) -> tuple[int, str]:
    """返回 (低音 MIDI, 类型 root/third/fifth)。"""
    root = chord.root_pc
    options: list[tuple[int, str]] = []
    for pc, label in ((root, "root"), (_third(chord), "third"), (_fifth(chord), "fifth")):
        for pitch in _pitches(pc):
            options.append((pitch, label))
    if not options:
        return 36 + root, "root"
    if prev is None:
        roots = _pitches(root, 36, 47) or _pitches(root)
        return min(roots, key=lambda p: abs(p - 43)), "root"

    target = prev
    next_target = target
    if next_chord is not None:
        next_options = _pitches(next_chord.root_pc)
        if next_options:
            next_target = min(next_options, key=lambda p: abs(p - target))

    best = None
    best_score = 1e9
    for pitch, label in options:
        motion = abs(pitch - target) / 12.0
        approach = abs(pitch - next_target) / 18.0
        inversion = {"root": -0.25, "third": 0.45, "fifth": 0.35}[label]
        if final and label != "root":
            inversion += 1.2
        leap = 0.8 if abs(pitch - target) > 5 else 0.0
        low = -0.15 if pitch < 48 else 0.0
        score = motion + approach + inversion + leap + low
        if score < best_score:
            best_score, best = score, (pitch, label)
    assert best is not None
    return best


def add_passing_tones(bass_notes: list[NoteEvent], melody: Melody,
                      beats_per_bar: float) -> tuple[list[NoteEvent], int]:
    """在相邻低音之间补经过音，返回 (新列表, 经过音数量)。"""
    ordered = sorted(bass_notes, key=lambda n: n.start)
    out = list(ordered)
    added = 0
    for current, following in zip(ordered, ordered[1:]):
        gap_start = current.start + current.dur
        gap = following.start - gap_start
        diff = following.pitch - current.pitch
        if gap < 0.45 or abs(diff) not in (1, 2):
            continue
        step = 1 if diff > 0 else -1
        pitch = following.pitch - step
        start = following.start - 0.5
        if start < gap_start - 1e-6:
            continue
        if any(abs(note.start - start) < 1e-6 for note in out):
            continue
        if _clashes(pitch, start, start + 0.4, melody):
            continue
        out.append(NoteEvent(pitch, start, 0.4, 58))
        added += 1
    out.sort(key=lambda note: note.start)
    return out, added


def _clashes(pitch: int, start: float, end: float, melody: Melody) -> bool:
    for note in melody.notes:
        if note.start < end - 1e-6 and note.end > start + 1e-6:
            if abs(pitch - note.pitch) <= 1:
                return True
    return False

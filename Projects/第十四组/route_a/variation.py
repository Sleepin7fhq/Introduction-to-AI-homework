"""乐句变奏：在每句末尾加一小段填充，避免整首一个循环。

只改伴奏，不动旋律；填充用和弦音/音阶音，落在句尾最后一拍，
并避开旋律的同度/小二度。
"""

from __future__ import annotations

from .harmony import Harmonization
from .io import Melody, NoteEvent

FILL_STYLES = {"arpeggio", "alberti", "guitar", "block", "pop", "sync"}


def add_phrase_fills(notes: list[NoteEvent], melody: Melody,
                     harmony: Harmonization, phrase_bars: int = 4,
                     style: str = "block") -> list[NoteEvent]:
    if style not in FILL_STYLES or phrase_bars <= 0:
        return list(notes)
    bpb = melody.beats_per_bar
    grid = melody.grid_start
    span = phrase_bars * bpb
    total = melody.bars * bpb
    fills: list[NoteEvent] = []

    phrase = 1
    while phrase * span < total - 1e-6:
        end = grid + phrase * span
        start = end - 1.0
        slot = next((s for s in harmony.slots
                     if s.start - 1e-6 <= start < s.end - 1e-6), None)
        if slot is not None and slot.chord is not None:
            chord_pcs = sorted(slot.chord.pcs)
            base = 60
            tones = []
            for step in range(4):
                target = base + step * 2
                while target % 12 not in chord_pcs:
                    target += 1
                tones.append(target)
            for index, pitch in enumerate(tones):
                begin = start + index * 0.25
                if _clashes(pitch, begin, begin + 0.2, melody):
                    pitch += 12
                if not _clashes(pitch, begin, begin + 0.2, melody):
                    fills.append(NoteEvent(pitch, begin, 0.2, 46))
        phrase += 1
    return list(notes) + fills


def avoid_melody(notes: list[NoteEvent], melody: Melody) -> list[NoteEvent]:
    """伴奏避让旋律：同度/小二度先试八度移位，仍冲突才丢弃。"""
    out: list[NoteEvent] = []
    for note in notes:
        if not _clashes(note.pitch, note.start, note.end, melody):
            out.append(note)
            continue
        for delta in (-12, 12, -24, 24):
            pitch = note.pitch + delta
            if 24 <= pitch <= 100 and not _clashes(pitch, note.start, note.end, melody):
                out.append(NoteEvent(pitch, note.start, note.dur, note.velocity))
                break
    return out


def _clashes(pitch: int, start: float, end: float, melody: Melody) -> bool:
    for note in melody.notes:
        if note.start < end - 1e-6 and note.end > start + 1e-6:
            if abs(pitch - note.pitch) <= 1:
                return True
    return False

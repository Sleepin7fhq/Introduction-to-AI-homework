"""低音/和声骨架：从整份谱子里抽最低音线、每拍和弦与根音直方图。

旋律提取只看单声部；骨架分析看所有声部，用来补调性判定的低音/和声证据。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from music21 import chord as m21chord
from music21 import stream

from .io import NoteEvent


@dataclass
class ChordSlice:
    start: float
    end: float
    pcs: frozenset[int]
    root_pc: int
    bass_pc: int


@dataclass
class Skeleton:
    bass_notes: list[NoteEvent] = field(default_factory=list)
    chords: list[ChordSlice] = field(default_factory=list)
    root_hist: list[float] = field(default_factory=lambda: [0.0] * 12)
    bass_hist: list[float] = field(default_factory=lambda: [0.0] * 12)
    final_bass_pc: int | None = None
    final_root_pc: int | None = None
    polyphonic: bool = False

    def summary(self) -> str:
        if not self.chords:
            return "无骨架"
        roots = " ".join(
            f"{_name(ch.root_pc)}{'m' if _is_minor(ch) else ''}"
            for ch in self.chords[:8]
        )
        return f"{len(self.chords)} 个和弦：{roots}…"

    def root_at(self, time: float) -> int | None:
        for chord in self.chords:
            if chord.start - 1e-6 <= time < chord.end - 1e-6:
                return chord.root_pc
        return None


def _name(pc: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return names[pc % 12]


def _is_minor(chord: ChordSlice) -> bool:
    return (chord.root_pc + 3) % 12 in chord.pcs and (chord.root_pc + 4) % 12 not in chord.pcs


def _infer_root(pcs: set[int], bass_pc: int) -> int:
    if not pcs:
        return bass_pc
    best_root = bass_pc
    best_score = -1e9
    for root in range(12):
        major = sum(1.0 for interval in (0, 4, 7) if (root + interval) % 12 in pcs)
        minor = sum(1.0 for interval in (0, 3, 7) if (root + interval) % 12 in pcs)
        score = max(major, minor)
        if root == bass_pc:
            score += 0.35
        if (root + 7) % 12 in pcs:
            score += 0.15
        if score > best_score:
            best_score = score
            best_root = root
    return best_root


def _flat_notes(parsed: stream.Stream) -> list[tuple[float, float, int]]:
    result = []
    for element in parsed.flatten().notes:
        if element.duration.isGrace:
            continue
        start = float(element.offset)
        dur = float(element.duration.quarterLength)
        if dur <= 0:
            continue
        if isinstance(element, m21chord.Chord):
            pitches = [p.midi for p in element.pitches]
        else:
            pitches = [element.pitch.midi]
        for pitch in pitches:
            result.append((start, dur, pitch))
    return result


def extract(parsed: stream.Stream, grid: float = 1.0) -> Skeleton:
    notes = _flat_notes(parsed)
    skeleton = Skeleton()
    if not notes:
        return skeleton
    end = max(start + dur for start, dur, _ in notes)
    steps = int(end / grid) + 1

    last_bass: int | None = None
    last_chord: ChordSlice | None = None
    max_voices = 0
    for index in range(steps):
        time = index * grid
        sounding = [(pitch, dur) for start, dur, pitch in notes
                    if start <= time + 1e-6 < start + dur]
        max_voices = max(max_voices, len(sounding))
        if not sounding:
            last_bass = None
            continue
        bass = min(pitch for pitch, _ in sounding)
        pcs = frozenset(pitch % 12 for pitch, _ in sounding)
        root = _infer_root(set(pcs), bass % 12)

        if last_bass == bass and skeleton.bass_notes:
            old = skeleton.bass_notes[-1]
            skeleton.bass_notes[-1] = NoteEvent(old.pitch, old.start,
                                                old.dur + grid, old.velocity)
        else:
            skeleton.bass_notes.append(NoteEvent(bass, time, grid, 90))
        last_bass = bass

        if last_chord and last_chord.root_pc == root and last_chord.pcs == pcs:
            last_chord.end = time + grid
        else:
            chord = ChordSlice(time, time + grid, pcs, root, bass % 12)
            skeleton.chords.append(chord)
            last_chord = chord

        skeleton.bass_hist[bass % 12] += grid
        skeleton.root_hist[root] += grid

    total = sum(skeleton.root_hist) or 1.0
    skeleton.root_hist = [value / total for value in skeleton.root_hist]
    total_bass = sum(skeleton.bass_hist) or 1.0
    skeleton.bass_hist = [value / total_bass for value in skeleton.bass_hist]
    if skeleton.chords:
        skeleton.final_bass_pc = skeleton.chords[-1].bass_pc
        skeleton.final_root_pc = skeleton.chords[-1].root_pc
    skeleton.polyphonic = max_voices >= 2
    return skeleton

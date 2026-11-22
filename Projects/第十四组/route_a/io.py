"""读入旋律：MIDI / MusicXML → 统一的音符序列。

music21 负责解析与量化；这里只做三件事：
1. 选对旋律轨（不能默认第 1 轨）；
2. 量化到 16 分 / 三连音网格；
3. 把 Note / Chord 统一成单声部的 NoteEvent。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from music21 import chord as m21chord
from music21 import converter, meter, note as m21note, stream, tempo
from music21.key import KeySignature


@dataclass
class NoteEvent:
    pitch: int
    start: float
    dur: float
    velocity: int = 90

    @property
    def end(self) -> float:
        return self.start + self.dur


@dataclass
class Melody:
    notes: list[NoteEvent]
    bpm: float = 120.0
    beats_per_bar: float = 4.0
    time_sig: tuple[int, int] = (4, 4)
    pickup_beats: float = 0.0
    source: str = ""
    bass_final: int | None = None
    final_chord_pcs: frozenset[int] | None = None
    key_signature: int | None = None
    skeleton: object | None = None

    def __post_init__(self) -> None:
        self.notes.sort(key=lambda n: (n.start, n.pitch))

    @property
    def grid_start(self) -> float:
        return self.pickup_beats

    @property
    def end(self) -> float:
        return max((n.end for n in self.notes), default=0.0)

    @property
    def bars(self) -> int:
        span = self.end - self.grid_start
        return max(1, math.ceil(span / self.beats_per_bar - 1e-6))

    @property
    def lowest(self) -> int:
        return min((n.pitch for n in self.notes), default=60)

    @property
    def highest(self) -> int:
        return max((n.pitch for n in self.notes), default=72)

    def bar_of(self, beat: float) -> int:
        return int(math.floor((beat - self.grid_start) / self.beats_per_bar + 1e-9))

    def to_stream(self) -> stream.Stream:
        out = stream.Stream()
        for n in self.notes:
            out.insert(n.start, m21note.Note(n.pitch, quarterLength=max(n.dur, 0.05)))
        return out


def _element_pitch(el) -> int:
    if isinstance(el, m21chord.Chord):
        return max(p.midi for p in el.pitches)
    return el.pitch.midi


def _part_stats(part: stream.Stream) -> tuple[float, int]:
    pitches = []
    for el in part.flatten().notes:
        if el.duration.isGrace:
            continue
        pitches.append(_element_pitch(el))
    if not pitches:
        return 0.0, 0
    pitches.sort()
    return float(pitches[len(pitches) // 2]), len(pitches)


def _extract_line(part: stream.Stream) -> list[NoteEvent]:
    """从单轨（可能含和弦/多声部）里抽一条单声部旋律线。

    先按起始时间分组，再用动态规划选一条“高音优先、级进优先、长音优先”的线：
    这样钢琴谱里的大和弦、分解伴奏不会把旋律冲掉。
    """
    groups: dict[float, list[tuple[int, float, int]]] = {}
    for el in part.flatten().notes:
        if el.duration.isGrace:
            continue
        dur = float(el.duration.quarterLength)
        if dur <= 0:
            continue
        velocity = int(el.volume.velocity or 90)
        start = round(float(el.offset), 4)
        for pitch in el.pitches:
            groups.setdefault(start, []).append((pitch.midi, dur, velocity))
    if not groups:
        return []

    times = sorted(groups)
    candidates = []
    for t in times:
        notes = sorted(groups[t], key=lambda item: -item[0])[:8]
        candidates.append(notes)

    scores: list[list[float]] = []
    backs: list[list[int]] = []
    for index, cands in enumerate(candidates):
        row: list[float] = []
        back: list[int] = []
        if index == 0:
            for pitch, dur, velocity in cands:
                row.append(_local_score(pitch, dur, velocity, cands[0][0]))
                back.append(-1)
        else:
            gap = times[index] - times[index - 1]
            for pitch, dur, velocity in cands:
                best_score = -1e9
                best_prev = 0
                for prev_index, (prev_pitch, prev_dur, _vel) in enumerate(candidates[index - 1]):
                    interval = abs(pitch - prev_pitch) / 12.0
                    transition = scores[index - 1][prev_index]
                    transition -= 0.85 * interval
                    transition -= 0.08 * min(gap, 4.0)
                    transition -= 0.12 * abs(dur - prev_dur) / 2.0
                    if transition > best_score:
                        best_score = transition
                        best_prev = prev_index
                row.append(best_score + _local_score(pitch, dur, velocity, cands[0][0]))
                back.append(best_prev)
        scores.append(row)
        backs.append(back)

    last = max(range(len(scores[-1])), key=lambda i: scores[-1][i])
    chosen: list[int] = [0] * len(times)
    for index in range(len(times) - 1, -1, -1):
        chosen[index] = last
        last = backs[index][last]

    events: list[NoteEvent] = []
    for index, pick in enumerate(chosen):
        pitch, dur, velocity = candidates[index][pick]
        if dur <= 0.05:
            continue
        events.append(NoteEvent(pitch, times[index], round(dur, 4), velocity))
    return events


def _local_score(pitch: int, dur: float, velocity: int, top_pitch: int) -> float:
    score = 0.35 * ((pitch - 58) / 24.0)
    score += 0.18 * min(dur, 2.0) / 2.0
    score += 0.08 * (velocity / 127.0)
    score += 0.25 if pitch == top_pitch else 0.0
    return score


def _pick_part(parsed: stream.Stream, track: int | None) -> stream.Stream:
    parts = list(parsed.parts) if hasattr(parsed, "parts") else []
    if not parts:
        return parsed
    if track is not None:
        if track >= len(parts):
            raise ValueError(f"--track {track} 超出范围：文件只有 {len(parts)} 个 part")
        return parts[track]
    named = [p for p in parts
             if any(k in (p.partName or "").lower()
                    for k in ("melody", "lead", "vocal", "旋律"))]
    pool = named or parts
    pool = [p for p in pool if _part_stats(p)[1] > 0] or pool
    return max(pool, key=_part_stats)


def _first_time_signature(parsed: stream.Stream) -> tuple[int, int]:
    ts = parsed.recurse().getElementsByClass(meter.TimeSignature).first()
    if ts is None:
        return (4, 4)
    return (ts.numerator, ts.denominator)


def _first_tempo(parsed: stream.Stream) -> float:
    marks = list(parsed.recurse().getElementsByClass(tempo.MetronomeMark))
    if not marks:
        return 120.0
    number = marks[0].number
    return float(number) if number else 120.0


def load_melody(path: str | Path, track: int | None = None,
                quantize: bool = True) -> Melody:
    """读 MIDI / MusicXML，返回单声部旋律。

    量化到 16 分音符与三连音网格，避免 0.4999 这类浮点误差毁掉小节对齐。
    """
    path = Path(path)
    parsed = converter.parse(str(path))
    part = _pick_part(parsed, track)
    if quantize:
        part = part.quantize(quarterLengthDivisors=(4, 3), inPlace=False)

    time_sig = _first_time_signature(parsed)
    beats_per_bar = time_sig[0] * 4.0 / time_sig[1]
    bpm = _first_tempo(parsed)
    key_sig = parsed.recurse().getElementsByClass(KeySignature).first()
    key_signature = int(key_sig.sharps) if key_sig is not None else None

    skeleton = None
    try:
        from .skeleton import extract as extract_skeleton
        skeleton = extract_skeleton(parsed)
    except Exception:  # noqa: BLE001
        skeleton = None

    notes: list[NoteEvent] = _extract_line(part)
    if not notes:
        raise ValueError(f"没有从 {path.name} 里读到音符")

    notes.sort(key=lambda n: (n.start, n.pitch))
    first = notes[0].start
    pickup = beats_per_bar if beats_per_bar * 0.5 <= first < beats_per_bar - 1e-6 else 0.0

    bass_final = None
    final_pcs = None
    try:
        elements = [el for el in parsed.flatten().notes if not el.duration.isGrace]
        if elements:
            end = max(float(el.offset) + float(el.duration.quarterLength)
                      for el in elements)
            sounding = [el for el in elements
                        if float(el.offset) <= end - 1e-4 < float(el.offset)
                        + float(el.duration.quarterLength)]
            pool = sounding or elements
            bass = min(min(p.midi for p in el.pitches) for el in pool)
            bass_final = bass % 12
            final_pcs = frozenset(p.midi % 12 for el in pool for p in el.pitches)
    except Exception:  # noqa: BLE001
        bass_final = None

    return Melody(notes=notes, bpm=bpm, beats_per_bar=beats_per_bar,
                  time_sig=time_sig, pickup_beats=pickup, source=str(path),
                  bass_final=bass_final, final_chord_pcs=final_pcs,
                  key_signature=key_signature, skeleton=skeleton)


def melody_from_events(events: list[NoteEvent], bpm: float = 120.0,
                       time_sig: tuple[int, int] = (4, 4),
                       pickup_beats: float = 0.0) -> Melody:
    beats_per_bar = time_sig[0] * 4.0 / time_sig[1]
    return Melody(notes=list(events), bpm=bpm, beats_per_bar=beats_per_bar,
                  time_sig=time_sig, pickup_beats=pickup_beats, source="<memory>")


def describe_parts(path: str | Path) -> list[dict]:
    """列出文件里的 part，供 --list-parts 使用（判断该选第几轨）。"""
    parsed = converter.parse(str(path))
    parts = list(parsed.parts) if hasattr(parsed, "parts") and parsed.parts else [parsed]
    out = []
    for index, part in enumerate(parts):
        median, count = _part_stats(part)
        out.append({
            "index": index,
            "name": part.partName or "",
            "notes": count,
            "median": median,
        })
    return out

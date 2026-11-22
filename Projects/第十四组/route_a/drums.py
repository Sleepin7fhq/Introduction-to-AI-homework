"""鼓轨：按小节生成 GM 打击乐（通道 10）。

鼓点不参与和声，只跟拍号、织体和乐句走：
* pop/rock：底鼓 1、3，军鼓 2、4，八分踩镲；
* ballad：底鼓 1，军鼓 3，四分踩镲；
* bossa：底鼓 1、3，侧击 2、4，反拍踩镲；
* waltz：底鼓 1，军鼓 2、3，四分踩镲。
每 4 小节句尾加一次军鼓过门，句首加吊镲。
"""

from __future__ import annotations

from .harmony import Harmonization
from .io import Melody, NoteEvent

KICK = 36
SNARE = 38
SIDE_STICK = 37
HAT = 42
OPEN_HAT = 46
CRASH = 49

PATTERNS = ("auto", "pop", "ballad", "bossa", "waltz")


def pick_pattern(style: str, beats_per_bar: float, requested: str = "auto") -> str:
    if requested != "auto":
        return requested
    if abs(beats_per_bar - 3.0) < 1e-6:
        return "waltz"
    if style == "bossa":
        return "bossa"
    if style in ("pad", "block", "alberti", "stride"):
        return "ballad"
    return "pop"


def _bar_hits(pattern: str, beats_per_bar: float) -> list[tuple[float, int, float, int]]:
    """返回 (小节内偏移, 音高, 时值, 力度)。"""
    hits: list[tuple[float, int, float, int]] = []
    bpb = beats_per_bar

    if pattern == "waltz" or abs(bpb - 3.0) < 1e-6:
        hits += [(0.0, KICK, 0.1, 88), (1.0, SNARE, 0.1, 70), (2.0, SNARE, 0.1, 66)]
        for beat in range(int(bpb)):
            hits.append((float(beat), HAT, 0.08, 58))
        return hits

    if pattern == "bossa":
        hits += [(0.0, KICK, 0.1, 78), (2.0, KICK, 0.1, 74)]
        hits += [(1.0, SIDE_STICK, 0.1, 74), (3.0, SIDE_STICK, 0.1, 74)]
        for off in (0.5, 1.5, 2.5, 3.5):
            hits.append((off, HAT, 0.07, 56))
        return hits

    if pattern == "ballad":
        hits += [(0.0, KICK, 0.1, 78), (2.0, SNARE, 0.1, 68)]
        for beat in range(int(bpb)):
            hits.append((float(beat), HAT, 0.08, 52))
        return hits

    # pop / rock
    hits += [(0.0, KICK, 0.1, 92), (2.0, KICK, 0.1, 84)]
    hits += [(1.0, SNARE, 0.1, 86), (3.0, SNARE, 0.1, 84)]
    for i in range(int(bpb * 2)):
        off = i * 0.5
        hits.append((off, HAT, 0.07, 62 if i % 2 == 0 else 52))
    return hits


def make_drums(melody: Melody, harmony: Harmonization, pattern: str = "auto",
               style: str = "pop", intensity: float = 1.0) -> list[NoteEvent]:
    pattern = pick_pattern(style, melody.beats_per_bar, pattern)
    bpb = melody.beats_per_bar
    notes: list[NoteEvent] = []

    for bar in range(melody.bars):
        start = melody.grid_start + bar * bpb
        for offset, pitch, dur, vel in _bar_hits(pattern, bpb):
            if offset >= bpb - 1e-6:
                continue
            notes.append(NoteEvent(pitch, start + offset, dur,
                                   max(1, min(127, int(vel * intensity)))))
        # 句首吊镲
        if bar % 4 == 0:
            notes.append(NoteEvent(CRASH, start, 0.4, int(72 * intensity)))
        # 句尾过门：4/4 在最后一拍加两个十六分军鼓
        if (bar + 1) % 4 == 0 and abs(bpb - 4.0) < 1e-6:
            for off in (3.25, 3.75):
                notes.append(NoteEvent(SNARE, start + off, 0.08, int(72 * intensity)))

    return notes

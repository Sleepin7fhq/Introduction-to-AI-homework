"""声部连接与低音。

每个和弦在 48–79 之间找 3–4 个音：优先靠近上一个和弦、整体低于旋律、
间距别拉太开。低音单独在 36–52 之间找，尽量级进。
"""

from __future__ import annotations

from itertools import product

from music21 import chord as m21chord
from music21 import note as m21note

from .harmony import ChordChoice


def _candidates(chord: ChordChoice, lo: int = 48, hi: int = 79) -> list[tuple[int, ...]]:
    per_tone = [[p for p in range(lo, hi + 1) if p % 12 == pc] for pc in sorted(chord.pcs)]
    out: set[tuple[int, ...]] = set()
    for combo in product(*per_tone):
        if len(set(combo)) < len(combo):
            continue
        ordered = tuple(sorted(combo))
        if ordered[-1] - ordered[0] > 19:
            continue
        out.add(ordered)
    return sorted(out)


def _parallel_count(prev: tuple[int, ...], cur: tuple[int, ...]) -> int:
    """轻量平行五/八度计数，用于声部搜索时的惩罚项。"""
    a = sorted(prev)
    b = sorted(cur)
    if len(a) != len(b):
        return 0
    count = 0
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            before = (a[j] - a[i]) % 12
            after = (b[j] - b[i]) % 12
            if before != after or before not in (0, 7):
                continue
            move_i = b[i] - a[i]
            move_j = b[j] - a[j]
            if move_i != 0 and move_j != 0 and move_i * move_j > 0:
                count += 1
    return count


def _score(combo: tuple[int, ...], prev: tuple[int, ...] | None, center: float) -> float:
    score = 0.0
    if prev:
        score -= 0.35 * sum(min(abs(p - q) for q in prev) for p in combo)
        score -= 0.20 * abs(combo[-1] - prev[-1])
        score -= 1.80 * _parallel_count(prev, combo)
    mean = sum(combo) / len(combo)
    score -= 0.09 * abs(mean - center)
    gaps = [b - a for a, b in zip(combo, combo[1:])]
    score -= 0.40 * sum(1 for gap in gaps if gap > 7)
    return score


def voice(chord: ChordChoice, prev: tuple[int, ...] | None,
          center: float = 58.0, melody_floor: int | None = None) -> tuple[int, ...]:
    candidates = _candidates(chord)
    if melody_floor is not None and melody_floor < 70:
        filtered = [c for c in candidates if c[-1] <= melody_floor - 2]
        candidates = filtered or candidates
    return max(candidates, key=lambda c: _score(c, prev, center))


def choose_bass(chord: ChordChoice, prev: int | None) -> int:
    options = [p for p in (36 + chord.root_pc, 48 + chord.root_pc) if 36 <= p <= 52]
    if not options:
        options = [48 + chord.root_pc]
    target = prev if prev is not None else 43
    return min(options, key=lambda p: 0.4 * abs(p - target) - (1.2 if p < 48 else 0.0))


def to_m21_chord(voicing: tuple[int, ...], duration: float = 1.0) -> m21chord.Chord:
    return m21chord.Chord([m21note.Note(p, quarterLength=duration) for p in voicing])


def count_parallels(prev: tuple[int, ...], cur: tuple[int, ...]) -> tuple[int, int]:
    """用 music21 的 VoiceLeadingQuartet 检查相邻和弦之间的平行五/八度。

    只比较按音高排序后的一一对应声部；外声部一定会被覆盖。
    """
    from music21 import voiceLeading

    if not prev or not cur:
        return 0, 0
    a = sorted(prev)
    b = sorted(cur)
    pairs = list(zip(a, b))
    fifths = octaves = 0
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            n1a = m21note.Note(pairs[i][0])
            n1b = m21note.Note(pairs[i][1])
            n2a = m21note.Note(pairs[j][0])
            n2b = m21note.Note(pairs[j][1])
            quartet = voiceLeading.VoiceLeadingQuartet(n1a, n1b, n2a, n2b)
            if quartet.parallelFifth():
                fifths += 1
            if quartet.parallelOctave():
                octaves += 1
    return fifths, octaves

"""表情自动化：随旋律起伏给每条轨画 CC11 曲线。

不是整首一个音量，而是每 0.5 拍采样一次旋律能量（音数 + 音高），
不同角色用不同跟随方式：
* 和弦：跟旋律密度，强拍略抬；
* 低音：稳定托底，只做轻微乐句弧；
* 副旋律：旋律越空越出来；
* 铺底层（弦乐/人声/管风琴）：跟乐句弧，慢慢呼吸；
* 拨奏层（钢琴/吉他）：跟旋律密度，短促响应；
* 鼓：几乎不动。
"""

from __future__ import annotations

from .instruments import INSTRUMENTS
from .io import Melody
from .render import ExtraTrack

STEP = 0.5


def _energy(melody: Melody) -> list[float]:
    total = melody.bars * melody.beats_per_bar
    count = max(2, int(total / STEP) + 1)
    raw: list[float] = []
    for index in range(count):
        start = index * STEP
        active = [n for n in melody.notes
                  if n.end > start - 1e-6 and n.start < start + STEP - 1e-6]
        density = min(1.0, len(active) / (STEP * 1.5))
        height = 0.0
        if active:
            average = sum(n.pitch for n in active) / len(active)
            height = max(0.0, min(1.0, (average - 58.0) / 20.0))
        raw.append(0.65 * density + 0.35 * height)

    low, high = min(raw), max(raw)
    if high - low < 0.08:
        norm = [0.5 for _ in raw]
    else:
        norm = [(value - low) / (high - low) for value in raw]
    smooth: list[float] = []
    for index in range(len(norm)):
        window = norm[max(0, index - 2):index + 3]
        smooth.append(sum(window) / len(window))
    return smooth


def _arc(beat: float, span: float) -> float:
    import math

    return math.sin(math.pi * ((beat % span) / span))


def _shape(raw: float, depth: float) -> int:
    value = 100.0 + (raw - 100.0) * depth
    return max(20, min(127, int(round(value))))


def build(melody: Melody, extras: list[ExtraTrack], phrase_bars: int = 4,
          level: str = "light") -> dict[int, list[tuple[float, int]]]:
    if level == "off":
        return {}
    depth = 0.55 if level == "light" else 1.0
    energy = _energy(melody)
    span = max(1, phrase_bars) * melody.beats_per_bar
    total = melody.bars * melody.beats_per_bar
    beats = [i * STEP for i in range(len(energy))]

    def curve(fn) -> list[tuple[float, int]]:
        points = []
        for beat, value in zip(beats, energy):
            if beat > total + 1e-6:
                break
            points.append((beat, _shape(fn(value, beat), depth)))
        return points

    curves: dict[int, list[tuple[float, int]]] = {
        1: curve(lambda e, b: 74 + 38 * e + 6 * _arc(b, span)),
        2: curve(lambda e, b: 96 + 10 * _arc(b, span) + 3 * e),
    }

    for extra in extras:
        if extra.name == "Counter":
            curves[3] = curve(lambda e, b: 62 + 45 * (1 - e) + 8 * _arc(b, span))
        elif extra.is_drum:
            curves[9] = curve(lambda e, b: 94 + 8 * e)
        elif extra.channel in (4, 5):
            instrument = INSTRUMENTS.get(extra.instrument or "")
            if instrument is not None and instrument.sustain:
                curves[extra.channel] = curve(
                    lambda e, b: 72 + 40 * _arc(b, span) + 8 * e)
            elif instrument is not None and instrument.pluck:
                curves[extra.channel] = curve(
                    lambda e, b: 64 + 48 * e + 6 * _arc(b, span))
            else:
                curves[extra.channel] = curve(
                    lambda e, b: 75 + 35 * _arc(b, span) + 10 * e)
    return curves

"""乐器档案：决定叠层的音域、复音数、密度与发声方式。

不是“只换 GM 音色”，而是让生成规则跟着乐器走：
* 音域：每个乐器有自己的实际音域，越界自动折叠；
* 复音数：长笛/小号/贝斯是单音，弦乐/钢琴可多音；
* 发声：弦乐/管风琴/人声是持续型，吉他/钢琴是拨奏型；
* 密度：弦乐、人声自动变疏，钢琴/吉他可以更密。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    key: str
    label: str
    program: int
    low: int
    high: int
    max_notes: int = 4
    density: float = 1.0
    sustain: bool = False
    pluck: bool = False
    velocity: float = 1.0
    gain: float = 1.0


INSTRUMENTS: dict[str, Instrument] = {
    "piano": Instrument("piano", "钢琴", 0, 21, 108, 4, 1.0, gain=1.50),
    "epiano": Instrument("epiano", "电钢", 4, 28, 100, 4, 1.0, gain=1.30),
    "strings": Instrument("strings", "弦乐", 48, 48, 84, 3, 0.7, sustain=True, gain=0.95),
    "violin": Instrument("violin", "小提琴", 40, 55, 91, 1, 0.8, sustain=True),
    "cello": Instrument("cello", "大提琴", 42, 36, 72, 1, 0.7, sustain=True),
    "guitar": Instrument("guitar", "尼龙吉他", 24, 40, 84, 4, 1.0, pluck=True, gain=1.35),
    "bass": Instrument("bass", "贝斯", 32, 28, 55, 1, 0.6, pluck=True, gain=1.10),
    "flute": Instrument("flute", "长笛", 73, 60, 96, 1, 0.8, sustain=True, gain=1.25),
    "trumpet": Instrument("trumpet", "小号", 56, 55, 82, 1, 0.8, sustain=True, gain=1.05),
    "organ": Instrument("organ", "管风琴", 19, 36, 84, 4, 0.8, sustain=True),
    "choir": Instrument("choir", "人声", 52, 48, 79, 3, 0.6, sustain=True),
    "synth": Instrument("synth", "合成铺底", 89, 48, 84, 4, 0.5, sustain=True),
}

# 不指定乐器时，按织体给一个合理默认
DEFAULT_INSTRUMENT = {
    "pad": "strings", "block": "strings",
    "arpeggio": "piano", "arp16": "piano", "alberti": "piano",
    "guitar": "guitar", "scale": "piano",
    "sync": "epiano", "pop": "epiano", "stride": "piano",
    "march": "piano", "bossa": "guitar",
}


def parse_spec(spec: str, styles: tuple[str, ...]) -> tuple[str, str | None]:
    """'pad:strings' -> ('pad', 'strings')；'pad' -> ('pad', None)。"""
    style, _, instrument = spec.partition(":")
    if style not in styles:
        raise ValueError(f"未知织体: {style}")
    if instrument:
        if instrument not in INSTRUMENTS:
            raise ValueError(f"未知乐器: {instrument}")
        return style, instrument
    return style, None


def profile_for(style: str, instrument: str | None) -> Instrument:
    key = instrument or DEFAULT_INSTRUMENT.get(style, "piano")
    return INSTRUMENTS[key]

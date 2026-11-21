"""乐句力度曲线 + 微时序（humanize）。

只作用于伴奏轨，不改用户旋律：
* 力度：按乐句位置做 0.9 → 1.1 → 0.9 的弧线（句首稍收、句中渐强、句尾回落）；
* 微时序：同一时刻的音符整体前后偏移 0–12ms，避免和弦被拆散；
* 力度再加 ±1–3 的随机抖动，让重复段落不完全一样。
"""

from __future__ import annotations

import math
import random

from .io import Melody, NoteEvent


def _clamp(value: int) -> int:
    return max(1, min(127, int(round(value))))


def phrase_dynamics(notes: list[NoteEvent], melody: Melody,
                    phrase_bars: int = 4, strength: float = 0.6) -> list[NoteEvent]:
    bpb = melody.beats_per_bar
    grid = melody.grid_start
    span = max(1, phrase_bars) * bpb
    out: list[NoteEvent] = []
    for note in notes:
        bar = int(math.floor((note.start - grid) / bpb + 1e-9))
        within = ((note.start - grid) % span) / span
        arc = 0.90 + 0.20 * math.sin(math.pi * within)
        velocity = _clamp(note.velocity * (1.0 + (arc - 1.0) * strength))
        out.append(NoteEvent(note.pitch, note.start, note.dur, velocity))
    return out


def humanize(notes: list[NoteEvent], bpm: float, amount: float = 0.5,
             seed: int = 7) -> list[NoteEvent]:
    rng = random.Random(seed)
    seconds_per_beat = 60.0 / max(bpm, 1.0)
    jitter_by_start: dict[float, float] = {}
    out: list[NoteEvent] = []
    for note in notes:
        key = round(note.start, 4)
        if key not in jitter_by_start:
            jitter_by_start[key] = rng.uniform(-1.0, 1.0) * 0.012 * amount
        jitter_beats = jitter_by_start[key] / seconds_per_beat
        start = max(0.0, note.start + jitter_beats)
        velocity = _clamp(note.velocity + rng.randint(-3, 3) * amount)
        out.append(NoteEvent(note.pitch, start, note.dur, velocity))
    return out


def apply(notes: list[NoteEvent], melody: Melody, bpm: float,
          phrase_bars: int = 4, level: str = "light") -> list[NoteEvent]:
    if level == "off":
        return list(notes)
    strength = 0.5 if level == "light" else 1.0
    shaped = phrase_dynamics(notes, melody, phrase_bars=phrase_bars, strength=strength)
    return humanize(shaped, bpm, amount=strength)

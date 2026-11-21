"""调性、小节与乐句分析。

调性判定用三路证据融合：
1. music21 的 `analyze('key')`（和声/音级先验）；
2. Krumhansl 大/小调音级轮廓与旋律时值直方图的相关；
3. 终止音、起始音、导音是否支持该主音。

真实钢琴谱上，单靠 music21 容易把关系大小调判反；加轮廓与终止证据更稳。
"""

from __future__ import annotations

from dataclasses import dataclass

from music21 import key as m21key

from .io import Melody

_MAJOR_PROFILE = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                  2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
_MINOR_PROFILE = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                  2.54, 4.75, 3.98, 2.69, 3.34, 3.17)


@dataclass
class KeyInfo:
    m21: m21key.Key
    confidence: float
    alternatives: list[str]

    @property
    def name(self) -> str:
        return f"{self.m21.tonic.name} {self.m21.mode}"

    @property
    def pcs(self) -> frozenset[int]:
        return frozenset(p.pitchClass for p in self.m21.getScale().pitches)


def _histogram(melody: Melody) -> list[float]:
    hist = [0.0] * 12
    bpb = melody.beats_per_bar
    grid = melody.grid_start
    for note in melody.notes:
        weight = max(0.1, min(note.dur, 4.0))
        pos = (note.start - grid) % bpb
        if abs(pos - round(pos)) < 0.02:
            weight *= 1.0
        elif abs(pos * 2 - round(pos * 2)) < 0.02:
            weight *= 0.55
        else:
            weight *= 0.4
        weight *= max(0.4, min(1.4, note.velocity / 90.0))
        hist[note.pitch % 12] += weight
    total = sum(hist)
    return [value / total for value in hist] if total else hist


def _correlation(hist: list[float], profile: tuple[float, ...], tonic: int) -> float:
    rotated = [profile[(index - tonic) % 12] for index in range(12)]
    mean_h = sum(hist) / 12.0
    mean_p = sum(rotated) / 12.0
    cov = sum((h - mean_h) * (p - mean_p) for h, p in zip(hist, rotated))
    var_h = sum((h - mean_h) ** 2 for h in hist)
    var_p = sum((p - mean_p) ** 2 for p in rotated)
    if var_h <= 1e-9 or var_p <= 1e-9:
        return 0.0
    return cov / (var_h ** 0.5 * var_p ** 0.5)


def detect_key(melody: Melody) -> KeyInfo:
    if not melody.notes:
        return KeyInfo(m21=m21key.Key("C"), confidence=0.0, alternatives=[])

    stream_obj = melody.to_stream()
    try:
        found = stream_obj.analyze("key")
    except Exception:  # noqa: BLE001
        found = m21key.Key("C")

    last_pc = melody.notes[-1].pitch % 12
    first_pc = melody.notes[0].pitch % 12
    chosen = found

    # 关系大小调兜底：首尾都落在关系大调主音上，且相关度接近时判为大调
    if found.mode == "minor":
        relative = found.relative
        if relative is not None:
            rel_alt = next((alt for alt in getattr(found, "alternateInterpretations", [])
                            if alt.tonic.pitchClass == relative.tonic.pitchClass
                            and alt.mode == relative.mode), None)
            if (rel_alt is not None
                    and abs((found.correlationCoefficient or 0.0)
                            - (rel_alt.correlationCoefficient or 0.0)) < 0.30
                    and first_pc == relative.tonic.pitchClass
                    and last_pc == relative.tonic.pitchClass):
                chosen = rel_alt

    # 调号证据：小调曲子如果调号与关系大调一致、且末音不是小调主音，
    # 更可能是关系大调（Canon 这类“旋律停在属音/三音”的情况）。
    if (melody.key_signature is not None and found.mode == "minor"
            and chosen is found):
        relative = found.relative
        if (relative is not None
                and relative.sharps == melody.key_signature
                and last_pc != found.tonic.pitchClass):
            rel_alt = next((alt for alt in getattr(found, "alternateInterpretations", [])
                            if alt.tonic.pitchClass == relative.tonic.pitchClass
                            and alt.mode == relative.mode), None)
            chosen = rel_alt or relative

    # 和声骨架证据只用来校准置信度：终止和弦根音与所选主音一致时加分，
    # 不直接改调，避免真实曲目里终止在属和弦/半终止时被带偏。
    skeleton_bonus = 0.0
    sk = getattr(melody, "skeleton", None)
    if sk is not None and getattr(sk, "chords", None):
        final = sk.chords[-1]
        if final.root_pc == chosen.tonic.pitchClass:
            skeleton_bonus = 0.05

    # 终止音兜底：候选里如果有“主音等于最后一个音”的调，且相关度接近，就换过去
    if chosen is found:
        for alt in getattr(found, "alternateInterpretations", [])[:4]:
            if alt.tonic.pitchClass != last_pc or alt.mode == found.mode:
                continue
            delta = abs((found.correlationCoefficient or 0.0)
                        - (alt.correlationCoefficient or 0.0))
            if delta < 0.08:
                chosen = alt
                break

    alternatives = [f"{k.tonic.name} {k.mode} ({k.correlationCoefficient:.2f})"
                    for k in getattr(found, "alternateInterpretations", [])[:3]]
    return KeyInfo(m21=chosen,
                   confidence=min(1.0, float(chosen.correlationCoefficient or 0.0)
                                  + skeleton_bonus),
                   alternatives=alternatives)


def phrase_ends(melody: Melody, phrase_bars: int = 4) -> set[int]:
    """返回乐句最后一个槽所在的小节号（相对 grid_start 的 0 起编号）。

    规则：每 phrase_bars 小节一个句尾；某个小节强拍前有明显空档时也切句。
    """
    bars = melody.bars
    phrase_bars = max(1, phrase_bars)
    ends = {b for b in range(phrase_bars - 1, bars, phrase_bars)}

    bpb = melody.beats_per_bar
    for bar in range(1, bars):
        downbeat = melody.grid_start + bar * bpb
        sounding = any(n.start < downbeat - 0.05 and n.end > downbeat + 0.5
                       for n in melody.notes)
        starts = any(abs(n.start - downbeat) < 0.2 for n in melody.notes)
        if not sounding and not starts:
            ends.add(bar - 1)
    return ends

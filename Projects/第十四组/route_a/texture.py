"""织体：把和弦与低音展开成可演奏的音符。

十三种：block / alberti / arpeggio / waltz / pop / pad / bossa / stride / march / guitar
        + arp16（十六分宽琶音）/ sync（3+3+2 切分）/ scale（音阶跑动）。
waltz 只对 3/4 拍有意义，其他拍号自动退化为 block；stride 在 3/4 退化为 waltz。
"""

from __future__ import annotations

from .harmony import Slot
from .io import NoteEvent

STYLES = ("block", "alberti", "arpeggio", "waltz", "pop", "pad",
          "bossa", "stride", "march", "guitar", "arp16", "sync", "scale")

STYLE_DESC = {
    "block": "柱式和弦",
    "alberti": "阿尔贝蒂低音",
    "arpeggio": "分解和弦",
    "waltz": "圆舞曲（3/4）",
    "pop": "流行低音 + 反拍和弦",
    "pad": "长音铺底",
    "bossa": "波萨诺瓦（低音 1/3 拍 + 切分和弦）",
    "stride": "跨步钢琴（强拍低音、弱拍和弦）",
    "march": "进行曲（低音与和弦交替）",
    "guitar": "吉他指弹（低音 + 上行分解）",
    "arp16": "十六分宽琶音（跨两个八度）",
    "sync": "切分伴奏（3+3+2 重音）",
    "scale": "音阶跑动（和弦音锚定强拍）",
}


def _clamp(value: int) -> int:
    return max(1, min(127, int(value)))


def make_texture(style: str, slot: Slot, voicing: tuple[int, ...], bass: int,
                 velocity: int, beats_per_bar: float = 4.0,
                 key_pcs: frozenset[int] | None = None
                 ) -> tuple[list[NoteEvent], list[NoteEvent]]:
    """返回 (和弦轨音符, 低音轨音符)。"""
    if style not in STYLES:
        raise ValueError(f"未知织体: {style}")

    start = slot.start
    length = slot.end - slot.start
    chord_notes: list[NoteEvent] = []
    bass_notes: list[NoteEvent] = []
    v = list(voicing)

    if style == "block":
        span = max(0.10, length * 0.94)
        for pitch in v:
            chord_notes.append(NoteEvent(pitch, start, span, _clamp(velocity)))
        bass_notes.append(NoteEvent(bass, start, span, _clamp(velocity - 6)))
        return chord_notes, bass_notes

    if style == "pad":
        span = max(0.10, length * 0.99)
        for pitch in v:
            chord_notes.append(NoteEvent(pitch, start, span, _clamp(velocity - 14)))
        bass_notes.append(NoteEvent(bass, start, span, _clamp(velocity - 12)))
        return chord_notes, bass_notes

    if style == "waltz":
        # 3/4：强拍低音，二、三拍和弦；其他拍号退化为柱式
        if abs(beats_per_bar - 3.0) > 1e-6 or length < 2.5:
            return make_texture("block", slot, voicing, bass, velocity, beats_per_bar)
        bass_notes.append(NoteEvent(bass, start, 0.95, _clamp(velocity)))
        for offset, accent in ((1.0, 0), (2.0, -2)):
            for pitch in v:
                chord_notes.append(NoteEvent(pitch, start + offset, 0.85,
                                             _clamp(velocity - 10 + accent)))
        return chord_notes, bass_notes

    if style == "pop":
        # 低音每拍，和弦在反拍上短促切入
        beat = 0.0
        while beat < length - 1e-6:
            bass_notes.append(NoteEvent(bass, start + beat, 0.45, _clamp(velocity - 4)))
            beat += 1.0
        off = 0.5
        while off < length - 1e-6:
            for pitch in v:
                chord_notes.append(NoteEvent(pitch, start + off, 0.28,
                                             _clamp(velocity - 2)))
            off += 1.0
        return chord_notes, bass_notes

    if style == "bossa":
        # 低音落在 1、3 拍；和弦在每拍的后半拍切入
        beat = 0.0
        while beat < length - 1e-6:
            bass_notes.append(NoteEvent(bass, start + beat, min(0.9, length - beat),
                                        _clamp(velocity - 4)))
            beat += 2.0
        off = 0.5
        while off < length - 1e-6:
            for pitch in v:
                chord_notes.append(NoteEvent(pitch, start + off, 0.32,
                                             _clamp(velocity - 2)))
            off += 1.0
        return chord_notes, bass_notes

    if style == "stride":
        # 跨步钢琴：强拍低音（八度加倍）、弱拍和弦；3/4 退化为圆舞曲
        if abs(beats_per_bar - 3.0) < 1e-6:
            return make_texture("waltz", slot, voicing, bass, velocity, beats_per_bar)
        beat = 0
        while beat < length - 1e-6:
            if beat % 2 == 0:
                span = min(0.9, length - beat)
                bass_notes.append(NoteEvent(bass, start + beat, span, _clamp(velocity)))
                bass_notes.append(NoteEvent(min(96, bass + 12), start + beat, span,
                                            _clamp(velocity - 8)))
            else:
                for pitch in v:
                    chord_notes.append(NoteEvent(pitch, start + beat,
                                                 min(0.8, length - beat),
                                                 _clamp(velocity - 6)))
            beat += 1
        return chord_notes, bass_notes

    if style == "march":
        # 进行曲：低音-和弦交替，强拍加重，弱拍短促，末尾补一个弱起和弦
        beat = 0
        while beat < length - 1e-6:
            if beat % 2 == 0:
                bass_notes.append(NoteEvent(bass, start + beat,
                                            min(0.4, length - beat), _clamp(velocity + 4)))
            else:
                for pitch in v:
                    chord_notes.append(NoteEvent(pitch, start + beat,
                                                 min(0.3, length - beat),
                                                 _clamp(velocity + 2)))
            beat += 1
        if abs(beats_per_bar - 3.0) < 1e-6 and length >= 3:
            for pitch in v:
                chord_notes.append(NoteEvent(pitch, start + 2.0, 0.45,
                                             _clamp(velocity - 2)))
        elif length >= 3.5:
            for pitch in v:
                chord_notes.append(NoteEvent(pitch, start + 3.5, 0.18,
                                             _clamp(velocity - 6)))
        return chord_notes, bass_notes

    if style == "guitar":
        # 指弹：每两拍一次低音，其余八分音符按 低-中-高-中 循环
        step = 0.5
        count = max(1, int(round(length / step)))
        tones = [v[0], v[1] if len(v) > 1 else v[0],
                 v[-1], v[1] if len(v) > 1 else v[0]]
        ti = 0
        for i in range(count):
            at = start + i * step
            if i % 4 == 0:
                bass_notes.append(NoteEvent(bass, at, 0.9, _clamp(velocity - 6)))
            else:
                chord_notes.append(NoteEvent(tones[ti % len(tones)], at, 0.42,
                                             _clamp(velocity - 8)))
                ti += 1
        return chord_notes, bass_notes

    if style == "arp16":
        # 十六分宽琶音：低音每两拍一次，其余音在和弦音与高八度之间跑
        step = 0.25
        count = max(1, int(round(length / step)))
        tones = [v[0], v[1] if len(v) > 1 else v[0],
                 v[-1], v[1] if len(v) > 1 else v[0]]
        seq = tones + [p + 12 for p in tones]
        ti = 0
        for i in range(count):
            at = start + i * step
            if i % 8 == 0:
                bass_notes.append(NoteEvent(bass, at, 0.9, _clamp(velocity - 4)))
            else:
                pitch = seq[ti % len(seq)]
                ti += 1
                chord_notes.append(NoteEvent(pitch, at, step * 0.85,
                                             _clamp(velocity - 6 + (5 if i % 8 == 4 else 0))))
        return chord_notes, bass_notes

    if style == "sync":
        # 切分：3+3+2 重音，低音落在 1、3 拍
        if abs(beats_per_bar - 3.0) < 1e-6:
            attacks = [(0.0, 0.5, 4), (1.5, 0.4, 0)]
        else:
            attacks = [(0.0, 0.45, 4), (1.5, 0.35, 0), (3.0, 0.35, 3)]
        for at, dur, accent in attacks:
            if at >= length - 1e-6:
                continue
            for pitch in v:
                chord_notes.append(NoteEvent(pitch, start + at, dur,
                                             _clamp(velocity + accent)))
        beat = 0.0
        while beat < length - 1e-6:
            bass_notes.append(NoteEvent(bass, start + beat, min(1.0, length - beat),
                                        _clamp(velocity - 2)))
            beat += 2.0
        return chord_notes, bass_notes

    if style == "scale":
        # 音阶跑动：强拍锚在和弦音上，弱拍走调内音阶
        pcs = set(key_pcs or ())
        if not pcs:
            pcs = {p % 12 for p in v}
        pool = sorted(p for p in range(48, 73) if p % 12 in pcs)
        if len(pool) < 4:
            return make_texture("block", slot, voicing, bass, velocity, beats_per_bar)
        chord_pcs = {p % 12 for p in v}
        chord_pool = [p for p in pool if p % 12 in chord_pcs]
        anchor = min(pool, key=lambda p: abs(p - (bass + 12)))
        index = pool.index(anchor)
        step = 0.5
        count = max(1, int(round(length / step)))
        line = [pool[(index + i) % len(pool)] for i in range(count)]
        for i in range(0, count, 2):
            if chord_pool:
                line[i] = min(chord_pool, key=lambda p: abs(p - line[i]))
        for i, pitch in enumerate(line):
            at = start + i * step
            chord_notes.append(NoteEvent(pitch, at, step * 0.9,
                                         _clamp(velocity - 6 + (4 if i % 4 == 0 else 0))))
        beat = 0.0
        while beat < length - 1e-6:
            bass_notes.append(NoteEvent(bass, start + beat, min(0.9, length - beat),
                                        _clamp(velocity - 6)))
            beat += 2.0
        return chord_notes, bass_notes

    step = 0.5
    count = max(1, int(round(length / step)))

    if style == "alberti":
        pattern = [bass, v[-1], v[1] if len(v) > 2 else v[0], v[-1]]
        for i in range(count):
            pitch = pattern[i % len(pattern)]
            at = start + i * step
            target = bass_notes if pitch == bass else chord_notes
            target.append(NoteEvent(pitch, at, step * 0.92,
                                    _clamp(velocity - (4 if i % 2 else 0))))
        return chord_notes, bass_notes

    # arpeggio：低音起，和弦音上行再折回
    sequence = [bass] + v + ([v[-2]] if len(v) > 1 else [])
    for i in range(count):
        pitch = sequence[i % len(sequence)]
        at = start + i * step
        accent = 4 if i % 4 == 0 else 0
        target = bass_notes if pitch == bass else chord_notes
        target.append(NoteEvent(pitch, at, step * 0.92,
                                _clamp(velocity - 4 + accent)))
    return chord_notes, bass_notes

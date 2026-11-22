"""和声：候选和弦、槽内契合度、功能进行、Viterbi、转调。

和弦构成与罗马数字全部交给 music21（`roman.RomanNumeral`），
这里只负责打分和搜索——也就是“编配判断”本身。

改造点（相对第一版）：
* 和弦符号正确显示七和弦（V7 → G7，ii7 → Dm7）；
* 增加副属和弦（V7/V、V7/vi、V7/ii、V7/iii…），必须解决，否则重罚；
* 提高 V7 的选中率（七音在旋律里出现时加分，终止处 V7→I 额外加分）；
* 在尾部乐句检测“属方向/下属方向”的转调，并把这一段交给新调重新配和声。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from music21 import key as m21key
from music21 import pitch as m21pitch
from music21 import roman

from .analysis import KeyInfo, phrase_ends
from .io import Melody, NoteEvent

_MAJOR_FIGURES = (
    ("I", 1, "T"), ("ii", 2, "S"), ("iii", 3, "T"), ("IV", 4, "S"),
    ("V", 5, "D"), ("V7", 5, "D"), ("vi", 6, "T"), ("viio", 7, "D"),
)
_MINOR_FIGURES = (
    ("i", 1, "T"), ("iio", 2, "S"), ("III", 3, "T"), ("iv", 4, "S"),
    ("V", 5, "D"), ("V7", 5, "D"), ("VI", 6, "T"), ("VII", 7, "D"), ("viio", 7, "D"),
)

# 副属：(罗马数字, 目标级数)
_MAJOR_SECONDARY = (
    ("V7/V", 5), ("V7/vi", 6), ("V7/ii", 2), ("V7/iii", 3),
)
_MINOR_SECONDARY = (
    ("V7/iv", 4), ("V7/VI", 6), ("V7/V", 5),
)

_SUFFIX = {
    "major": "", "minor": "m", "diminished": "dim", "augmented": "+",
    "dominant-seventh": "7", "major-seventh": "maj7", "minor-seventh": "m7",
    "half-diminished": "m7b5", "diminished-seventh": "dim7",
}

_STABILITY = {1: 0.40, 2: 0.00, 3: -0.45, 4: 0.18, 5: 0.25, 6: 0.06, 7: -0.45}

_FUNC_SCORE = {
    ("T", "S"): 0.30, ("T", "D"): 0.35, ("T", "T"): 0.00,
    ("S", "D"): 0.45, ("S", "T"): 0.10, ("S", "S"): 0.00,
    ("D", "T"): 0.55, ("D", "D"): 0.05, ("D", "S"): -0.70,
}


@dataclass(frozen=True)
class ChordChoice:
    roman: str
    symbol: str
    root_pc: int
    pcs: frozenset[int]
    degree: int
    func: str
    seventh: bool = False
    stability: float = 0.0
    kind: str = "diatonic"          # diatonic | secondary
    target_pc: int | None = None    # 副属要解决到的根音

    @property
    def is_tonic(self) -> bool:
        return self.degree == 1 and not self.seventh and self.kind == "diatonic"

    @property
    def exotic(self) -> bool:
        return self.kind != "diatonic"


@dataclass
class Slot:
    bar: int
    index: int
    start: float
    end: float
    chord: ChordChoice | None = None

    @property
    def length(self) -> float:
        return self.end - self.start


@dataclass
class Modulation:
    target: KeyInfo
    from_bar: int

    @property
    def text(self) -> str:
        return f"第 {self.from_bar + 1} 小节起 → {self.target.name}"


@dataclass
class Harmonization:
    key: KeyInfo
    slots: list[Slot]
    chart: list[list[str]]
    stats: dict[str, float] = field(default_factory=dict)
    modulation: Modulation | None = None

    def chart_text(self) -> str:
        return " | ".join(" ".join(bar) if bar else "-" for bar in self.chart)


def _root_name(rn: roman.RomanNumeral) -> str:
    root = rn.root()
    if root is None:
        return "?"
    return root.name.replace("-", "b")


def _suffix_for(rn: roman.RomanNumeral, seventh: bool) -> str:
    """music21 的 quality 不区分七和弦，这里按 figure 补后缀。"""
    figure = (rn.figure or "").lower()
    if seventh:
        if "maj7" in figure:
            return "maj7"
        if figure.startswith("v7") or (figure.endswith("7") and rn.quality == "major"):
            return "7"
        if rn.quality == "minor":
            return "m7"
        if rn.quality == "diminished":
            return "m7b5"
    return _SUFFIX.get(rn.quality, "")


def _make_chord(figure: str, key: m21key.Key, degree: int, func: str,
                kind: str = "diatonic") -> ChordChoice | None:
    rn = roman.RomanNumeral(figure, key)
    pcs = frozenset(p.pitchClass for p in rn.pitches)
    root = rn.root()
    if root is None or len(pcs) < 2:
        return None
    seventh = len(rn.pitches) >= 4
    stability = _STABILITY[degree] - (0.04 if seventh else 0.0)
    if kind == "secondary":
        stability = -0.15
    target = (root.pitchClass + 5) % 12 if kind == "secondary" else None
    return ChordChoice(
        roman=figure,
        symbol=_root_name(rn) + _suffix_for(rn, seventh),
        root_pc=root.pitchClass,
        pcs=pcs,
        degree=degree,
        func=func,
        seventh=seventh,
        stability=stability,
        kind=kind,
        target_pc=target,
    )


_SIMPLE_MAJOR = (("I", 1, "T"), ("ii", 2, "S"), ("IV", 4, "S"),
                 ("V", 5, "D"), ("vi", 6, "T"))
_SIMPLE_MINOR = (("i", 1, "T"), ("iv", 4, "S"), ("V", 5, "D"), ("VI", 6, "T"))


def build_vocabulary(key: m21key.Key, simple: bool = False) -> list[ChordChoice]:
    if simple:
        figures = _SIMPLE_MAJOR if key.mode == "major" else _SIMPLE_MINOR
        return [c for c in (_make_chord(f, key, d, fn) for f, d, fn in figures) if c]
    figures = _MAJOR_FIGURES if key.mode == "major" else _MINOR_FIGURES
    secondary = _MAJOR_SECONDARY if key.mode == "major" else _MINOR_SECONDARY
    out: list[ChordChoice] = []
    for figure, degree, func in figures:
        chord = _make_chord(figure, key, degree, func)
        if chord:
            out.append(chord)
    for figure, target_degree in secondary:
        chord = _make_chord(figure, key, target_degree, "D", kind="secondary")
        if chord:
            out.append(chord)
    return out


def _metric_weight(start: float, grid_start: float, beats_per_bar: float) -> float:
    pos = (start - grid_start) % beats_per_bar
    nearest = round(pos)
    if abs(pos - nearest) < 0.02:
        return 1.0 if nearest % beats_per_bar == 0 else 0.75
    if abs(pos * 2 - round(pos * 2)) < 0.02:
        return 0.40
    return 0.25


def _emission(chord: ChordChoice, hits: list[tuple[NoteEvent, float]],
              key_pcs: frozenset[int], beats_per_bar: float,
              grid_start: float) -> float:
    total = 0.0
    score = 0.0
    first: NoteEvent | None = None
    melody_pcs = {note.pitch % 12 for note, _ in hits}
    for note, overlap in hits:
        if first is None or note.start < first.start:
            first = note
        weight = overlap * _metric_weight(note.start, grid_start, beats_per_bar)
        total += weight
        pc = note.pitch % 12
        if pc in chord.pcs:
            value = 1.0 + (0.12 if pc == chord.root_pc else 0.0)
        elif pc in key_pcs:
            value = -0.5
        else:
            value = -1.2
        if any((pc - tone) % 12 in (1, 11) for tone in chord.pcs):
            value -= 0.4
        score += value * weight

    base = (score / total) if total > 0 else 0.0
    base += 0.25 * chord.stability
    if first is not None and first.pitch % 12 == chord.root_pc:
        base += 0.20 * _metric_weight(first.start, grid_start, beats_per_bar)

    if chord.kind == "secondary":
        base -= 0.18
        # 副属的三音就是目标调的导音；旋律里出现它，才值得用副属
        if (chord.root_pc + 4) % 12 in melody_pcs:
            base += 0.24
    # V7：旋律里出现七音时明显更合适；整体也给一点倾向，避免永远选三和弦
    if chord.roman == "V7":
        base += 0.10
        if (chord.root_pc + 10) % 12 in melody_pcs:
            base += 0.15
    return base


def _transition(prev: ChordChoice, cur: ChordChoice, *, phrase_end: bool,
                phrase_start: bool, cadence_support: bool) -> float:
    score = 0.0
    if prev.roman == cur.roman:
        score -= 0.15
    else:
        score -= 0.12

    motion = (cur.root_pc - prev.root_pc) % 12
    if motion == 5:
        score += 0.35
    elif motion == 7:
        score += 0.30
    elif motion in (2, 10):
        score += 0.18
    elif motion in (3, 9):
        score += 0.08
    elif motion == 6:
        score -= 0.30

    score += _FUNC_SCORE.get((prev.func, cur.func), 0.0)

    # 副属必须解决到目标，否则重罚
    if prev.kind == "secondary":
        score += 0.85 if cur.root_pc == prev.target_pc else -0.85

    if phrase_start:
        if cur.degree in (1, 4, 5, 6):
            score += 0.30
        elif cur.degree in (3, 7):
            score -= 0.40
        if cur.kind == "secondary":
            score -= 0.25

    if phrase_end:
        if not cadence_support:
            score -= 0.90
            return score
        if cur.degree == 1:
            if prev.roman == "V7":
                score += 2.80        # 正格终止，V7 更强
            elif prev.roman == "V":
                score += 2.10
            elif prev.func == "D":
                score += 0.90
            elif prev.func == "S":
                score += 0.70
            else:
                score += 0.35
        elif cur.func == "D":
            score += 0.45
        else:
            score -= 0.90
    return score


def build_slots(melody: Melody, chords_per_bar: int) -> list[Slot]:
    chords_per_bar = max(1, min(4, int(chords_per_bar)))
    bpb = melody.beats_per_bar
    slot_len = bpb / chords_per_bar
    slots: list[Slot] = []
    for bar in range(melody.bars):
        for i in range(chords_per_bar):
            start = melody.grid_start + bar * bpb + i * slot_len
            slots.append(Slot(bar=bar, index=i, start=start, end=start + slot_len))
    return slots


def _hits(melody: Melody, slot: Slot) -> list[tuple[NoteEvent, float]]:
    out = []
    for note in melody.notes:
        overlap = min(note.end, slot.end) - max(note.start, slot.start)
        if overlap > 1e-6:
            out.append((note, overlap))
    return out


def harmonize(melody: Melody, key_info: KeyInfo, chords_per_bar: int = 1,
              phrase_bars: int = 4, simple: bool = False) -> Harmonization:
    if not melody.notes:
        raise ValueError("旋律为空")

    slots = build_slots(melody, chords_per_bar)
    vocab = build_vocabulary(key_info.m21, simple=simple)
    bpb = melody.beats_per_bar
    grid_start = melody.grid_start
    ends = phrase_ends(melody, phrase_bars)
    hits_per_slot = [_hits(melody, slot) for slot in slots]

    emission = [
        [_emission(chord, hits, key_info.pcs, bpb, grid_start) for chord in vocab]
        for hits in hits_per_slot
    ]

    n, v = len(slots), len(vocab)
    best = [[0.0] * v for _ in range(n)]
    back = [[-1] * v for _ in range(n)]

    for j in range(v):
        start_penalty = -0.80 if vocab[j].kind == "secondary" else 0.0
        best[0][j] = emission[0][j] + (0.80 if vocab[j].is_tonic else -0.20) + start_penalty

    for i in range(1, n):
        slot = slots[i]
        is_end = slot.bar in ends and slot.index == (chords_per_bar - 1)
        is_start = slot.index == 0 and phrase_bars > 0 and slot.bar % phrase_bars == 0
        last_pc = None
        if hits_per_slot[i]:
            last_note = max((note for note, _ in hits_per_slot[i]), key=lambda x: x.end)
            last_pc = last_note.pitch % 12
        for j in range(v):
            support = last_pc is not None and last_pc in vocab[j].pcs
            top, arg = float("-inf"), -1
            for k in range(v):
                value = best[i - 1][k] + _transition(
                    vocab[k], vocab[j], phrase_end=is_end,
                    phrase_start=is_start, cadence_support=support)
                if value > top:
                    top, arg = value, k
            best[i][j] = top + emission[i][j]
            back[i][j] = arg

    if n == 1:
        for j in range(v):
            best[0][j] += 3.0 if vocab[j].is_tonic else -2.0
    else:
        for j in range(v):
            best[n - 1][j] += 3.0 if vocab[j].is_tonic else -2.0

    last = max(range(v), key=lambda j: (best[n - 1][j], -j))
    sequence = [last]
    for i in range(n - 1, 0, -1):
        sequence.append(back[i][sequence[-1]])
    sequence.reverse()

    for slot, index in zip(slots, sequence):
        slot.chord = vocab[index]

    chart = _build_chart(melody, slots)
    stats = _stats(melody, slots, bpb, grid_start)
    return Harmonization(key=key_info, slots=slots, chart=chart, stats=stats)


def _build_chart(melody: Melody, slots: list[Slot]) -> list[list[str]]:
    chart: list[list[str]] = [[] for _ in range(melody.bars)]
    for slot in slots:
        if slot.chord is None or slot.bar >= len(chart):
            continue
        label = slot.chord.symbol
        if not chart[slot.bar] or chart[slot.bar][-1] != label:
            chart[slot.bar].append(label)
    return chart


def _stats(melody: Melody, slots: list[Slot], bpb: float,
           grid_start: float) -> dict[str, float]:
    strong = conflict = 0
    for note in melody.notes:
        slot = next((s for s in slots if s.start - 1e-6 <= note.start < s.end - 1e-6), None)
        if slot is None or slot.chord is None:
            continue
        if _metric_weight(note.start, grid_start, bpb) < 0.7:
            continue
        strong += 1
        if note.pitch % 12 not in slot.chord.pcs:
            conflict += 1

    changes = sum(1 for a, b in zip(slots, slots[1:])
                  if a.chord and b.chord and a.chord.roman != b.chord.roman)
    v7 = sum(1 for s in slots if s.chord and s.chord.roman == "V7")
    secondary = sum(1 for s in slots if s.chord and s.chord.kind == "secondary")
    return {
        "conflict_rate": (conflict / strong) if strong else 0.0,
        "strong_beats": float(strong),
        "chord_changes": float(changes),
        "v7": float(v7),
        "secondary": float(secondary),
        "slots": float(len(slots)),
    }


def _tail_melody(melody: Melody, from_bar: int) -> Melody:
    offset = melody.grid_start + from_bar * melody.beats_per_bar
    notes = [NoteEvent(n.pitch, n.start - offset, n.dur, n.velocity)
             for n in melody.notes if n.start >= offset - 1e-6]
    return Melody(notes=notes, bpm=melody.bpm, beats_per_bar=melody.beats_per_bar,
                  time_sig=melody.time_sig, pickup_beats=0.0)


def try_modulate(melody: Melody, key_info: KeyInfo, harmony: Harmonization,
                 phrase_bars: int = 4, simple: bool = False) -> Harmonization | None:
    """在尾部乐句尝试属方向/下属方向的转调。

    条件很保守：尾部音集必须完全落在新调音阶内、出现新调导音、且最后一个音是新调主音；
    还要出现当前调之外的音（否则只是同音集的关系调，不算转调）。
    """
    if melody.bars < phrase_bars * 2:
        return None

    current_pcs = key_info.pcs
    tonic_pc = key_info.m21.tonic.pitchClass
    candidates = [
        KeyInfo(m21=m21key.Key(m21pitch.Pitch((tonic_pc + 7) % 12 + 60).name, "major"),
                confidence=1.0, alternatives=[]),
        KeyInfo(m21=m21key.Key(m21pitch.Pitch((tonic_pc + 5) % 12 + 60).name, "major"),
                confidence=1.0, alternatives=[]),
    ]

    for boundary in range(phrase_bars, melody.bars - phrase_bars + 1, phrase_bars):
        offset = melody.grid_start + boundary * melody.beats_per_bar
        tail = [n for n in melody.notes if n.start >= offset - 1e-6]
        if not tail:
            continue
        tail_pcs = {n.pitch % 12 for n in tail}
        last_pc = tail[-1].pitch % 12
        if tail_pcs <= current_pcs:
            continue  # 没有新调特征音
        for candidate in candidates:
            target_pcs = candidate.pcs
            leading = (candidate.m21.tonic.pitchClass + 11) % 12
            if (tail_pcs <= target_pcs
                    and leading in tail_pcs
                    and last_pc == candidate.m21.tonic.pitchClass):
                tail_melody = _tail_melody(melody, boundary)
                tail_harmony = harmonize(tail_melody, candidate, chords_per_bar=1,
                                        phrase_bars=phrase_bars, simple=simple)
                prefix = [s for s in harmony.slots if s.bar < boundary]
                shifted = []
                for slot in tail_harmony.slots:
                    shifted.append(Slot(bar=slot.bar + boundary, index=slot.index,
                                        start=slot.start + offset,
                                        end=slot.end + offset, chord=slot.chord))
                combined = prefix + shifted
                chart = [[] for _ in range(melody.bars)]
                for slot in combined:
                    if slot.chord is None or slot.bar >= len(chart):
                        continue
                    label = slot.chord.symbol
                    if not chart[slot.bar] or chart[slot.bar][-1] != label:
                        chart[slot.bar].append(label)
                stats = _stats(melody, combined, melody.beats_per_bar, melody.grid_start)
                return Harmonization(
                    key=key_info, slots=combined, chart=chart, stats=stats,
                    modulation=Modulation(target=candidate, from_bar=boundary))
    return None

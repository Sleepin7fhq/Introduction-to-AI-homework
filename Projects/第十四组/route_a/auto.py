"""自动配置：根据旋律特征给出一整套参数。

分析维度：
* 拍号：3/4 直接走 waltz；
* 速度：慢 → pad/block，中 → arpeggio/alberti，快 → pop/sync；
* 音符密度（每拍音数）：太密就少动，太疏就加流动；
* 平均时值：长音多 → 持续织体；短音多 → 轻快织体；
* 半音化程度：低 → simple 和声，高 → rich 和声。

输出 AutoPlan，CLI 的 --auto 与界面“自动配置”共用。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .analysis import KeyInfo
from .io import Melody


@dataclass
class AutoPlan:
    style: str
    chords_per_bar: int
    phrase_bars: int
    harmony: str
    ensemble: str
    humanize: str
    balance: str
    reverb: str
    reverb_engine: str
    counter: bool
    drums: bool
    drum_pattern: str
    ir: str = "hall"
    soundfont: str = "musescore"
    layers: list[tuple[str, str | None]] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def _stats(melody: Melody, key_info: KeyInfo) -> dict[str, float]:
    notes = melody.notes
    count = max(1, len(notes))
    span = max(1.0, melody.bars * melody.beats_per_bar)
    durations = [n.dur for n in notes] or [1.0]
    chromatic = 0
    key_pcs = set(key_info.pcs)
    for note in notes:
        if note.pitch % 12 not in key_pcs:
            chromatic += 1
    return {
        "density": len(notes) / span,
        "avg_dur": sum(durations) / count,
        "short_ratio": sum(1 for d in durations if d <= 0.5) / count,
        "chromatic": chromatic / count,
        "bars": melody.bars,
        "bpm": melody.bpm,
        "bpb": melody.beats_per_bar,
    }


def suggest(melody: Melody, key_info: KeyInfo) -> AutoPlan:
    stats = _stats(melody, key_info)
    density = stats["density"]
    bpm = stats["bpm"]
    bpb = stats["bpb"]
    reasons: list[str] = []

    if abs(bpb - 3.0) < 1e-6:
        plan = AutoPlan(
            style="waltz", chords_per_bar=1, phrase_bars=4, harmony="simple",
            ensemble="strings", humanize="light", balance="orchestral",
            reverb="hall", reverb_engine="ir", counter=False,
            drums=False, drum_pattern="auto", ir="hall",
            layers=[("pad", "strings")],
        )
        reasons.append("3/4 拍，走圆舞曲织体")
        return _finish(plan, stats, reasons)

    if bpm >= 122 and density >= 1.1:
        style = "sync" if density >= 1.7 else "pop"
        plan = AutoPlan(
            style=style, chords_per_bar=2, phrase_bars=4, harmony="rich",
            ensemble="band", humanize="strong", balance="pop",
            reverb="light", reverb_engine="ir", counter=False,
            drums=True, drum_pattern="auto", ir="opera", soundfont="generaluser",
            layers=[("pad", "epiano")],
        )
        reasons.append(f"速度 {bpm:.0f} BPM、密度 {density:.2f}/拍，走流行节奏")
        return _finish(plan, stats, reasons)

    if bpm <= 70 or stats["avg_dur"] >= 1.6:
        plan = AutoPlan(
            style="pad", chords_per_bar=1, phrase_bars=4, harmony="simple",
            ensemble="strings", humanize="light", balance="orchestral",
            reverb="hall", reverb_engine="ir", counter=True,
            drums=False, drum_pattern="auto", ir="church",
            layers=[("arpeggio", "piano")],
        )
        reasons.append(f"速度慢、平均时值 {stats['avg_dur']:.2f} 拍，铺底为主")
        return _finish(plan, stats, reasons)

    if density <= 0.75:
        plan = AutoPlan(
            style="block", chords_per_bar=1, phrase_bars=4, harmony="simple",
            ensemble="strings", humanize="light", balance="orchestral",
            reverb="hall", reverb_engine="ir", counter=True,
            drums=False, drum_pattern="auto", ir="church",
            layers=[("arpeggio", "piano")],
        )
        reasons.append(f"音符较疏（{density:.2f}/拍），柱式和弦 + 钢琴流动")
        return _finish(plan, stats, reasons)

    if density >= 1.8:
        plan = AutoPlan(
            style="alberti", chords_per_bar=1, phrase_bars=4, harmony="rich",
            ensemble="piano", humanize="light", balance="orchestral",
            reverb="medium", reverb_engine="ir", counter=False,
            drums=False, drum_pattern="auto", ir="hall",
            layers=[("pad", "strings")],
        )
        reasons.append(f"音符很密（{density:.2f}/拍），阿尔贝蒂 + 弦乐铺底")
        return _finish(plan, stats, reasons)

    plan = AutoPlan(
        style="arpeggio", chords_per_bar=1, phrase_bars=4,
        harmony="simple" if stats["chromatic"] < 0.12 else "rich",
        ensemble="piano", humanize="light", balance="orchestral",
        reverb="medium", reverb_engine="ir", counter=density < 1.2,
        drums=False, drum_pattern="auto", layers=[("pad", "strings")],
    )
    reasons.append(f"中速、密度 {density:.2f}/拍，琶音 + 弦乐铺底")
    return _finish(plan, stats, reasons)


def _finish(plan: AutoPlan, stats: dict[str, float], reasons: list[str]) -> AutoPlan:
    if plan.harmony == "simple" and stats["chromatic"] >= 0.18:
        plan.harmony = "rich"
        reasons.append("半音较多，改为 rich 和声")
    plan.reasons = reasons + [
        f"半音化 {stats.get('chromatic', 0):.0%}",
        f"共 {int(stats['bars'])} 小节，短语按 4 小节",
    ]
    return plan

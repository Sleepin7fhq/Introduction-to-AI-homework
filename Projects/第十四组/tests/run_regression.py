"""10 首旋律的端到端回归：配器 → MIDI → WAV → 指标 → 报告。

运行：python tests/run_regression.py
产物：output/route_a/*.mid|wav、output/route_a/report.md、summary.json
"""

from __future__ import annotations

import json
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mido
import numpy as np
from music21 import converter

from route_a.analysis import detect_key
from route_a.cli import arrange
from route_a.io import load_melody
from route_a.render import export_midi, render_wav

DATA = ROOT / "tests" / "data"
OUT = ROOT / "output" / "route_a"
OUT.mkdir(parents=True, exist_ok=True)


def wav_stats(path: Path) -> dict[str, float]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate()
        data = np.frombuffer(handle.readframes(frames), dtype="<i2").astype(np.float32) / 32768
    return {
        "seconds": round(frames / rate, 2),
        "peak": round(float(np.max(np.abs(data))), 3),
        "rms": round(float(np.sqrt(np.mean(data ** 2))), 4),
    }


def midi_stats(path: Path) -> dict:
    mid = mido.MidiFile(str(path))
    channels = sorted({msg.channel for track in mid.tracks for msg in track
                       if not msg.is_meta and hasattr(msg, "channel")})
    programs = sorted({(msg.channel, msg.program) for track in mid.tracks for msg in track
                       if msg.type == "program_change"})
    return {"tracks": len(mid.tracks), "channels": channels, "programs": programs}


def main() -> int:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    started = time.perf_counter()

    for entry in manifest:
        stem = Path(entry["file"]).stem
        t0 = time.perf_counter()
        melody = load_melody(DATA / entry["file"])
        key_info = detect_key(melody)
        harmony, chords, bass, voicings, parallels = arrange(
            melody, key_info, style="block", chords_per_bar=1, phrase_bars=4)
        midi_path = OUT / f"{stem}.mid"
        wav_path = OUT / f"{stem}.wav"
        export_midi(melody, harmony, chords, bass, midi_path)
        render_wav(midi_path, wav_path)
        elapsed = time.perf_counter() - t0

        back = converter.parse(str(midi_path))
        restored = len(list(back.recurse().notes))
        final = harmony.slots[-1].chord
        row = {
            "file": stem,
            "expected_key": entry["key"],
            "detected_key": key_info.name,
            "key_ok": key_info.name == entry["key"],
            "time_sig": entry["time_sig"],
            "pickup": entry["pickup"],
            "bars": melody.bars,
            "notes": len(melody.notes),
            "chart": harmony.chart_text(),
            "conflict": round(harmony.stats["conflict_rate"], 3),
            "v7": int(harmony.stats.get("v7", 0)),
            "secondary": int(harmony.stats.get("secondary", 0)),
            "slots": int(harmony.stats["slots"]),
            "modulation": harmony.modulation.text if harmony.modulation else "",
            "parallels": parallels,
            "final": final.symbol if final else "-",
            "final_ok": bool(final and final.degree == 1),
            "restored_notes": restored,
            "midi": midi_stats(midi_path),
            "wav": wav_stats(wav_path),
            "seconds": round(elapsed, 2),
        }
        rows.append(row)
        print(f"{stem:22s} {row['detected_key']:10s} "
              f"conflict={row['conflict']:.0%} par={parallels} final={row['final']:3s} "
              f"V7={row['v7']} sec={row['secondary']} "
              f"{'mod=' + row['modulation'] if row['modulation'] else ''} "
              f"wav={row['wav']['seconds']:5.1f}s  {elapsed:.1f}s")
        print(f"    {row['chart']}")

    total = time.perf_counter() - started
    key_ok = sum(1 for r in rows if r["key_ok"])
    final_ok = sum(1 for r in rows if r["final_ok"])
    avg_conflict = sum(r["conflict"] for r in rows) / len(rows)
    total_slots = sum(r["slots"] for r in rows)
    v7_total = sum(r["v7"] for r in rows)
    secondary_total = sum(r["secondary"] for r in rows)
    modulation_count = sum(1 for r in rows if r["modulation"])

    # 前 10 首与改造前的样本一致，用它做严格的同口径对比
    orig = rows[:10]
    o_slots = sum(r["slots"] for r in orig)
    o_v7 = sum(r["v7"] for r in orig)
    o_sec = sum(r["secondary"] for r in orig)
    o_conflict = sum(r["conflict"] for r in orig) / len(orig)
    o_key = sum(1 for r in orig if r["key_ok"])
    o_final = sum(1 for r in orig if r["final_ok"])

    summary = {
        "count": len(rows),
        "key_accuracy": round(key_ok / len(rows), 3),
        "final_tonic_rate": round(final_ok / len(rows), 3),
        "avg_conflict": round(avg_conflict, 3),
        "total_slots": total_slots,
        "v7_rate": round(v7_total / total_slots, 3),
        "secondary_rate": round(secondary_total / total_slots, 3),
        "modulation_count": modulation_count,
        "original_10": {
            "slots": o_slots, "v7": o_v7, "v7_rate": round(o_v7 / o_slots, 3),
            "secondary": o_sec, "avg_conflict": round(o_conflict, 3),
            "key_ok": o_key, "final_ok": o_final,
        },
        "total_seconds": round(total, 2),
        "rows": rows,
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    baseline = None
    baseline_path = OUT.parent / "baseline_metrics.json"
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    lines = [
        "# 路线 A 回归报告",
        "",
        f"- 样本：{len(rows)} 首",
        f"- 调性识别正确：{key_ok}/{len(rows)}（{key_ok / len(rows):.0%}）",
        f"- 结尾落在主和弦：{final_ok}/{len(rows)}（{final_ok / len(rows):.0%}）",
        f"- 平均强拍冲突率：{avg_conflict:.1%}",
        f"- V7 使用：{v7_total}/{total_slots}（{v7_total / total_slots:.1%}）",
        f"- 副属和弦：{secondary_total}/{total_slots}（{secondary_total / total_slots:.1%}）",
        f"- 触发转调：{modulation_count} 首",
        f"- 端到端总耗时：{total:.1f} 秒（含渲染）",
        "",
    ]
    if baseline:
        base_slots = baseline.get("slots", 1)
        lines += [
            "## 与改造前对比（仅原 10 首，同口径）",
            "",
            "| 指标 | 改造前 | 改造后 | 变化 |",
            "| --- | --- | --- | --- |",
            f"| 调性识别 | {baseline.get('key_ok', 9)}/10 | {o_key}/10 | — |",
            f"| 结尾主和弦 | {baseline.get('final_ok', 10)}/10 | {o_final}/10 | — |",
            f"| V7 使用率 | {baseline.get('v7', 0)}/{base_slots}"
            f"（{baseline.get('v7', 0) / base_slots:.1%}） | "
            f"{o_v7}/{o_slots}（{o_v7 / o_slots:.1%}） | "
            f"{o_v7 / o_slots - baseline.get('v7', 0) / base_slots:+.1%} |",
            f"| 副属和弦 | 0 | {o_sec}/{o_slots}（{o_sec / o_slots:.1%}） | 新增 |",
            f"| 平均冲突率 | {baseline.get('avg_conflict', 0):.1%} | {o_conflict:.1%} | "
            f"{o_conflict - baseline.get('avg_conflict', 0):+.1%} |",
            "",
            "> 第 11 首是新增的转调演示，不参与同口径对比。",
            "",
        ]

    lines += [
        "| # | 文件 | 期望调 | 识别调 | 拍号 | 和弦谱 | 冲突率 | 平行五八 | 结尾 | V7/副属 | 转调 | WAV |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, r in enumerate(rows, 1):
        chart = r["chart"].replace(" | ", " → ")
        lines.append(
            f"| {i} | {r['file']} | {r['expected_key']} | {r['detected_key']}"
            f"{'' if r['key_ok'] else ' ✗'} | {r['time_sig']} | {chart} | "
            f"{r['conflict']:.0%} | {r['parallels']} | {r['final']} | "
            f"{r['v7']}/{r['secondary']} | {r['modulation'] or '—'} | "
            f"{r['wav']['seconds']:.1f}s / peak {r['wav']['peak']} |")
    lines += [
        "",
        "## MIDI 校验",
        "",
        "| 文件 | 轨数 | 通道 | 音色 (channel, program) | 回读音符数 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append(f"| {r['file']} | {r['midi']['tracks']} | {r['midi']['channels']} | "
                     f"{r['midi']['programs']} | {r['restored_notes']} |")
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n调性 {key_ok}/{len(rows)}，主和弦收尾 {final_ok}/{len(rows)}，"
          f"平均冲突 {avg_conflict:.1%}，V7 {v7_total}/{total_slots}，"
          f"副属 {secondary_total}，转调 {modulation_count}，总耗时 {total:.1f}s")
    print(f"报告: {OUT / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

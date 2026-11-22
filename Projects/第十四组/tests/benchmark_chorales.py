"""巴赫众赞歌基准：用女高音当旋律，看自动和声与巴赫原作的重合度。

指标：
* 调性是否正确（tonic + mode）；
* 强拍和弦音集合与巴赫纵向音集合的 Jaccard；
* 终止是否落在主和弦；
* 每首耗时。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from music21 import corpus, meter, note

from route_a.analysis import detect_key
from route_a.cli import arrange
from route_a.io import Melody, NoteEvent
from route_a.skeleton import extract as extract_skeleton


def to_melody(chorale) -> Melody:
    soprano = chorale.parts[0]
    notes = []
    for n in soprano.flatten().notes:
        if isinstance(n, note.Note):
            notes.append(NoteEvent(int(n.pitch.midi), float(n.offset),
                                   float(n.duration.quarterLength), 80))
    ts = chorale.recurse().getElementsByClass(meter.TimeSignature).first()
    bpb = float(ts.barDuration.quarterLength) if ts else 4.0
    bass_final = None
    final_pcs = None
    if len(chorale.parts) > 1:
        bass_notes = [n for n in chorale.parts[-1].flatten().notes
                      if isinstance(n, note.Note)]
        if bass_notes:
            bass_final = int(bass_notes[-1].pitch.pitchClass)
        end = max(float(n.offset) + float(n.duration.quarterLength)
                  for n in chorale.parts[0].flatten().notes)
        pcs = set()
        for part in chorale.parts:
            for n in part.flatten().notes:
                if float(n.offset) <= end - 1e-4 < float(n.offset) + float(n.duration.quarterLength):
                    pcs.update(int(p.pitchClass) for p in n.pitches)
        final_pcs = frozenset(pcs)
    return Melody(notes=notes, bpm=80, beats_per_bar=bpb,
                  time_sig=(ts.numerator, ts.denominator) if ts else (4, 4),
                  bass_final=bass_final, final_chord_pcs=final_pcs,
                  skeleton=extract_skeleton(chorale))


def vertical_pcs(chorale, offset: float) -> set[int]:
    result: set[int] = set()
    for part in chorale.parts:
        for n in part.flatten().notes:
            start = float(n.offset)
            if start <= offset + 1e-6 < start + float(n.duration.quarterLength):
                result.add(int(n.pitch.pitchClass))
    return result


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    out = ROOT / "output" / "benchmark"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    key_ok = tonic_ok = 0
    jaccards = []
    total = 0.0
    errors = 0

    for index, chorale in enumerate(corpus.chorales.Iterator(numberingSystem="bwv")):
        if index >= limit:
            break
        name = str(chorale.metadata.title or f"chorale {index}")
        t0 = time.perf_counter()
        try:
            melody = to_melody(chorale)
            info = detect_key(melody)
            truth = chorale.analyze("key")
            harmony, _, _, _, _ = arrange(melody, info, style="block", modulate=False)
            elapsed = time.perf_counter() - t0
            total += elapsed

            same_key = (info.m21.tonic.pitchClass == truth.tonic.pitchClass
                        and info.m21.mode == truth.mode)
            final = harmony.slots[-1].chord
            final_ok = bool(final and final.degree == 1)

            ours_pcs = []
            bach_pcs = []
            for slot in harmony.slots:
                if slot.chord is None:
                    continue
                bach = vertical_pcs(chorale, slot.start)
                if not bach:
                    continue
                ours_pcs.append(set(slot.chord.pcs))
                bach_pcs.append(bach)
            if ours_pcs:
                jac = sum(len(a & b) / max(1, len(a | b))
                          for a, b in zip(ours_pcs, bach_pcs)) / len(ours_pcs)
            else:
                jac = 0.0

            key_ok += int(same_key)
            tonic_ok += int(final_ok)
            jaccards.append(jac)
            rows.append((name, info.name, truth.name, jac, final_ok, elapsed))
        except Exception as exc:  # noqa: BLE001
            errors += 1
            rows.append((name, "ERROR", str(exc)[:60], 0.0, False,
                         time.perf_counter() - t0))

    count = max(1, len(rows))
    mean_jac = sum(jaccards) / max(1, len(jaccards))
    lines = [
        "# 巴赫众赞歌基准",
        "",
        f"- 样本：{len(rows)} 首（前 {limit} 首，errors={errors}）",
        f"- 调性正确：{key_ok}/{count} = {key_ok / count:.0%}",
        f"- 终止主和弦：{tonic_ok}/{count} = {tonic_ok / count:.0%}",
        f"- 和弦音集合 Jaccard：{mean_jac:.3f}",
        f"- 总耗时：{total:.1f}s，平均 {total / count:.2f}s/首",
        "",
        "| 众赞歌 | 检出调性 | 实际调性 | Jaccard | 终止主和弦 | 秒 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, detected, truth, jac, final_ok, elapsed in rows:
        lines.append(f"| {name[:28]} | {detected} | {truth} | {jac:.2f} | "
                     f"{'是' if final_ok else '否'} | {elapsed:.2f} |")
    report = out / "chorales.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:8]))
    print(f"报告: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

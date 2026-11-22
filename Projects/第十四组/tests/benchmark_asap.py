"""ASAP 真实曲目回归：用 20 首钢琴谱的 quantized score 测健壮性。

ASAP 只用于本地评估（CC BY-NC-SA 4.0），不随包分发。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from route_a.analysis import detect_key
from route_a.cli import arrange
from route_a.io import load_melody


def main() -> int:
    files = sorted((ROOT / "tools" / "asap_dataset").glob("**/midi_score.mid"))
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    files = files[:limit]
    out = ROOT / "output" / "benchmark"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    errors = 0
    total = 0.0
    confidences = []
    conflicts = []

    for path in files:
        name = str(path.relative_to(ROOT / "tools" / "asap_dataset")).replace("\\", "/")
        t0 = time.perf_counter()
        try:
            melody = load_melody(path)
            info = detect_key(melody)
            harmony, _, _, _, _ = arrange(melody, info, style="block",
                                          modulate=False)
            elapsed = time.perf_counter() - t0
            total += elapsed
            confidences.append(info.confidence)
            conflicts.append(harmony.stats.get("conflict_rate", 0.0))
            rows.append((name, info.name, f"{info.confidence:.2f}", melody.bars,
                         f"{harmony.stats.get('conflict_rate', 0):.0%}", elapsed))
        except Exception as exc:  # noqa: BLE001
            errors += 1
            rows.append((name, "ERROR", str(exc)[:50], 0, "-",
                         time.perf_counter() - t0))

    count = max(1, len(rows))
    lines = [
        "# ASAP 真实曲目回归",
        "",
        f"- 样本：{len(rows)} 首（errors={errors}）",
        f"- 平均调性置信度：{sum(confidences) / max(1, len(confidences)):.2f}",
        f"- 平均强拍冲突：{sum(conflicts) / max(1, len(conflicts)):.1%}",
        f"- 总耗时：{total:.1f}s，平均 {total / count:.2f}s/首",
        "",
        "| 曲目 | 检出调性 | 置信度 | 小节 | 冲突 | 秒 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, key, conf, bars, conflict, elapsed in rows:
        lines.append(f"| {name[:52]} | {key} | {conf} | {bars} | {conflict} | "
                     f"{elapsed:.2f} |")
    report = out / "asap.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:7]))
    print(f"报告: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

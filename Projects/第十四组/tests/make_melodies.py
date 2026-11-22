"""生成 10 首回归测试旋律（公版改编 + 原创），写成 MIDI。

覆盖：C/G/F/D 大调、a 小调、4/4 与 3/4 与 6/8、有无弱起。
运行：python tests/make_melodies.py
"""

from __future__ import annotations

import json
from pathlib import Path

from music21 import key, meter, note, stream, tempo

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "data"
OUT.mkdir(parents=True, exist_ok=True)

MELODIES = {
    "01_twinkle": dict(key="C", mode="major", ts="4/4", bpm=100, pickup=0.0, notes="""
        C4:1 C4:1 G4:1 G4:1 A4:1 A4:1 G4:2 F4:1 F4:1 E4:1 E4:1 D4:1 D4:1 C4:2
        G4:1 G4:1 F4:1 F4:1 E4:1 E4:1 D4:2 G4:1 G4:1 F4:1 F4:1 E4:1 E4:1 D4:2
        C4:1 C4:1 G4:1 G4:1 A4:1 A4:1 G4:2 F4:1 F4:1 E4:1 E4:1 D4:1 D4:1 C4:2
    """),
    "02_ode_to_joy": dict(key="C", mode="major", ts="4/4", bpm=96, pickup=0.0, notes="""
        E4:1 E4:1 F4:1 G4:1 G4:1 F4:1 E4:1 D4:1 C4:1 C4:1 D4:1 E4:1 E4:1.5 D4:0.5 D4:2
        E4:1 E4:1 F4:1 G4:1 G4:1 F4:1 E4:1 D4:1 C4:1 C4:1 D4:1 E4:1 D4:1.5 C4:0.5 C4:2
    """),
    "03_mary": dict(key="C", mode="major", ts="4/4", bpm=100, pickup=0.0, notes="""
        E4:1 D4:1 C4:1 D4:1 E4:1 E4:1 E4:2 D4:1 D4:1 D4:2 E4:1 G4:1 G4:2
        E4:1 D4:1 C4:1 D4:1 E4:1 E4:1 E4:1 E4:1 D4:1 D4:1 E4:1 D4:1 C4:4
    """),
    "04_london_bridge": dict(key="G", mode="major", ts="4/4", bpm=110, pickup=0.0, notes="""
        G4:1 A4:1 G4:1 F#4:1 E4:1 F#4:1 G4:2 D4:1 E4:1 F#4:2 E4:1 F#4:1 G4:2
        G4:1 A4:1 G4:1 F#4:1 E4:1 F#4:1 G4:1 D4:1 G4:1 E4:1 C4:2 G4:2
    """),
    "05_jingle": dict(key="C", mode="major", ts="4/4", bpm=120, pickup=0.0, notes="""
        E4:1 E4:1 E4:2 E4:1 E4:1 E4:2 E4:1 G4:1 C4:1 D4:1 E4:4
        F4:1 F4:1 F4:2 F4:1 E4:1 E4:2 E4:1 D4:1 D4:1 E4:1 D4:2 G4:2
    """),
    "06_greensleeves": dict(key="A", mode="minor", ts="6/8", bpm=90, pickup=0.0, notes="""
        A4:1 C5:1 D5:1 E5:1.5 F5:0.5 E5:1 D5:1.5 B4:0.5 G4:1 A4:1.5 B4:0.5 C5:1
        A4:1.5 A4:0.5 A4:1 G4:1.5 A4:0.5 B4:1 C5:1.5 B4:0.5 A4:1 A4:3
    """),
    "07_waltz_pickup": dict(key="F", mode="major", ts="3/4", bpm=120, pickup=2.0, notes="""
        C4:1 F4:1 A4:1 C5:1 Bb4:2 A4:1 G4:1 F4:1 E4:1 F4:3
        C4:1 A4:1 C5:1 Bb4:2 G4:1 F4:1 E4:1 D4:1 C4:3
    """),
    "08_canon": dict(key="D", mode="major", ts="4/4", bpm=80, pickup=0.0, notes="""
        F#5:1 E5:1 D5:1 C#5:1 B4:1 A4:1 B4:1 C#5:1
        D5:1 C#5:1 B4:1 A4:1 G4:1 F#4:1 G4:1 E4:1
    """),
    "09_minor_original": dict(key="A", mode="minor", ts="4/4", bpm=88, pickup=0.0, notes="""
        A4:1 C5:0.5 B4:0.5 A4:1 E4:1 F4:1 A4:0.5 G4:0.5 F4:1 E4:1
        D4:1 F4:0.5 E4:0.5 D4:1 C4:1 E4:2 E4:1 G#4:1
        A4:1 C5:0.5 B4:0.5 A4:1 E4:1 F4:1 A4:0.5 G4:0.5 F4:1 C5:1
        B4:1 G#4:1 E4:1 D4:1 C4:1 B4:0.5 A4:0.5 A4:2
    """),
    "10_gmaj_pickup": dict(key="G", mode="major", ts="4/4", bpm=100, pickup=3.0, notes="""
        D4:1 G4:1 B4:1 D5:1 G5:1 F#5:2 E5:1 D5:1 C5:1 B4:1 A4:1 G4:1
        A4:2 D4:2 G4:1 B4:1 D5:1 G5:1 F#5:2 E5:1 D5:1 C5:1 A4:1 B4:1 C5:1 G4:4
    """),
    "11_modulation_demo": dict(key="C", mode="major", ts="4/4", bpm=92, pickup=0.0, notes="""
        C4:1 E4:1 G4:1 E4:1 F4:1 A4:1 G4:1 F4:1
        E4:1 G4:1 C5:1 G4:1 D4:1 F4:1 E4:1 D4:1
        C4:1 E4:1 G4:1 C5:1 B4:1 G4:1 E4:1 D4:1
        C4:1 D4:1 E4:1 F4:1 G4:4
        G4:1 B4:1 D5:1 B4:1 C5:1 E5:1 D5:1 C5:1
        B4:1 D5:1 G5:1 D5:1 A4:1 C5:1 B4:1 A4:1
        G4:1 B4:1 D5:1 G5:1 F#5:2 D5:1 B4:1
        G4:1 A4:1 B4:1 C5:1 D5:2 G4:2
    """),
}


def main() -> None:
    manifest = []
    for name, spec in MELODIES.items():
        score = stream.Score()
        part = stream.Part()
        part.insert(0, meter.TimeSignature(spec["ts"]))
        part.insert(0, tempo.MetronomeMark(number=spec["bpm"]))
        part.insert(0, key.Key(spec["key"], spec["mode"]))
        cursor = float(spec["pickup"])
        for token in spec["notes"].split():
            pitch, dur = token.split(":")
            part.insert(cursor, note.Note(pitch, quarterLength=float(dur)))
            cursor += float(dur)
        score.insert(0, part)
        path = OUT / f"{name}.mid"
        score.write("midi", fp=str(path))

        beats_per_bar = int(spec["ts"].split("/")[0]) * 4 / int(spec["ts"].split("/")[1])
        manifest.append({
            "file": path.name,
            "key": f"{spec['key']} {spec['mode']}",
            "time_sig": spec["ts"],
            "bpm": spec["bpm"],
            "pickup": spec["pickup"],
            "bars": round((cursor - spec["pickup"]) / beats_per_bar, 3),
        })
        print(f"{path.name}: {manifest[-1]['key']}, {spec['ts']}, {cursor:.2f} beats")

    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n共 {len(manifest)} 首，写入 {OUT}")


if __name__ == "__main__":
    main()

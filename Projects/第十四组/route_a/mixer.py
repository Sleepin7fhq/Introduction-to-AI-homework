"""轨道音量平衡（mixer）。

用 MIDI CC7（channel volume）给每条轨设一个基准音量，而不是只改音符力度：
* 旋律最前，副旋律次之，和弦/铺底退后，低音托底，鼓不抢；
* 三个预设：orchestral（古典/配器）、pop（流行）、flat（全 1.0）。
"""

from __future__ import annotations

BALANCE_PRESETS = {
    "orchestral": {
        "melody": 1.00, "counter": 0.72, "chords": 0.62,
        "bass": 0.80, "layer": 0.62, "drums": 0.78,
    },
    "pop": {
        "melody": 1.00, "counter": 0.65, "chords": 0.72,
        "bass": 0.90, "layer": 0.68, "drums": 0.92,
    },
    "flat": {
        "melody": 1.00, "counter": 1.00, "chords": 1.00,
        "bass": 1.00, "layer": 1.00, "drums": 1.00,
    },
}

BALANCE_LABELS = {"orchestral": "配器", "pop": "流行", "flat": "平直"}


def volumes_for(preset: str, *, counter: bool = False, layers: int = 0,
                drums: bool = False) -> dict[int, float]:
    cfg = BALANCE_PRESETS.get(preset, BALANCE_PRESETS["orchestral"])
    volumes = {
        0: cfg["melody"],
        1: cfg["chords"],
        2: cfg["bass"],
    }
    if counter:
        volumes[3] = cfg["counter"]
    for i in range(min(layers, 2)):
        volumes[4 + i] = cfg["layer"]
    if drums:
        volumes[9] = cfg["drums"]
    return volumes

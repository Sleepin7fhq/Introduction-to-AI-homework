"""外部工具路径与默认参数。"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "tools" / "bin"

FLUIDSYNTH = Path(os.environ.get(
    "FLUIDSYNTH",
    str(BIN / "fluidsynth" / "fluidsynth-v2.6.2-win10-x64-cpp11" / "bin" / "fluidsynth.exe"),
))
SOUNDFONT = Path(os.environ.get(
    "SOUNDFONT",
    str(BIN / "soundfonts" / "fluid-soundfont-3.1" / "FluidR3_GM.sf2"),
))

SAMPLE_RATE = 44100
GAIN = 0.8

MUSESOUNDFONT = BIN / "soundfonts" / "musescore" / "MuseScore_General.sf3"
GENERALUSER = BIN / "soundfonts" / "generaluser" / "GeneralUser GS v1.471.sf2"
SOUNDFONT_ALIASES = {
    "fluid": SOUNDFONT,
    "musescore": MUSESOUNDFONT,
    "generaluser": GENERALUSER,
}

IR_DIR = BIN / "ir"
BUNDLED_IRS = {
    "hall": "Musikvereinsaal.wav",
    "opera": "Scala Milan Opera Hall.wav",
    "church": "St Nicolaes Church.wav",
}

# 三轨的 GM 音色（0 起）：钢琴 / 钢琴 / 原声贝斯
PROGRAMS = {0: 0, 1: 0, 2: 32}

# 音色组：主三轨（旋律/和弦/低音）+ 副旋律 + 叠层音色（None 表示沿用织体默认）
ENSEMBLES = {
    "piano": {"label": "钢琴", "primary": (0, 0, 32), "counter": 0, "layer": None},
    "strings": {"label": "弦乐", "primary": (40, 48, 42), "counter": 40, "layer": 48},
    "band": {"label": "小乐队", "primary": (4, 4, 33), "counter": 40, "layer": 4},
}

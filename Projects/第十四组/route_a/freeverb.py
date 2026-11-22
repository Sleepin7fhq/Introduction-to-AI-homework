"""Freeverb 脉冲响应生成器。

Freeverb 是 Jezar at Dreampoint 发布的公有领域算法，也是很多开源 DAW/插件
（LMMS、部分 LV2 插件、旧版 Ardour 插件链）混响的源头。

这里不实时跑 DSP，而是用 Freeverb 的网络离线生成一条立体声脉冲响应（IR），
再交给现有的 FFT 卷积混响使用：
* 运行时不增加延迟；
* 不需要引入 C++ 插件宿主；
* 许可证干净（公有领域），可以随包分发。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

# 44.1 kHz 下的经典 tuning
COMB_TUNING = (1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617)
ALLPASS_TUNING = (556, 441, 341, 225)
STEREO_SPREAD = 23

IR_PATH = Path(__file__).resolve().parent / "data" / "freeverb_ir.npz"


def _comb(x: np.ndarray, delay: int, feedback: float, damp: float) -> np.ndarray:
    buf = [0.0] * delay
    out = np.zeros_like(x)
    idx = 0
    store = 0.0
    for n, sample in enumerate(x):
        bufout = buf[idx]
        store = bufout * (1.0 - damp) + store * damp
        buf[idx] = sample + store * feedback
        out[n] = bufout
        idx += 1
        if idx >= delay:
            idx = 0
    return out


def _allpass(x: np.ndarray, delay: int, feedback: float = 0.5) -> np.ndarray:
    buf = [0.0] * delay
    out = np.zeros_like(x)
    idx = 0
    for n, sample in enumerate(x):
        bufout = buf[idx]
        out[n] = -sample + bufout
        buf[idx] = sample + bufout * feedback
        idx += 1
        if idx >= delay:
            idx = 0
    return out


def build_ir(sr: int = 44100, seconds: float = 2.8,
             roomsize: float = 0.84, damp: float = 0.2) -> np.ndarray:
    n = int(seconds * sr)
    impulse = np.zeros(n, dtype=np.float64)
    impulse[0] = 1.0
    scale = sr / 44100.0
    combs = [max(8, int(round(c * scale))) for c in COMB_TUNING]
    allpasses = [max(4, int(round(a * scale))) for a in ALLPASS_TUNING]

    def one_channel(spread: int) -> np.ndarray:
        merged = np.zeros(n, dtype=np.float64)
        for delay in combs:
            merged += _comb(impulse, delay + spread, roomsize, damp)
        merged /= len(combs)
        for delay in allpasses:
            merged = _allpass(merged, delay + spread)
        return merged

    left = one_channel(0)
    right = one_channel(STEREO_SPREAD)
    stereo = np.stack([left, right])
    peak = float(np.max(np.abs(stereo))) or 1.0
    return (stereo / peak).astype(np.float32)


def ensure_ir(sr: int = 44100, seconds: float = 2.8) -> np.ndarray:
    """优先读取预生成的 IR，缺失时现场生成。"""
    if IR_PATH.exists():
        with np.load(IR_PATH) as data:
            ir = data["ir"]
        if ir.shape[1] >= sr * 1.0:
            return ir.astype(np.float64)
    ir = build_ir(sr=sr, seconds=seconds)
    IR_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(IR_PATH, ir=ir)
    return ir.astype(np.float64)

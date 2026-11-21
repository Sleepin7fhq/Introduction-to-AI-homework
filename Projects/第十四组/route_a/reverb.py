"""离线混响：给渲染好的 WAV 叠加一段脉冲响应。

两种引擎：
* ``ir``       —— 合成 IR（指数衰减噪声 + 早期反射），无外部依赖；
* ``freeverb`` —— 用公有领域的 Freeverb 算法离线生成 IR 再卷积。

都用 numpy 的 FFT 做卷积，不引入 C++ 插件宿主。
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from .freeverb import ensure_ir

PRESETS = {
    "off": None,
    "light": {"mix": 0.18, "rt60": 1.0, "predelay": 0.012},
    "medium": {"mix": 0.30, "rt60": 1.8, "predelay": 0.018},
    "hall": {"mix": 0.42, "rt60": 2.8, "predelay": 0.025},
}

PRESET_LABELS = {"off": "无", "light": "轻", "medium": "中", "hall": "大厅"}


def _make_ir(sr: int, rt60: float, predelay: float, seed: int = 7) -> np.ndarray:
    length = int(max(0.4, rt60 * 1.15) * sr)
    t = np.arange(length) / sr
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal((2, length)) * np.exp(-6.9 * t / max(rt60, 0.2))

    # 短 FIR 低通，去掉高频毛刺
    kernel = np.exp(-np.arange(12) / 3.0)
    kernel /= kernel.sum()
    for ch in range(2):
        ir[ch] = np.convolve(ir[ch], kernel, mode="same")

    # 早期反射
    for delay_ms, gain in ((9, 0.55), (17, 0.35), (29, 0.22), (43, 0.14)):
        idx = int(delay_ms / 1000 * sr)
        if idx < length:
            ir[:, idx:idx + 3] += gain

    # 立体声去相关
    ir[1] = np.roll(ir[1], 37)

    # 预延迟
    pre = int(predelay * sr)
    if pre > 0:
        ir = np.concatenate([np.zeros((2, pre)), ir], axis=1)

    energy = np.sqrt(np.sum(ir ** 2, axis=1, keepdims=True))
    ir = ir / np.maximum(energy, 1e-9)
    return ir.astype(np.float64)


def _fft_convolve(x: np.ndarray, h: np.ndarray) -> np.ndarray:
    n = len(x) + len(h) - 1
    size = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(h, size), size)[:n]


def _load_ir(path: str | Path, sr: int) -> np.ndarray:
    """读取外部 WAV 脉冲响应（16/24-bit PCM），转到目标采样率并归一化。"""
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        rate = handle.getframerate()
        width = handle.getsampwidth()
        raw = handle.readframes(handle.getnframes())
    if width == 2:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif width == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        values = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        values = np.where(values >= (1 << 23), values - (1 << 24), values)
        data = values.astype(np.float64) / float(1 << 23)
    elif width == 4:
        data = np.frombuffer(raw, dtype="<i4").astype(np.float64) / float(1 << 31)
    else:
        raise ValueError("IR 只支持 16/24/32-bit PCM WAV")
    data = data.reshape(-1, channels).T
    if channels == 1:
        data = np.repeat(data, 2, axis=0)
    data = data[:2]

    if rate != sr and len(data[0]) > 1:
        count = max(2, int(round(len(data[0]) * sr / rate)))
        old = np.arange(len(data[0]))
        new = np.linspace(0, len(data[0]) - 1, count)
        data = np.stack([np.interp(new, old, ch) for ch in data])

    max_len = int(6.0 * sr)
    if data.shape[1] > max_len:
        data = data[:, :max_len]
    energy = np.sqrt(np.sum(data ** 2, axis=1, keepdims=True))
    return data / np.maximum(energy, 1e-9)


def add_reverb(wav_path: str | Path, preset: str = "medium",
               mix: float | None = None, sr: int | None = None,
               engine: str = "ir", ir_path: str | Path | None = None) -> bool:
    """就地给 WAV 加混响，返回是否处理。"""
    cfg = PRESETS.get(preset)
    if cfg is None:
        return False
    wav_path = Path(wav_path)
    with wave.open(str(wav_path), "rb") as handle:
        channels = handle.getnchannels()
        rate = handle.getframerate()
        width = handle.getsampwidth()
        raw = handle.readframes(handle.getnframes())
    if width != 2:
        return False
    rate = sr or rate

    data = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    data = data.reshape(-1, channels)
    if channels == 1:
        data = np.repeat(data, 2, axis=1)
    dry = data[:, :2].T  # (2, n)

    if ir_path is not None:
        ir = _load_ir(ir_path, rate)
    elif engine == "freeverb":
        ir = ensure_ir(sr=rate, seconds=2.8)
        limit = {"light": 1.0, "medium": 1.8, "hall": 2.8}.get(preset, 2.8)
        ir = ir[:, :int(limit * rate)]
    else:
        ir = _make_ir(rate, cfg["rt60"], cfg["predelay"])
    wet = np.empty((2, dry.shape[1] + ir.shape[1] - 1), dtype=np.float64)
    for ch in range(2):
        wet[ch] = _fft_convolve(dry[ch], ir[ch])

    wet_rms = float(np.sqrt(np.mean(wet ** 2))) or 1e-9
    dry_rms = float(np.sqrt(np.mean(dry ** 2))) or 1e-9
    wet *= (dry_rms * 1.4) / wet_rms

    wet_mix = cfg["mix"] if mix is None else max(0.0, min(1.0, mix))
    out = np.zeros_like(wet)
    out[:, :dry.shape[1]] += dry * (1.0 - wet_mix * 0.35)
    out += wet * wet_mix

    # 尾部淡出，避免咔哒
    fade = min(int(0.02 * rate), out.shape[1] // 2)
    if fade > 1:
        out[:, -fade:] *= np.linspace(1.0, 0.0, fade)

    peak = np.max(np.abs(out)) or 1.0
    out = np.clip(out * (0.9 / peak), -1.0, 1.0)
    pcm = (out.T * 32767.0).astype("<i2")

    with wave.open(str(wav_path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())
    return True

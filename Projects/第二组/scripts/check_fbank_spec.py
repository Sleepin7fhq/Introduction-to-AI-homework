#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确认 AST fbank 的 FFT 长度 / mel 滤波器维度，避免 C++ 端实现偏差。"""
import numpy as np
import torch
import torchaudio
from torchaudio.compliance import kaldi

print("torchaudio fbank default round_to_power_of_two =",
      kaldi.fbank.__defaults__[kaldi.fbank.__code__.co_varnames.index("round_to_power_of_two")])

window_size = int(16000 * 25.0 / 1000)      # 400
window_shift = int(16000 * 10.0 / 1000)      # 160
padded = 512 if 400 > 256 else 400           # next_power_of_2(400) = 512
print("window_size", window_size, "shift", window_shift, "padded", padded)

mel, _ = kaldi.get_mel_banks(128, padded, 16000.0, 20.0, 0.0, 100.0, -500.0, 1.0)
print("mel_energies shape (num_bins, num_fft_bins) =", tuple(mel.shape))
print("after pad right 1 col ->", (mel.shape[0], mel.shape[1] + 1))
print("rfft bins of padded window =", padded // 2 + 1)
print("fft_bin_width =", 16000.0 / padded)

# 端到端对照：torchaudio fbank vs numpy 手工实现（padded=512 版本）
sig = np.random.RandomState(0).randn(16000).astype(np.float32) * 0.1
ref = torchaudio.compliance.kaldi.fbank(
    torch.from_numpy(sig).unsqueeze(0), sample_frequency=16000,
    window_type="hanning", num_mel_bins=128).numpy()

# numpy 手工实现
n_fft = 512
# torch.hann_window(400, periodic=False) == 0.5 - 0.5*cos(2*pi*n/399)
win = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(400) / 399.0)).astype(np.float64)
pre = 0.97
frames = 1 + (len(sig) - 400) // 160
out = np.zeros((frames, 128))
mel_m = mel.numpy().astype(np.float64)          # (128, 256)
mel_m = np.pad(mel_m, ((0, 0), (0, 1)))         # (128, 257)
for i in range(frames):
    fr = sig[i * 160:i * 160 + 400].astype(np.float64).copy()
    fr -= fr.mean()                              # remove_dc_offset
    off = np.concatenate(([fr[0]], fr[:-1]))     # replicate pad
    fr = fr - pre * off                          # preemphasis
    fr = fr * win
    buf = np.zeros(n_fft); buf[:400] = fr
    spec = np.abs(np.fft.rfft(buf)) ** 2.0
    out[i] = np.log(np.maximum(spec @ mel_m.T, 1.192092955078125e-07))
print("manual vs torchaudio max abs diff =", float(np.max(np.abs(out - ref))))

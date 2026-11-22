# -*- coding: utf-8 -*-
"""音频客观分析：电平、动态、频段分布、瞬态密度。

用法: python scripts/analyze_audio.py <wav...>
输出表 + 可选 JSON。
"""
import array
import json
import math
import os
import struct
import sys

import numpy as np


def read_wav(path):
    data = open(path, 'rb').read()
    assert data[:4] == b'RIFF' and data[8:12] == b'WAVE', 'not wav'
    pos, fmt, pcm = 12, None, None
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack('<I', data[pos + 4:pos + 8])[0]
        if cid == b'fmt ':
            fmt = data[pos + 8:pos + 8 + size]
        elif cid == b'data':
            pcm = data[pos + 8:pos + 8 + size]
            break
        pos += 8 + size + (size & 1)
    af, ch, rate = struct.unpack('<HHI', fmt[0:8])
    bits = struct.unpack('<H', fmt[14:16])[0]
    if af == 3 and bits == 32:
        x = np.frombuffer(pcm, dtype='<f4').astype(np.float32)
    elif af == 1 and bits == 16:
        x = np.frombuffer(pcm, dtype='<i2').astype(np.float32) / 32768.0
    else:
        raise ValueError('unsupported %d/%d' % (af, bits))
    x = x.reshape(-1, ch)
    return x, rate, ch


def band_ratio(spec, freqs, lo, hi):
    m = (freqs >= lo) & (freqs < hi)
    return float(spec[m].sum() / (spec.sum() + 1e-12))


def analyze(path):
    x, rate, ch = read_wav(path)
    mono = x.mean(axis=1)
    n = len(mono)
    dur = n / rate

    peak = float(np.max(np.abs(mono)))
    rms = float(np.sqrt(np.mean(mono ** 2)))
    # 去掉首尾 50ms 的静音再算有效 RMS
    start, stop = int(0.05 * rate), max(int(0.05 * rate) + 1, n - int(0.05 * rate))
    active = mono[start:stop]
    rms_active = float(np.sqrt(np.mean(active ** 2)))

    # 频谱（取整段平均）
    win = 4096
    hop = 2048
    frames = []
    for i in range(0, max(0, n - win), hop):
        seg = mono[i:i + win] * np.hanning(win)
        frames.append(np.abs(np.fft.rfft(seg)))
    spec = np.mean(frames, axis=0) if frames else np.zeros(win // 2 + 1)
    freqs = np.fft.rfftfreq(win, 1.0 / rate)
    centroid = float((freqs * spec).sum() / (spec.sum() + 1e-12))

    bands = {
        'sub_20_80': band_ratio(spec, freqs, 20, 80),
        'bass_80_250': band_ratio(spec, freqs, 80, 250),
        'lowmid_250_600': band_ratio(spec, freqs, 250, 600),
        'mid_600_2k': band_ratio(spec, freqs, 600, 2000),
        'presence_2k_6k': band_ratio(spec, freqs, 2000, 6000),
        'air_6k_16k': band_ratio(spec, freqs, 6000, 16000),
    }

    # 瞬态密度：谱通量峰值
    flux = []
    for i in range(1, len(frames)):
        d = np.maximum(0, np.diff(np.log1p(frames[i])) - np.diff(np.log1p(frames[i - 1])))
        flux.append(float(d.sum()))
    flux = np.array(flux) if flux else np.array([0.0])
    thr = flux.mean() + 2.0 * flux.std()
    onsets = int((flux > thr).sum())
    onset_rate = onsets / max(0.001, dur)

    # 立体声宽度
    if ch == 2:
        l, r = x[:, 0], x[:, 1]
        corr = float(np.corrcoef(l, r)[0, 1]) if np.std(l) > 1e-9 and np.std(r) > 1e-9 else 1.0
    else:
        corr = 1.0

    return {
        'file': os.path.basename(path),
        'duration': round(dur, 2),
        'sample_rate': rate,
        'channels': ch,
        'peak_dbfs': round(20 * math.log10(peak + 1e-12), 2),
        'rms_dbfs': round(20 * math.log10(rms + 1e-12), 2),
        'rms_active_dbfs': round(20 * math.log10(rms_active + 1e-12), 2),
        'crest_db': round(20 * math.log10(peak / (rms + 1e-12) + 1e-12), 2),
        'spectral_centroid_hz': round(centroid),
        'bands': {k: round(v, 3) for k, v in bands.items()},
        'onset_rate_per_sec': round(onset_rate, 2),
        'stereo_corr': round(corr, 3),
    }


if __name__ == '__main__':
    files = [a for a in sys.argv[1:] if not a.startswith('--')]
    rows = [analyze(f) for f in files]
    if '--json' in sys.argv:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        hdr = '%-34s %6s %7s %7s %7s %6s %8s %8s' % (
            'file', 'dur', 'peak', 'rms', 'crest', 'cent', 'onset/s', 'width')
        print(hdr)
        print('-' * len(hdr))
        for r in rows:
            print('%-34s %6.2f %7.1f %7.1f %7.1f %6d %8.2f %8.3f' % (
                r['file'], r['duration'], r['peak_dbfs'], r['rms_dbfs'],
                r['crest_db'], r['spectral_centroid_hz'], r['onset_rate_per_sec'], r['stereo_corr']))
        print('')
        print('%-34s %7s %7s %7s %7s %7s %7s' % ('file', 'sub', 'bass', 'lowmid', 'mid', 'pres', 'air'))
        print('-' * 78)
        for r in rows:
            b = r['bands']
            print('%-34s %6.1f%% %6.1f%% %6.1f%% %6.1f%% %6.1f%% %6.1f%%' % (
                r['file'], b['sub_20_80'] * 100, b['bass_80_250'] * 100,
                b['lowmid_250_600'] * 100, b['mid_600_2k'] * 100,
                b['presence_2k_6k'] * 100, b['air_6k_16k'] * 100))

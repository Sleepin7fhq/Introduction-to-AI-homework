"""从真实 WAV 生成波形图，供 PPT 使用（不是装饰性假波形）。"""
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), 'assets')

BG = (8, 11, 16)
C1 = (94, 234, 212)   # teal
C2 = (56, 189, 248)   # sky
C3 = (167, 139, 250)  # violet


def read_wav_float32(path):
    with open(path, 'rb') as f:
        data = f.read()
    assert data[:4] == b'RIFF' and data[8:12] == b'WAVE'
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
    assert af == 3 and bits == 32, 'expect float32'
    a = np.frombuffer(pcm, dtype='<f4').astype(np.float32)
    a = a.reshape(-1, ch)
    return a, rate, ch


def lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_wave(path, out_path, width=2400, height=560, accent=C1):
    a, rate, ch = read_wav_float32(path)
    mono = a.mean(axis=1)
    dur = len(mono) / float(rate)

    img = Image.new('RGB', (width, height), BG)
    d = ImageDraw.Draw(img)

    # 背景网格
    for x in range(0, width, 120):
        d.line([(x, 0), (x, height)], fill=(18, 24, 33))
    for y in range(0, height, 70):
        d.line([(0, y), (width, y)], fill=(18, 24, 33))
    d.line([(0, height // 2), (width, height // 2)], fill=(36, 48, 62))

    # 分桶取峰值（每列一个峰）
    buckets = width * 2
    step = max(1, len(mono) // buckets)
    trimmed = mono[: buckets * step]
    peaks = np.abs(trimmed).reshape(-1, step).max(axis=1) if step > 1 else np.abs(trimmed)
    if len(peaks) > buckets:
        peaks = peaks[:buckets]
    peaks = np.clip(peaks / (peaks.max() + 1e-9), 0, 1)
    # 每两列合成一列
    if len(peaks) % 2 == 1:
        peaks = peaks[:-1]
    peaks = peaks.reshape(-1, 2).max(axis=1)

    mid = height // 2
    for i, p in enumerate(peaks):
        x = int(i * width / len(peaks))
        h = p * (height * 0.46)
        col = lerp(accent, C3, i / max(1, len(peaks)))
        d.line([(x, mid - h), (x, mid + h)], fill=col)
        # 镜像柔光
        d.line([(x + 1, mid - h), (x + 1, mid + h)], fill=lerp(col, BG, 0.55))

    # 时间刻度
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 22)
    except Exception:
        font = ImageFont.load_default()
    for s in range(0, int(dur) + 1, 2):
        x = int(s / dur * width)
        d.line([(x, height - 34), (x, height - 20)], fill=(70, 88, 106))
        d.text((x + 6, height - 34), '%ds' % s, font=font, fill=(110, 128, 146))

    img.save(out_path, quality=95)
    print('%s  %.2fs  %d Hz  %dch  peak=%.2f' % (os.path.basename(out_path), dur, rate, ch, float(peaks.max())))
    return dur


if __name__ == '__main__':
    draw_wave(os.path.join(ASSETS, 'acestep-techno-128bpm.wav'),
              os.path.join(ASSETS, 'wave-techno.png'), accent=C2)
    draw_wave(os.path.join(ASSETS, 'acestep-early8-rave-138bpm.wav'),
              os.path.join(ASSETS, 'wave-rave.png'), accent=C1)

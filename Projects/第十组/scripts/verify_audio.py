"""WAV 真伪验证：不看文件大小，直接解析 RIFF 头 + 算信号统计。

支持 16-bit PCM 与 32-bit IEEE float（ACE-Step 输出的是 float32/48kHz）。
用法: python scripts/verify_audio.py <file.wav> [more.wav ...]
"""
import array
import json
import math
import os
import struct
import sys


def parse_wav(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("not a RIFF/WAVE file")
    pos = 12
    fmt = None
    pcm = None
    while pos + 8 <= len(data):
        cid = data[pos : pos + 4]
        size = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        body = data[pos + 8 : pos + 8 + size]
        if cid == b"fmt ":
            fmt = body
        elif cid == b"data":
            pcm = body
            break
        pos += 8 + size + (size & 1)
    if fmt is None or pcm is None:
        raise ValueError("missing fmt/data chunk")
    audio_format, channels, rate = struct.unpack("<HHI", fmt[0:8])
    bits = struct.unpack("<H", fmt[14:16])[0]
    return audio_format, channels, rate, bits, pcm


def decode(fmt, bits, raw):
    if fmt == 3 and bits == 32:
        a = array.array("f")
        a.frombytes(raw[: len(raw) - (len(raw) % 4)])
        if sys.byteorder == "big":
            a.byteswap()
        return a, "float32"
    if fmt == 1 and bits == 16:
        a = array.array("h")
        a.frombytes(raw[: len(raw) - (len(raw) % 2)])
        if sys.byteorder == "big":
            a.byteswap()
        return a, "pcm16"
    if fmt == 1 and bits == 32:
        a = array.array("i")
        a.frombytes(raw[: len(raw) - (len(raw) % 4)])
        if sys.byteorder == "big":
            a.byteswap()
        return a, "pcm32"
    raise ValueError("unsupported format=%d bits=%d" % (fmt, bits))


def verify(path):
    out = {"path": path}
    try:
        fmt, ch, rate, bits, raw = parse_wav(path)
        samples, kind = decode(fmt, bits, raw)
    except Exception as e:
        out["ok"] = False
        out["error"] = "%s: %s" % (type(e).__name__, e)
        return out

    n = len(samples)
    full = 32768.0 if kind == "pcm16" else (2147483648.0 if kind == "pcm32" else 1.0)
    peak = 0.0
    sumsq = 0.0
    nonzero = 0
    dc = 0.0
    for v in samples:
        a = -v if v < 0 else v
        if a > peak:
            peak = a
        sumsq += float(v) * float(v)
        dc += v
        if a > (1000.0 / 32768.0) * full * 0.03:
            nonzero += 1

    rms = math.sqrt(sumsq / n) if n else 0.0
    out.update(
        {
            "ok": True,
            "codec": kind,
            "channels": ch,
            "sample_rate": rate,
            "frames_per_channel": n // ch if ch else 0,
            "duration_sec": round(n / float(ch) / rate, 3) if ch else 0,
            "file_bytes": os.path.getsize(path),
            "peak_dbfs": round(20 * math.log10(peak / full), 2) if peak else -999,
            "rms_dbfs": round(20 * math.log10(rms / full), 2) if rms else -999,
            "non_silent_ratio": round(nonzero / float(n), 4) if n else 0,
            "dc_offset": round(dc / float(n), 5) if n else 0,
            "has_signal": bool(peak > 0.02 and (nonzero / float(n) if n else 0) > 0.05),
        }
    )
    return out


if __name__ == "__main__":
    res = [verify(p) for p in sys.argv[1:]]
    print(json.dumps(res, indent=2, ensure_ascii=False))

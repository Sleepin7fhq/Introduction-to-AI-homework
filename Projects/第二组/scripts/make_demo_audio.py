"""make_demo_audio.py —— 生成答辩演示用的音频样例。

四种典型宿舍场景（16kHz / 16bit / 单声道 WAV）：
  1. demo_loud_talk.wav   大声喧哗：多人重叠说话 + 尖锐人声 + 强包络冲击
  2. demo_music.wav       乐器声：吉他和弦/钢琴琶音 + 鼓点
  3. demo_game_audio.wav  游戏外放：电子合成音 + 快速鼓机节奏 + 音效 blip
  4. demo_normal_talk.wav 正常交谈：低音量、平稳、单人语音

这些音频仅用于「离线推理」演示路径；内核读取它们做推理后同样立刻丢弃，
不会把文件内容外传或留存。
"""

from __future__ import annotations

import argparse
import math
import struct
import wave
from pathlib import Path

SR = 16000


def _write_wav(path: Path, samples: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for s in samples:
        v = max(-1.0, min(1.0, s))
        frames += struct.pack("<h", int(v * 32767))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))
    print(f"  写出 {path}  ({len(samples) / SR:.1f} s)")


def _rand(seed: int):
    """确定性 LCG，保证每次生成结果一致（答辩可复现）。"""
    state = seed

    def nxt() -> float:
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        return (state / 0x7FFFFFFF) * 2.0 - 1.0

    return nxt


def _voice(f0: float, dur: float, amp: float, seed: int, harsh: float = 0.0) -> list[float]:
    """合成一段类人声：基频 + 谐波 + 共振峰包络 + 噪声。"""
    n = int(dur * SR)
    rnd = _rand(seed)
    out: list[float] = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        # 音高随时间轻微起伏
        f = f0 * (1.0 + 0.05 * math.sin(2 * math.pi * 1.7 * t + seed))
        phase += 2 * math.pi * f / SR
        v = 0.0
        # 基频 + 3/5/7 次谐波（类声道共振峰）
        for k, w in ((1, 1.0), (3, 0.5), (5, 0.28), (7, 0.16)):
            v += w * math.sin(k * phase)
        # 呼吸噪声
        v += 0.08 * rnd()
        # 音量包络（音节起伏）
        env = 0.55 + 0.45 * math.sin(2 * math.pi * 3.1 * t)
        v *= env
        # harsh > 0：加入高频「尖锐喊叫」成分
        if harsh > 0:
            v += harsh * math.sin(2 * math.pi * 3200 * t) * env
        out.append(amp * v)
    return out


def _mix(base: list[float], add: list[float], at: float = 0.0) -> list[float]:
    off = int(at * SR)
    need = off + len(add)
    if len(base) < need:
        base = base + [0.0] * (need - len(base))
    for i, v in enumerate(add):
        base[off + i] += v
    return base


def gen_loud_talk(dur: float = 8.0) -> list[float]:
    """大声喧哗：3 个人同时喊 + 拍桌子式冲击 + 高强度包络。"""
    n = int(dur * SR)
    rnd = _rand(7)
    out = [0.0] * n
    # 多人大声说话叠加
    for idx, (f0, seed, amp) in enumerate(
        [(180.0, 11, 0.30), (232.0, 23, 0.26), (142.0, 37, 0.24)]
    ):
        seg = _voice(f0, dur, amp, seed, harsh=0.10 + 0.05 * idx)
        out = _mix(out, seg, 0.0)
    # 喊叫峰值（突发）
    for t0 in (1.2, 3.7, 6.1):
        out = _mix(out, _voice(300.0, 0.6, 0.35, 101 + int(t0 * 10), harsh=0.18), t0)
    # 背景人群噪声 + 拍击冲击
    for i in range(n):
        out[i] += 0.05 * rnd()
    for t0 in (2.5, 5.3):
        click = [0.5 * math.exp(-i / 300.0) * (rnd()) for i in range(2000)]
        out = _mix(out, click, t0)
    # 整体饱和
    return [math.tanh(1.5 * v) * 0.85 for v in out]


def gen_music(dur: float = 8.0) -> list[float]:
    """乐器声：吉他和弦 + 钢琴琶音 + 鼓组。"""
    n = int(dur * SR)
    rnd = _rand(99)
    out = [0.0] * n

    def pluck(freq: float, length: float, amp: float) -> list[float]:
        m = int(length * SR)
        buf = []
        for i in range(m):
            t = i / SR
            decay = math.exp(-3.2 * t)
            v = (math.sin(2 * math.pi * freq * t)
                 + 0.5 * math.sin(2 * math.pi * 2 * freq * t)
                 + 0.25 * math.sin(2 * math.pi * 3 * freq * t))
            buf.append(amp * decay * v)
        return buf

    # C 大调和弦每 2 秒一次
    chords = [(261.6, 329.6, 392.0), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6)]
    for bar in range(int(dur // 2)):
        for f in chords[bar % len(chords)]:
            out = _mix(out, pluck(f, 1.9, 0.22), bar * 2.0)
    # 分解和弦琶音
    arp = [523.3, 659.3, 784.0, 659.3]
    step = 0.25
    for i in range(int(dur / step)):
        f = arp[i % len(arp)]
        out = _mix(out, pluck(f, 0.9, 0.12), i * step)
    # 鼓：底鼓 + 军鼓 + hi-hat
    for i in range(int(dur / 0.5)):
        t0 = i * 0.5
        kick = [0.7 * math.exp(-i / 500.0) * math.sin(2 * math.pi * (60 - 30 * i / 500.0) * i / SR)
                for i in range(4000)]
        out = _mix(out, kick, t0)
        if i % 2 == 1:
            snare = [0.35 * math.exp(-i / 700.0) * rnd() for i in range(3000)]
            out = _mix(out, snare, t0)
        hat = [0.12 * math.exp(-i / 200.0) * rnd() for i in range(800)]
        out = _mix(out, hat, t0 + 0.25)
    return [math.tanh(1.2 * v) * 0.85 for v in out]


def gen_game_audio(dur: float = 8.0) -> list[float]:
    """游戏外放：电子合成 bassline + 快速鼓机 + 音效 blip。"""
    n = int(dur * SR)
    rnd = _rand(555)
    out = [0.0] * n
    # 合成 bassline（方波 + 锯齿）
    bass = [55.0, 55.0, 82.4, 73.4, 55.0, 55.0, 65.4, 49.0]
    step = 0.25
    for i in range(int(dur / step)):
        f = bass[i % len(bass)]
        m = int(step * SR)
        buf = []
        ph = 0.0
        for j in range(m):
            ph += 2 * math.pi * f / SR
            saw = 2.0 * ((ph / (2 * math.pi)) % 1.0) - 1.0
            sq = 1.0 if math.sin(ph) > 0 else -1.0
            env = math.exp(-2.5 * j / SR * 4)
            buf.append(0.30 * env * (0.6 * saw + 0.4 * sq))
        out = _mix(out, buf, i * step)
    # 鼓机 hi-hat 16 分音
    for i in range(int(dur / 0.125)):
        hat = [0.16 * math.exp(-j / 150.0) * rnd() for j in range(700)]
        out = _mix(out, hat, i * 0.125)
    # 音效 blip（技能/拾取）
    for t0 in (1.1, 3.4, 5.9, 7.2):
        blip = []
        for j in range(int(0.25 * SR)):
            t = j / SR
            f = 900 + 2600 * t * 4
            blip.append(0.25 * math.exp(-9 * t) * math.sin(2 * math.pi * f * t))
        out = _mix(out, blip, t0)
    return [math.tanh(1.1 * v) * 0.85 for v in out]


def gen_normal_talk(dur: float = 8.0) -> list[float]:
    """正常交谈：低音量、平稳、单人语音 + 轻微房间底噪。"""
    n = int(dur * SR)
    rnd = _rand(2024)
    out = [0.0] * n
    # 轮流说话的两段 + 一段停顿
    seg1 = _voice(128.0, 2.6, 0.16, 71)
    seg2 = _voice(196.0, 2.4, 0.14, 89)
    seg3 = _voice(150.0, 1.9, 0.15, 103)
    out = _mix(out, seg1, 0.2)
    out = _mix(out, seg2, 3.1)
    out = _mix(out, seg3, 5.9)
    for i in range(n):
        out[i] += 0.012 * rnd()  # 房间底噪
    return [v * 0.9 for v in out]


def main() -> None:
    ap = argparse.ArgumentParser(description="生成答辩演示音频样例")
    ap.add_argument("--out-dir", default=str(Path(__file__).resolve().parent.parent / "assets" / "audio_demo"))
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    print("生成演示音频 →", out_dir)
    _write_wav(out_dir / "demo_loud_talk.wav", gen_loud_talk())
    _write_wav(out_dir / "demo_music.wav", gen_music())
    _write_wav(out_dir / "demo_game_audio.wav", gen_game_audio())
    _write_wav(out_dir / "demo_normal_talk.wav", gen_normal_talk())
    print("完成。")


if __name__ == "__main__":
    main()

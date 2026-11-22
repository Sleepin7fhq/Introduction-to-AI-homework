"""tune_demo_audio.py —— 调参脚本：把真实素材合成为能被 AST 正确识别的四类演示音频。

思路：
  * 正常交谈 → 直接用 LibriSpeech 真实朗读片段（AST 输出 "Speech" → 归入正常交谈）
  * 大声喧哗 → 真实语音做移调 + 强削波 + 快速幅度调制，逼近 shouting / yelling 的声学特征
  * 乐器声   → 真实钢琴 / 小号 / 鼓片段（AST 输出 "Music" / "Piano" / "Drum"）
  * 游戏外放 → 方波/锯齿合成音 + 快速鼓机 + 音效 blip，逼近 video game music 的特征

脚本会逐个跑内核离线推理并打印判定，便于人工挑选效果最好的那一版。
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "assets" / "audio_demo"
SRC_DIR = DEMO_DIR / "_src"
KERNEL = REPO_ROOT / "build" / "bin" / ("dorm_noise_kernel.exe" if sys.platform == "win32" else "dorm_noise_kernel")
ONNX = REPO_ROOT / "models" / "ast_audioset.onnx"
SR = 16000


def _load(name: str) -> np.ndarray:
    p = DEMO_DIR / name
    data, sr = sf.read(str(p), always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if sr != SR:
        n = int(round(len(data) * SR / sr))
        data = np.interp(np.linspace(0, len(data) - 1, n), np.arange(len(data)), data)
    return data.astype(np.float32)


def _resample(data: np.ndarray, factor: float) -> np.ndarray:
    """线性重采样（factor > 1 表示降速/变低沉）。"""
    n = int(len(data) * factor)
    if n <= 0:
        return data
    return np.interp(np.linspace(0, len(data) - 1, n), np.arange(len(data)), data).astype(np.float32)


def _shout_like(data: np.ndarray, seed: int = 5) -> np.ndarray:
    """把正常语音加工成「大声喧哗」：
    1) 降速 0.88（降低基频、加长音节）→ 再整体升调回原区间
    2) 强削波 tanh(3x) 制造破音
    3) 60~90 Hz 幅度调制模拟「拍桌子/齐声喊」的冲击
    4) 叠加高频谐波噪声制造嘶吼质感
    """
    rng = np.random.default_rng(seed)
    slow = _resample(data, 0.9)          # 变慢 → 基频下移
    fast = _resample(slow, 1 / 1.18)      # 提回来一点
    out = np.tanh(fast * 3.2) * 0.85      # 削波破音
    t = np.arange(len(out)) / SR
    # 拍击式幅度调制
    for hz in (62.0, 88.0):
        out *= 0.62 + 0.38 * np.sign(np.sin(2 * np.pi * hz * t))
    # 嘶吼高频成分
    hiss = rng.standard_normal(len(out)).astype(np.float32)
    out += 0.16 * np.tanh(hiss * 4.0)
    return np.clip(out, -1, 1).astype(np.float32)


def _game_music_like(dur: float = 8.0, seed: int = 17) -> np.ndarray:
    """合成「游戏外放」：电子方波主旋律 + 快速鼓机 + 技能音效。"""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros(n, dtype=np.float32)

    # 8-bit 风格方波旋律（A 小调）
    notes = [440.0, 523.3, 659.3, 587.3, 440.0, 392.0, 523.3, 659.3]
    step = 0.25
    for i in range(int(dur / step)):
        f = notes[i % len(notes)]
        j0 = int(i * step * SR)
        m = int(step * SR)
        ph = np.arange(m) * f / SR
        # 25% 占空比方波 → 典型的芯片音乐音色
        sq = np.where((ph % 1.0) < 0.25, 1.0, -1.0).astype(np.float32)
        env = np.exp(-3.0 * np.arange(m) / SR)
        out[j0:j0 + m] += 0.30 * sq * env

    # 低音 bassline（锯齿）
    bass = [55.0, 55.0, 82.4, 73.4]
    for i in range(int(dur / 0.5)):
        f = bass[i % len(bass)]
        j0 = int(i * 0.5 * SR)
        m = int(0.5 * SR)
        ph = np.arange(m) * f / SR
        saw = 2.0 * ((ph % 1.0)) - 1.0
        env = np.exp(-4.0 * np.arange(m) / SR)
        out[j0:j0 + m] += 0.26 * saw.astype(np.float32) * env

    # 16 分音 hi-hat 鼓机
    for i in range(int(dur / 0.125)):
        j0 = int(i * 0.125 * SR)
        m = int(0.06 * SR)
        noise = rng.standard_normal(m).astype(np.float32)
        env = np.exp(-35.0 * np.arange(m) / SR)
        out[j0:j0 + m] += 0.20 * noise * env

    # 底鼓
    for i in range(int(dur / 0.5)):
        j0 = int(i * 0.5 * SR)
        m = int(0.18 * SR)
        tt = np.arange(m) / SR
        f = 110 * np.exp(-18 * tt)
        out[j0:j0 + m] += 0.45 * np.sin(2 * np.pi * np.cumsum(f) * tt) * np.exp(-14 * tt)

    # 技能/拾取音效 blip
    for t0 in (1.3, 3.6, 5.4, 6.9):
        j0 = int(t0 * SR)
        m = int(0.22 * SR)
        tt = np.arange(m) / SR
        f = 780 + 3400 * tt * 4
        out[j0:j0 + m] += 0.28 * np.exp(-11 * tt) * np.sin(2 * np.pi * np.cumsum(f) * tt)

    return np.clip(np.tanh(out * 1.15) * 0.9, -1, 1).astype(np.float32)


def _write(name: str, data: np.ndarray) -> Path:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    path = DEMO_DIR / name
    sf.write(str(path), data, SR, subtype="PCM_16")
    return path


def _classify(path: Path) -> dict:
    proc = subprocess.run(
        [str(KERNEL), "--offline", str(ONNX), str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    for line in reversed(proc.stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    return {"error": proc.stdout[-400:]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="只生成某一类: shout / game")
    args = ap.parse_args()

    results = {}

    if args.only in ("", "shout"):
        speech = _load("real_speech_0.wav")
        for tag, gain, mod in (("a", 1.0, 1.0), ("b", 1.35, 1.35), ("c", 1.7, 1.6)):
            loud = np.clip(_shout_like(speech) * gain, -1, 1).astype(np.float32)
            if mod != 1.0:
                t = np.arange(len(loud)) / SR
                loud = np.clip(loud * (0.6 + 0.4 * mod * np.abs(np.sin(2 * np.pi * 7 * t))), -1, 1).astype(np.float32)
            p = _write(f"cand_loud_talk_{tag}.wav", loud)
            r = _classify(p)
            results[f"loud_talk_{tag}"] = r
            segs = r.get("segments", [])
            top = segs[0] if segs else {}
            print(f"[loud_talk_{tag}] class={top.get('class_zh')} conf={top.get('confidence')} "
                  f"label={top.get('top_label_name')} p={top.get('top_label_prob')}")

    if args.only in ("", "game"):
        game = _game_music_like()
        p = _write("cand_game_audio.wav", game)
        r = _classify(p)
        results["game_audio"] = r
        segs = r.get("segments", [])
        top = segs[0] if segs else {}
        print(f"[game_audio] class={top.get('class_zh')} conf={top.get('confidence')} "
              f"label={top.get('top_label_name')} p={top.get('top_label_prob')}")

    out = DEMO_DIR / "candidates.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("结果已写入", out)


if __name__ == "__main__":
    main()

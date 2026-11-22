#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 ESC-50 parquet 中提取真实的"大声喧哗 / 人群嘈杂"音频素材。

ESC-50 类别中与本题四类相关的有：
  - screaming / crowd / children shouting  -> 大声喧哗
  - clapping / cheering                    -> 人群喧哗
  - musical instrument 类（没有）          -> 乐器声（用 librosa piano 补）

用法：
  python scripts/extract_esc50.py --parquet assets/audio_demo/_src/esc50_part0.parquet \
      --out-dir assets/audio_demo --categories screaming crowd children_shouting clapping

输出：<out-dir>/esc50_<category>_<n>.wav  (16kHz / 16bit / mono)
"""
from __future__ import annotations

import argparse
import json
import io
import os
import sys

import numpy as np

SAMPLE_RATE = 16000


def iter_rows(parquet_path: str, categories: set[str], limit_per_cat: int):
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(parquet_path)
    total = 0
    got = {c: 0 for c in categories}
    for batch in pf.iter_batches(batch_size=64):
        cols = batch.to_pydict()
        n = len(cols["filename"])
        for i in range(n):
            cat = cols.get("category", [""] * n)[i]
            if isinstance(cat, dict):  # 兼容 category 存成 struct 的情况
                cat = cat.get("category", "")
            cat = str(cat)
            if cat not in categories:
                continue
            if got.get(cat, 0) >= limit_per_cat:
                continue
            audio = cols["audio"][i]
            raw = audio.get("bytes") if isinstance(audio, dict) else None
            if raw is None:
                path = audio.get("path") if isinstance(audio, dict) else None
                if not path or not os.path.exists(path):
                    continue
                with open(path, "rb") as fh:
                    raw = fh.read()
            got[cat] += 1
            total += 1
            yield cat, raw
    sys.stderr.write(f"[esc50] 命中 {total} 条\n")


def decode_to_mono_16k(raw: bytes) -> np.ndarray:
    """解码任意音频容器 -> float32 [-1,1] 单声道 -> 重采样到 16k。"""
    import soundfile as sf

    data, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if sr != SAMPLE_RATE:
        import math

        n_out = int(round(len(mono) * SAMPLE_RATE / sr))
        if n_out <= 0:
            return np.zeros(0, dtype=np.float32)
        x_old = np.linspace(0.0, 1.0, num=len(mono), endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
        mono = np.interp(x_new, x_old, mono).astype(np.float32)
    return np.clip(mono, -1.0, 1.0)


def write_wav(path: str, mono: np.ndarray) -> None:
    import soundfile as sf

    pcm = (mono * 32767.0).astype("<i2")
    sf.write(path, pcm, SAMPLE_RATE, subtype="PCM_16")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", nargs="+", required=True)
    ap.add_argument("--out-dir", default="assets/audio_demo")
    ap.add_argument(
        "--categories",
        nargs="+",
        default=["screaming", "crowd", "children_shouting", "clapping"],
    )
    ap.add_argument("--limit-per-cat", type=int, default=3)
    args = ap.parse_args()

    cats = {c.strip() for c in args.categories}
    os.makedirs(args.out_dir, exist_ok=True)
    manifest = {}

    for pq_path in args.parquet:
        if not os.path.exists(pq_path):
            sys.stderr.write(f"[esc50] 跳过不存在文件: {pq_path}\n")
            continue
        try:
            for cat, raw in iter_rows(pq_path, cats, args.limit_per_cat):
                try:
                    mono = decode_to_mono_16k(raw)
                except Exception as exc:  # noqa: BLE001
                    sys.stderr.write(f"[esc50] 解码失败 {cat}: {exc}\n")
                    continue
                if mono.size < SAMPLE_RATE:  # 少于 1 秒不要
                    continue
                idx = manifest.get(cat, 0)
                out = os.path.join(args.out_dir, f"esc50_{cat}_{idx}.wav")
                write_wav(out, mono)
                manifest[cat] = idx + 1
                sys.stderr.write(f"[esc50] {cat} -> {out} ({mono.size / SAMPLE_RATE:.2f}s)\n")
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[esc50] 读取 {pq_path} 失败: {exc}\n")

    with open(os.path.join(args.out_dir, "esc50_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

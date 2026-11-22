#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""带断点续传与重试的下载器（用于 ESC-50 / 其它大文件）。

用法：
  python scripts/robust_download.py --out assets/audio_demo/_src/esc50_part0.parquet \
      https://hf-mirror.com/datasets/ashraq/esc50/resolve/main/data/train-00000-of-00002-2f1ab7b824ec751f.parquet
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) dorm-noise-demo/1.0"


def download(url: str, out: str, retries: int = 8) -> bool:
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    for attempt in range(1, retries + 1):
        have = os.path.getsize(out) if os.path.exists(out) else 0
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        if have:
            req.add_header("Range", f"bytes={have}-")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                total = resp.headers.get("Content-Range") or resp.headers.get("Content-Length")
                mode = "ab" if (have and resp.status == 206) else "wb"
                if mode == "wb":
                    have = 0
                sys.stderr.write(f"[dl] try{attempt} {url} have={have} total={total}\n")
                with open(out, mode) as fh:
                    while True:
                        chunk = resp.read(1 << 20)
                        if not chunk:
                            break
                        fh.write(chunk)
            size = os.path.getsize(out)
            sys.stderr.write(f"[dl] done {out} size={size}\n")
            return True
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            sys.stderr.write(f"[dl] fail try{attempt}: {exc}\n")
            time.sleep(min(30, 2 ** attempt))
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("url")
    args = ap.parse_args()
    ok = download(args.url, args.out)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

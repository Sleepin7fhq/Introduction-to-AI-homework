#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""便携单文件 exe 的 IPC 自检（用 ui/kernel_client.py 的 KernelClient，避免自写 socket 读取踩广播坑）。

用法:
    python scripts/portable_selftest.py [--exe <path>] [--port 8780]

覆盖:
    1. 启动便携 exe（自解压模型+DLL 到 %LOCALAPPDATA%\\DormNoise\\runtime）
    2. IPC 连接 / status / set_config / reset / offline_file
    3. 校验四类时长结构与中文 UTF-8
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ui"))

from kernel_client import KernelClient  # noqa: E402

DEFAULT_EXE = os.path.join(ROOT, "build", "portable", "宿舍噪音识别.exe")
SPEECH = os.path.join(ROOT, "assets", "audio_demo", "real_speech_0.wav")
CLASS_KEYS = ["loud_talk", "normal_volume", "game_audio", "normal_talk"]
CLASS_ZH = {"大声喧哗", "正常音量", "游戏外放", "正常交谈"}
DEFAULT_THRESHOLDS = [15.0, 9999.0, 45.0, 9999.0]

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {name}" + (f"  {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=DEFAULT_EXE)
    ap.add_argument("--port", type=int, default=8780)
    ap.add_argument("--no-capture", action="store_true", default=True)
    args = ap.parse_args()

    print("=" * 62)
    print("便携单文件 exe · IPC 自检")
    print("=" * 62)

    if not os.path.exists(args.exe):
        print(f"[FATAL] 便携 exe 不存在: {args.exe}")
        return 2

    print(f"\n[1/6] 启动便携 exe: {args.exe}")
    proc = subprocess.Popen(
        [args.exe, "--port", str(args.port)] + (["--no-capture"] if args.no_capture else []),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=ROOT,
    )
    time.sleep(10.0)
    if proc.poll() is not None:
        out = proc.stdout.read().decode("utf-8", "replace") if proc.stdout else ""
        print(f"[FATAL] 便携 exe 启动即退出:\n{out}")
        return 2

    client = KernelClient(port=args.port)
    try:
        print("\n[2/6] 连接 IPC ...")
        ok = client.connect(timeout=10.0)
        check("连接内核", ok, client.last_error)
        if not ok:
            return 2

        print("\n[3/6] status ...")
        resp = client.status()
        check("status 有响应", resp is not None and resp.get("type") == "state")
        time.sleep(1.2)
        st = client.state
        check("kernel_alive=True", st.kernel_alive)
        check("classes 四类及顺序正确",
              [c.get("key") or c.get("class_key") for c in st.classes] == CLASS_KEYS,
              str(st.classes))
        check("model_path 指向释放目录", "runtime" in st.model_path.replace("\\", "/").lower()
              or "DormNoise" in st.model_path, st.model_path)
        check("默认时长阈值和正常音量门限正确", st.segment_sec > 0 and st.thresholds == DEFAULT_THRESHOLDS
              and abs(st.normal_volume_dbfs - (-45.0)) < 1e-6)

        print("\n[4/6] set_config / reset ...")
        resp = client.set_config(segment_sec=3.0, thresholds=[10.0, 20.0, 30.0, 9999.0],
                                 min_confidence=0.05, auto_alert=True, normal_volume_dbfs=-50.0)
        check("set_config 返回 ok", resp is not None and resp.get("type") == "ok",
              json.dumps(resp, ensure_ascii=False) if resp else "None")
        time.sleep(1.2)
        check("正常音量门限配置已生效",
              abs(client.state.normal_volume_dbfs - (-50.0)) < 1e-6,
              str(client.state.normal_volume_dbfs))
        check("reset 返回 ok", (client.reset_stats() or {}).get("type") == "ok")

        print("\n[5/6] offline_file ...")
        if os.path.exists(SPEECH):
            resp = client.offline_file(SPEECH)
            ok = resp is not None and resp.get("type") == "offline_result"
            check("offline_result 返回", ok)
            segs = (resp or {}).get("segments") or []
            check("至少一个分段", len(segs) > 0)
            if segs:
                s0 = segs[0]
                check("含分段 RMS dBFS", isinstance(s0.get("rms_dbfs"), (int, float)),
                      str(s0.get("rms_dbfs")))
                check("真实朗读判定为正常交谈", s0.get("class_key") == "normal_talk",
                      f"{s0.get('class_key')} / {s0.get('class_zh')} conf={s0.get('confidence')}")
                check("含 top 细分标签", bool(s0.get("top_label_name")),
                      f"{s0.get('top_label_name')} {s0.get('top_label_prob')}")
        else:
            check("真实朗读测试素材存在", False, SPEECH)

        print("\n[6/6] 中文 UTF-8 校验 ...")
        raw = json.dumps(client.state.__dict__, ensure_ascii=False, default=str)
        check("中文可序列化", "喧哗" in raw)
        names = [c.get("class_zh") or c.get("zh") for c in client.state.classes]
        check("classes 含四个中文名",
              set(names) == CLASS_ZH, str(names))
    finally:
        client.disconnect()
        print("\n[清理] 关闭便携 exe ...")
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()

    print("\n" + "=" * 62)
    print(f"结果：PASS={PASS}  FAIL={FAIL}")
    print("=" * 62)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

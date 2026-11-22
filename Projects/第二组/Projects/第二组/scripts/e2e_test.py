#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""UI ↔ 内核 端到端联调测试（不依赖浏览器）。

用法：
  python scripts/e2e_test.py

覆盖：
  1. 启动内核（build/bin/dorm_noise_kernel.exe）
  2. 用 ui/kernel_client.py 连接
  3. status / set_config / reset / offline_file 全链路
  4. 校验 state JSON 的四类时长结构
  5. 校验中文 UTF-8 无乱码
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ui"))

from kernel_client import KernelClient  # noqa: E402

EXE = os.path.join(ROOT, "build", "bin", "dorm_noise_kernel.exe")
MODEL = os.path.join(ROOT, "models", "ast_audioset.onnx")
SPEECH = os.path.join(ROOT, "assets", "audio_demo", "real_speech_0.wav")
CLASS_KEYS = ["loud_talk", "normal_volume", "game_audio", "normal_talk"]
CLASS_ZH = {"大声喧哗", "正常音量", "游戏外放", "正常交谈"}
DEFAULT_THRESHOLDS = [15.0, 9999.0, 45.0, 9999.0]
PORT = 8765

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
    print("=" * 62)
    print("宿舍噪音识别系统 · UI↔内核 端到端联调测试")
    print("=" * 62)

    if not os.path.exists(EXE):
        print(f"[FATAL] 内核可执行文件不存在: {EXE}")
        return 2
    if not os.path.exists(MODEL):
        print(f"[FATAL] 模型不存在: {MODEL}")
        return 2

    print("\n[1/6] 启动内核 ...")
    proc = subprocess.Popen(
        [EXE, "--model", MODEL, "--port", str(PORT), "--no-capture"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=ROOT,
    )
    time.sleep(6.0)
    if proc.poll() is not None:
        out = proc.stdout.read().decode("utf-8", "replace") if proc.stdout else ""
        print(f"[FATAL] 内核启动即退出:\n{out}")
        return 2

    client = KernelClient(port=PORT)
    try:
        print("\n[2/6] 连接 IPC ...")
        ok = client.connect(timeout=8.0)
        check("连接内核", ok, client.last_error)
        if not ok:
            return 2

        print("\n[3/6] status ...")
        resp = client.status()
        check("status 有响应", resp is not None and resp.get("type") == "state",
              str(resp.get("type")) if resp else "None")
        time.sleep(1.2)
        st = client.state
        check("kernel_alive=True", st.kernel_alive)
        check("classes 四类及顺序正确",
              [c.get("key") or c.get("class_key") for c in st.classes] == CLASS_KEYS,
              str(st.classes))
        check("默认时长阈值和正常音量门限正确", st.segment_sec > 0 and st.thresholds == DEFAULT_THRESHOLDS
              and abs(st.normal_volume_dbfs - (-45.0)) < 1e-6,
              f"segment_sec={st.segment_sec} thresholds={st.thresholds}")
        check("model_path 非空", len(st.model_path) > 0, st.model_path)

        print("\n[4/6] set_config ...")
        resp = client.set_config(segment_sec=3.0, thresholds=[10.0, 20.0, 30.0, 9999.0],
                                 min_confidence=0.05, auto_alert=True, normal_volume_dbfs=-50.0)
        check("set_config 返回 ok", resp is not None and resp.get("type") == "ok",
              json.dumps(resp, ensure_ascii=False) if resp else "None")
        time.sleep(1.2)
        check("新配置已生效", abs(client.state.segment_sec - 3.0) < 1e-6
              and abs(client.state.thresholds[0] - 10.0) < 1e-6
              and abs(client.state.normal_volume_dbfs - (-50.0)) < 1e-6,
              f"segment_sec={client.state.segment_sec} thresholds={client.state.thresholds}")

        print("\n[5/6] reset ...")
        resp = client.reset_stats()
        check("reset 返回 ok", resp is not None and resp.get("type") == "ok")

        print("\n[6/6] offline_file ...")
        if os.path.exists(SPEECH):
            resp = client.offline_file(SPEECH)
            ok = resp is not None and resp.get("type") == "offline_result"
            check("offline_result 返回", ok)
            if ok:
                segs = resp.get("segments") or []
                check("至少一个分段", len(segs) > 0)
                if segs:
                    s = segs[0]
                    check("含分段 RMS dBFS", isinstance(s.get("rms_dbfs"), (int, float)),
                          str(s.get("rms_dbfs")))
                    check("真实朗读判定为正常交谈", s.get("class_key") == "normal_talk",
                          f"{s.get('class_key')} / {s.get('class_zh')} conf={s.get('confidence')}")
                    check("含 top 细分标签", bool(s.get("top_label_name")),
                          f"{s.get('top_label_name')} {s.get('top_label_prob')}")
        else:
            check("真实朗读测试素材存在", False, SPEECH)

        print("\n[6b] 未知命令容错 ...")
        resp = client.send({"cmd": "bogus_cmd"})
        check("未知命令返回 error", resp is not None and resp.get("type") == "error",
              resp.get("message", "") if resp else "None")

        print("\n[7/7] 中文 UTF-8 校验 ...")
        import json as _json
        raw = _json.dumps(client.state.__dict__, ensure_ascii=False, default=str)
        check("中文可序列化", "大声喧哗" in raw or "喧哗" in raw)
        classes_zh = [c.get("class_zh") or c.get("zh") for c in client.state.classes]
        check("classes 含四个中文名", set(classes_zh) == CLASS_ZH, str(classes_zh))

    finally:
        client.disconnect()
        print("\n[清理] 关闭内核 ...")
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

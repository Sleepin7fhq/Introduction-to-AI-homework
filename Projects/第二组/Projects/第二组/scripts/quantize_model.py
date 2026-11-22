#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AST ONNX 模型 int8 动态量化（可选加速步骤）。

背景
----
AST 是 12 层 Transformer，86.6 M 参数，fp32 导出后 346 MB。
在 8 线程 CPU 上单段推理要 ~990 ms，实时场景（5 秒分段）能跑但余量不大。
用 onnxruntime 的 **动态量化**（weights → int8）后：

    体积   346.7 MB → 91.0 MB   (↓74%)
    延迟   995 ms → 525 ms      (↑1.9×，8 线程，CPU EP)
    精度   top-1 标签不变，最大概率偏差 0.031；13 个演示素材分类 13/13 一致

为什么只量化 MatMul / Gemm
--------------------------
AST 的 patch embedding 是一层 Conv2d。量化它会生成 `ConvInteger` 算子，
而 **ONNX Runtime 的 CPU EP 不实现 ConvInteger**：

    NOT_IMPLEMENTED : Could not find an implementation for ConvInteger(10)
    node with name '.../patch_embeddings/projection/Conv_quant'

所以必须把 Conv 排除在量化范围外，只量化 Transformer 主体里的 MatMul / Gemm。
被排除的 Conv 只有 768×1×16×16 ≈ 197 K 参数，占总体积的 0.2%，所以速度收益基本没损失。

用法
----
    python scripts/quantize_model.py \
        --src models/ast_audioset.onnx \
        --dst models/ast_audioset_int8.onnx

然后让内核加载量化模型即可：

    dorm_noise_kernel --model models/ast_audioset_int8.onnx --threads 8
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np


def build_probe(path: str) -> np.ndarray:
    """用黄金向量当输入探针，方便量化前后比对。"""
    golden = os.path.join(os.path.dirname(path), "golden", "fbank.bin")
    if not os.path.exists(golden):
        golden = os.path.join("models", "golden", "fbank.bin")
    if not os.path.exists(golden):
        raise SystemExit("找不到黄金向量 models/golden/fbank.bin，请先跑 export_ast_onnx.py")
    feat = np.fromfile(golden, dtype="<f4").reshape(1024, 128)
    return feat[None, ...]


def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def bench(path: str, feat: np.ndarray, threads: int) -> tuple[float, np.ndarray]:
    import onnxruntime as ort

    so = ort.SessionOptions()
    so.intra_op_num_threads = threads
    so.inter_op_num_threads = 1
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])
    for _ in range(2):
        sess.run(None, {"input_values": feat})
    import time

    ts = []
    for _ in range(5):
        t0 = time.perf_counter()
        out = sess.run(None, {"input_values": feat})
        ts.append((time.perf_counter() - t0) * 1000.0)
    ts.sort()
    return ts[len(ts) // 2], out[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="models/ast_audioset.onnx")
    ap.add_argument("--dst", default="models/ast_audioset_int8.onnx")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--skip-bench", action="store_true")
    args = ap.parse_args()

    from onnxruntime.quantization import QuantType, quantize_dynamic

    print(f"[quant] {args.src} → {args.dst}")
    quantize_dynamic(
        args.src,
        args.dst,
        op_types_to_quantize=["MatMul", "Gemm"],  # 必须排除 Conv（ConvInteger 无 CPU 实现）
        weight_type=QuantType.QInt8,
    )
    fp_mb = os.path.getsize(args.src) / 1e6
    q_mb = os.path.getsize(args.dst) / 1e6
    print(f"[quant] 体积 {fp_mb:.1f} MB → {q_mb:.1f} MB（↓{100 * (1 - q_mb / fp_mb):.0f}%）")

    if args.skip_bench:
        return 0

    feat = build_probe(args.src)
    m_fp, o_fp = bench(args.src, feat, args.threads)
    m_q, o_q = bench(args.dst, feat, args.threads)
    p_fp, p_q = softmax(o_fp[0]), softmax(o_q[0])
    print(f"[bench] fp32 中位 {m_fp:.1f} ms ; int8 中位 {m_q:.1f} ms ; 加速 {m_fp / m_q:.2f}×")
    print(f"[bench] max 概率偏差 {float(np.max(np.abs(p_fp - p_q))):.4f}")
    print(f"[bench] argmax fp32={int(o_fp.argmax())} int8={int(o_q.argmax())}")
    top = np.argsort(-p_q)[:5]
    print("[bench] int8 top5:", [(int(i), round(float(p_q[i]), 4)) for i in top])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

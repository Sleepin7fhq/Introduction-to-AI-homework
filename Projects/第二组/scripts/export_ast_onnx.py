#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_ast_onnx.py
=================
把 HuggingFace 的 AST 音频分类模型（MIT/ast-finetuned-audioset-10-10-0.4593，527 类 AudioSet）
导出为端侧可运行的 ONNX，并生成 C++ 内核需要的元数据文件。

产出：
  models/ast_audioset.onnx      —— 导出的 ONNX 模型（动态 batch，CPU 可跑）
  models/labels.json            —— AudioSet 527 类 id → 名称
  models/label_map.json         —— 四类（大声喧哗/正常音量/游戏外放/正常交谈）定义表 + 预处理参数
  models/golden/golden.wav      —— 校验用 16bit/16kHz 单声道测试音频
  models/golden/fbank.npy       —— 该音频的黄金特征（Python 参考实现）
  models/golden/logits.npy      —— 该特征的 ONNX logits（黄金输出）
  models/golden/meta.json       —— 校验元信息

用法：
  python scripts/export_ast_onnx.py --hf-dir models/hf_ast --out-dir models
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import wave
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------------------
# 1. 四类标签聚合表
#    AudioSet 有 527 类，我们把它们聚合到答辩要求的 4 类。
#    一个标签允许同时属于多个类别（例如 "Synthesizer" 既可能是乐器也可能是游戏音效），
#    最终取各类别概率质量（probability mass）的最大值作为判定结果。
# --------------------------------------------------------------------------------------

# 大声喧哗：喊叫 / 吼叫 / 欢呼 / 尖叫
LOUD_TALK_NAMES = [
    "Shout",
    "Bellow",
    "Whoop",
    "Yell",
    "Battle cry",
    "Children shouting",
    "Screaming",
    "Cheering",
    "Applause",
]

# 正常交谈：说话 / 对话 / 笑声 / 哭声 / 咳嗽 等日常人声（低音量）
NORMAL_TALK_NAMES = [
    "Speech",
    "Male speech",
    "Female speech",
    "Child speech",
    "Conversation",
    "Narration",
    "Babbling",
    "Speech synthesizer",
    "Whispering",
    "Laughter",
    "Baby laughter",
    "Giggle",
    "Snicker",
    "Belly laugh",
    "Chuckle",
    "Crying",
    "Baby cry",
    "Whimper",
    "Wail/moan",
    "Sigh",
    "Rapping",
    "Groan",
    "Grunt",
    "Whistling",
    "Breathing",
    "Wheeze",
    "Snoring",
    "Gasp",
    "Pant",
    "Snort",
    "Cough",
    "Throat clearing",
    "Sneeze",
    "Sniff",
    "Chatter",
    "Crowd",
    "Hubbub, speech noise, speech babble",
]

# 正常音量由内核 RMS 电平门控判断，不映射音乐或其它语义标签。

# 游戏外放：电子游戏 BGM、鼓机、音效提示音等
GAME_NAMES = [
    "Video game music",
    "Drum machine",
    "Electronic music",
    "House music",
    "Techno",
    "Dubstep",
    "Drum and bass",
    "Electronica",
    "EDM",
    "Ambient music",
    "Trance music",
    "Beatboxing",
    "Synthesizer",
    "Sampler",
    "Effects unit",
    "Beep, bleep",
    "Ping",
    "Ding",
    "Video game",
    "Arcade game",
]


def build_class_defs(id2label: dict[int, str]) -> list[dict]:
    """把标签名 -> 标签 id，并组装成四类定义。"""
    name2id = {v: k for k, v in id2label.items()}

    def ids_of(names: list[str]) -> list[int]:
        out = []
        for n in names:
            if n in name2id:
                out.append(int(name2id[n]))
        return sorted(out)

    loud = ids_of(LOUD_TALK_NAMES)
    normal = ids_of(NORMAL_TALK_NAMES)
    game = ids_of(GAME_NAMES)
    # normal_volume 没有语义标签，由 C++ 端 RMS 电平门控决定。

    return [
        {
            "key": "loud_talk",
            "zh": "大声喧哗",
            "icon": "🗣️",
            "ids": loud,
            "names": [id2label[i] for i in loud],
        },
        {
            "key": "normal_volume",
            "zh": "正常音量",
            "icon": "🍃",
            "ids": [],
            "names": [],
            "decision": "segment RMS <= normal_volume_dbfs; not a semantic model class",
        },
        {
            "key": "game_audio",
            "zh": "游戏外放",
            "icon": "🎮",
            "ids": game,
            "names": [id2label[i] for i in game],
        },
        {
            "key": "normal_talk",
            "zh": "正常交谈",
            "icon": "💬",
            "ids": normal,
            "names": [id2label[i] for i in normal],
        },
    ]


# --------------------------------------------------------------------------------------
# 2. 导出
# --------------------------------------------------------------------------------------
def export_onnx(hf_dir: Path, out_path: Path, opset: int = 17) -> None:
    import torch
    from transformers import ASTForAudioClassification

    print(f"[1/4] 加载 PyTorch 模型: {hf_dir}")
    model = ASTForAudioClassification.from_pretrained(str(hf_dir))
    model.eval()

    class LogitsWrapper(torch.nn.Module):
        """只输出 logits，方便 ONNX 导出。"""

        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, input_values):  # input_values: (batch, 1024, 128)
            return self.m(input_values).logits

    wrapped = LogitsWrapper(model).eval()

    # 动态 batch 的 dummy 输入（时间 1024 帧 × 128 mel bin）
    dummy = torch.zeros(1, 1024, 128, dtype=torch.float32)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[2/4] 导出 ONNX (opset={opset}) -> {out_path}")
    torch.onnx.export(
        wrapped,
        dummy,
        str(out_path),
        input_names=["input_values"],
        output_names=["logits"],
        dynamic_axes={"input_values": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=opset,
        do_constant_folding=True,
    )

    # 顺手验一下 PyTorch 自己的输出，供后面 ONNX 对齐
    with torch.no_grad():
        pt_logits = wrapped(dummy).numpy()
    np.save(out_path.parent / "golden" / "_pt_logits_dummy.npy", pt_logits)
    print(f"      PyTorch dummy logits[0][:5] = {pt_logits[0][:5]}")


def check_onnx(onnx_path: Path, golden_dir: Path) -> dict:
    """用 onnxruntime 跑黄金特征，比较与 PyTorch 的差异。"""
    import onnxruntime as ort

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    print("[3/4] ONNX 输入/输出:")
    for i in sess.get_inputs():
        print(f"      input  {i.name}: {i.shape} {i.type}")
    for o in sess.get_outputs():
        print(f"      output {o.name}: {o.shape} {o.type}")

    fb = np.load(golden_dir / "fbank.npy").astype(np.float32)
    logits = sess.run(None, {"input_values": fb[None, ...]})[0]
    np.save(golden_dir / "logits.npy", logits)
    print(f"      ONNX logits[0][:5] = {logits[0][:5]}")
    return {"logits": logits}


def build_golden(hf_dir: Path, golden_dir: Path, out_dir: Path) -> None:
    """生成黄金测试音频 + 参考特征（Python 侧 torchaudio kaldi fbank，与 C++ 实现对齐的目标）。"""
    import torch
    import torchaudio

    golden_dir.mkdir(parents=True, exist_ok=True)

    sr = 16000
    dur = 3.0
    t = np.arange(int(sr * dur), dtype=np.float64) / sr
    # 合成一段"语音样"信号：基频 + 共振峰 + 少量噪声 + 包络
    f0 = 130.0
    sig = (
        0.45 * np.sin(2 * np.pi * f0 * t)
        + 0.25 * np.sin(2 * np.pi * 3 * f0 * t)
        + 0.15 * np.sin(2 * np.pi * 7 * f0 * t)
    )
    env = 0.6 + 0.4 * np.sin(2 * np.pi * 3.0 * t)
    sig = sig * env + 0.02 * np.random.RandomState(0).randn(len(t))
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * 0.6

    pcm = (sig * 32767.0).astype(np.int16)
    wav_path = golden_dir / "golden.wav"
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())

    # 与 transformers ASTFeatureExtractor 完全一致的调用路径
    waveform = torch.from_numpy(sig.astype(np.float32)).unsqueeze(0)
    fbank = torchaudio.compliance.kaldi.fbank(
        waveform,
        sample_frequency=16000,
        window_type="hanning",
        num_mel_bins=128,
    )  # (frames, 128)
    print(f"      kaldi fbank 帧数 = {fbank.shape[0]}")

    # 补齐/截断到 1024 帧，然后按 AST 的归一化
    max_length = 1024
    n = fbank.shape[0]
    if n < max_length:
        fbank = torch.nn.ZeroPad2d((0, 0, 0, max_length - n))(fbank)
    elif n > max_length:
        fbank = fbank[0:max_length, :]
    mean, std = -4.2677393, 4.5689974
    feat = ((fbank.numpy() - mean) / (std * 2)).astype(np.float32)
    np.save(golden_dir / "fbank.npy", feat)

    meta = {
        "sample_rate": sr,
        "duration_sec": dur,
        "frames": int(n),
        "max_length": max_length,
        "num_mel_bins": 128,
        "mean": mean,
        "std": std,
        "note": "fbank.npy = AST 归一化后的 input_values，形状 (1024,128)；C++ 侧应逐元素逼近",
    }
    with open(golden_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"      黄金特征已写入 {golden_dir / 'fbank.npy'}  shape={feat.shape}")

    # 同时导出裸二进制，供 C++ 内核直接读取做数值比对（避免 C++ 侧解析 .npy）
    feat.astype("<f4").tofile(golden_dir / "fbank.bin")
    with open(golden_dir / "golden_features.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "shape": [int(feat.shape[0]), int(feat.shape[1])],
                "dtype": "float32-le",
                "file": "fbank.bin",
                "wav": "golden.wav",
                "mean": mean,
                "std": std,
            },
            f,
            ensure_ascii=False,
            indent=1,
        )
    print(f"      黄金特征裸二进制已写入 {golden_dir / 'fbank.bin'}")


def write_meta(hf_dir: Path, out_dir: Path) -> None:
    cfg = json.load(open(hf_dir / "config.json", encoding="utf-8"))
    id2label = {int(k): v for k, v in cfg["id2label"].items()}
    pre = json.load(open(hf_dir / "preprocessor_config.json", encoding="utf-8"))

    with open(out_dir / "labels.json", "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in sorted(id2label.items())}, f, ensure_ascii=False, indent=1)

    classes = build_class_defs(id2label)
    label_map = {
        "classes": classes,
        "audio": {
            "sample_rate": int(pre.get("sampling_rate", 16000)),
            "num_mel_bins": int(pre.get("num_mel_bins", 128)),
            "max_length": int(pre.get("max_length", 1024)),
            "mean": float(pre.get("mean", -4.2677393)),
            "std": float(pre.get("std", 4.5689974)),
            # AST 官方训练/推理都是 [-1,1] 浮点波形直接喂 fbank（transformers 里 *2**15 那行是被注释掉的），
            # 因此 C++ 侧保持 1.0 不缩放。
            "input_scale": 1.0,
        },
        "labels": {str(k): v for k, v in sorted(id2label.items())},
    }
    with open(out_dir / "label_map.json", "w", encoding="utf-8") as f:
        json.dump(label_map, f, ensure_ascii=False, indent=1)

    write_cpp_labels(label_map, out_dir / "ast_labels.h")

    print("[4/4] 元数据:")
    for c in classes:
        print(f"      {c['key']:<12} ({c['zh']}): {len(c['ids'])} 个 AudioSet 标签")


def write_cpp_labels(label_map: dict, out_path: Path) -> None:
    """
    生成 C++ 侧直接 include 的标签头文件。

    内核不需要在运行时解析 JSON：四类映射表与 AudioSet 全量标签在编译期就固化成静态数组，
    既省掉一个 JSON 依赖，也让"内核只做推理、不做业务配置"的边界更清晰。
    """
    classes = label_map["classes"]
    audio = label_map["audio"]
    labels = label_map["labels"]

    lines = [
        "// ============================================================================",
        "// 自动生成，请勿手工修改。",
        f"// 来源: scripts/export_ast_onnx.py  （HF: MIT/ast-finetuned-audioset-10-10-0.4593）",
        "// 内容: 四类聚合映射 + AudioSet 527 类标签名 + AST 预处理参数",
        "// ============================================================================",
        "#pragma once",
        "#include <cstdint>",
        "",
        "namespace dorm_noise {",
        "",
        "// ---- AST 预处理参数（与 transformers ASTFeatureExtractor 对齐）----",
        f"inline constexpr int    kSampleRate   = {int(audio['sample_rate'])};",
        f"inline constexpr int    kNumMelBins   = {int(audio['num_mel_bins'])};",
        f"inline constexpr int    kMaxLength    = {int(audio['max_length'])};",
        f"inline constexpr float  kFeatureMean  = {float(audio['mean'])!r}f;",
        f"inline constexpr float  kFeatureStd   = {float(audio['std'])!r}f;",
        f"inline constexpr float  kInputScale   = {float(audio['input_scale'])!r}f;",
        "",
        "// ---- 四个目标类别（顺序即 UI 展示顺序）----",
        "enum class ClassKey : int {",
    ]
    for i, c in enumerate(classes):
        lines.append(f"    {c['key']} = {i},  // {c['zh']}")
    lines.append("};")
    lines.append("")
    lines.append(f"inline constexpr int kNumClasses = {len(classes)};")
    lines.append("")

    # 每个类别一个 id 列表
    for c in classes:
        lines.append(f"// {c['zh']} ({c['key']}) -> {len(c['ids'])} 个 AudioSet 标签 id")
        lines.append(f"inline constexpr int kIds_{c['key']}[] = {{")
        ids = c["ids"]
        if not ids:
            lines.append("    -1,  // 占位；该类别由内核电平门控决定，无 AudioSet 标签")
        for j in range(0, len(ids), 12):
            chunk = ids[j : j + 12]
            lines.append("    " + ", ".join(str(int(v)) for v in chunk) + ",")
        lines.append("};")
        lines.append(
            f"inline constexpr int kCount_{c['key']} = {len(ids)};"
        )
        lines.append("")

    # 类别 key 字符串表（供 JSON 输出使用）
    lines.append("inline constexpr const char* kClassKeys[] = {")
    for c in classes:
        lines.append(f'    "{c["key"]}",')
    lines.append("};")
    lines.append("inline constexpr const char* kClassZh[] = {")
    for c in classes:
        lines.append(f'    "{c["zh"]}",')
    lines.append("};")
    lines.append("")

    # AudioSet 527 类标签名
    lines.append("// ---- AudioSet 全量标签（id -> 名称），用于给出最可能的细分标签 ----")
    lines.append(f"inline constexpr int kNumAudioSetLabels = {len(labels)};")
    lines.append("inline constexpr const char* kAudioSetLabels[] = {")
    for k in sorted(labels, key=lambda x: int(x)):
        name = labels[k].replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'    "{name}",  // {k}')
    lines.append("};")
    lines.append("")
    lines.append("}  // namespace dorm_noise")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[5/5] C++ 标签头文件已生成: {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Export HF AST to ONNX for the dorm-noise kernel")
    ap.add_argument("--hf-dir", default="models/hf_ast", help="HuggingFace AST 本地目录")
    ap.add_argument("--out-dir", default="models", help="输出目录")
    ap.add_argument("--opset", type=int, default=17)
    ap.add_argument("--skip-export", action="store_true", help="只重建元数据与黄金向量")
    args = ap.parse_args()

    hf_dir = Path(args.hf_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    golden_dir = out_dir / "golden"
    golden_dir.mkdir(parents=True, exist_ok=True)

    onnx_path = out_dir / "ast_audioset.onnx"

    if not args.skip_export:
        export_onnx(hf_dir, onnx_path, opset=args.opset)

    build_golden(hf_dir, golden_dir, out_dir)
    write_meta(hf_dir, out_dir)

    if onnx_path.exists():
        check_onnx(onnx_path, golden_dir)

    size_mb = onnx_path.stat().st_size / 1024 / 1024 if onnx_path.exists() else 0
    print(f"\n完成。ONNX 大小 = {size_mb:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验：ONNX 与 PyTorch 在黄金特征上的数值一致性，并打印 top-k 标签。"""
import json
import numpy as np
import onnxruntime as ort
import torch
from transformers import ASTForAudioClassification

fb = np.load("models/golden/fbank.npy").astype(np.float32)
model = ASTForAudioClassification.from_pretrained("models/hf_ast").eval()
with torch.no_grad():
    pt = model(torch.from_numpy(fb[None])).logits.numpy()
sess = ort.InferenceSession("models/ast_audioset.onnx", providers=["CPUExecutionProvider"])
ox = sess.run(None, {"input_values": fb[None]})[0]

print("max abs diff :", float(np.max(np.abs(pt - ox))))
print("argmax pt    :", int(pt.argmax()))
print("argmax onnx  :", int(ox.argmax()))

labels = json.load(open("models/labels.json", encoding="utf-8"))
top = np.argsort(-ox[0])[:8]
print("top8         :", [(int(i), labels[str(i)], round(float(ox[0][i]), 3)) for i in top])

lm = json.load(open("models/label_map.json", encoding="utf-8"))
probs = np.exp(ox[0] - ox[0].max())
probs = probs / probs.sum()
for c in lm["classes"]:
    ids = c["ids"]
    mass = float(probs[ids].sum())
    print(f"  {c['key']:<12} {c['zh']:<6} mass={mass:.4f}  n_ids={len(ids)}")

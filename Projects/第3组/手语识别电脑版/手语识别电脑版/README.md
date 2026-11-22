# 手语采集 + 识别（前端）

`collect/` 目录包含三个纯前端页面，全部本地推理、无后端，通过本地 HTTP 服务器运行。

## 三个页面

| 页面 | 文件 | 用途 |
|---|---|---|
| **手语识别** | `recognize.html` | 上传视频/开摄像头，实时识别 203 个手语词（TCN 模型） |
| **骨架采集器** | `collector.html` | 录自己的手语动作，产出骨架序列训练样本 |
| **静态手势实验台** | `index.html` | 单帧静态手势 KNN 识别 Demo（3 类，可自建） |

## 文件

```
collect/
├── recognize.html / recognize.mjs / recognize.css   手语识别页（203 词）
├── web_inference.mjs          纯 JS TCN 推理引擎（零依赖）
├── sign_model_web.json        导出的模型权重（TCN V1，已做 BN 融合）
├── collector.html / collector.mjs / collector.css   采集器页面
├── sequence_engine.mjs        时序样本引擎（录制器/归一化/校验）
├── vendor/                    MediaPipe 模型（复用，无需改）
├── style.css / engine.mjs / index.html / app.mjs    原实验台
└── README.md
```

## 运行方式

```bash
cd collect
python -m http.server 8000
```

浏览器打开：
- 识别页：`http://localhost:8000/recognize.html`
- 采集器：`http://localhost:8000/collector.html`
- 实验台：`http://localhost:8000/index.html`

> 注意：不能用 `file://` 直接打开，ES 模块和 WASM 需要 HTTP。localhost 属于安全上下文，可调用摄像头。

## 识别页（recognize.html）

1. 点「上传视频」选一个手语词视频（约 1–3 秒，H.264 编码的 .mp4），或「开启摄像头」。
2. 画面持续提取手部骨架，每凑满 30 帧用 TCN 模型识别一次。
3. 右侧实时显示 **Top-5 识别结果**（带概率条）与详情。

模型：`sign_model_web.json`，由 `scripts/export_web.py` 从 `models/sign_model.pt` 导出（203 词，Top1 32.68%）。

## 采集器（collector.html）

1. **加载词表**（可选）：点「加载 label_map.json」，选择上一级 `data/label_map.json`，之后「手语词」框可下拉选 200+ 词。
2. **开启摄像头**（或「打开视频」用现成手语视频）。
3. **输入手语词** + 采集者名（如 `Participant_01`）。
4. **点「● 开始录制」**，完整做一遍手语动作，做完点「■ 停止录制」。
   - 录制中骨架变红色，右上角显示帧数。
   - 帧数不足（<5 帧）不保存。
5. 重复采集，每个词建议采 **5–8 条**不同角度/距离的样本。
6. **点「导出样本」** 得到 `csl-sequences-YYYY-MM-DD.json`，交给训练。

## 样本 JSON 结构

```json
{
  "version": 1,
  "samples": [
    {
      "label": "你好",
      "signer": "Participant_01",
      "view": "front",
      "frames": 30,
      "sequence": [[x0,y0,x1,y1,...,x20,y20], ... 30 帧 ...]
    }
  ]
}
```

- 每帧 42 维 = 21 个关键点的 (x,y)，以手腕为原点、按手部尺度归一化。
- 与 `engine.mjs` 的特征提取完全同源，静态/时序样本可混用。

## 纠错反馈（提高准确率的关键）

训练结果反馈后，按以下方式迭代：

1. **单条删除**：样本列表里每条都有「删除」按钮，可删掉手势没做好、角度不对、标签填错的样本。
2. **针对性补采**：训练后某词准确率低 / 易混淆，回到采集器给该词多采几条。
3. **版本管理**：每轮训练前「导出样本」留档，对比不同轮次的准确率变化。

## 数据来源互补

- **NationalCSL-DP 视频**（别人录的，6707 词）→ 离线转骨架序列训练
- **本采集器**（自己录的，实时骨架序列）→ 补充、纠错、适配实际使用场景

两者统一转成「骨架序列 → 标签」格式后喂给同一个时序模型。

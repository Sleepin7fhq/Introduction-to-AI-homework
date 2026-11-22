# 🔄 模型转换与 ONNX 导出

> 从 HuggingFace 原始权重 → 端侧可运行的 ONNX → C++ 内核可用的标签表与黄金向量
> 对应脚本：`scripts/export_ast_onnx.py`

---

## 0. 一句话流程

```text
HuggingFace: MIT/ast-finetuned-audioset-10-10-0.4593
        │  config.json / preprocessor_config.json / pytorch_model.bin
        ▼
python scripts/export_ast_onnx.py --hf-dir models/hf_ast --out-dir models
        │
        ├── models/ast_audioset.onnx      330 MB  输入 [batch,1024,128] → 输出 [batch,527]
        ├── models/ast_labels.h            C++ 编译期直接 include 的标签表
        ├── models/label_map.json          四类聚合定义 + 预处理参数（给 Python/工具用）
        ├── models/labels.json             AudioSet 527 类 id → 名称
        └── models/golden/                黄金向量：golden.wav / fbank.bin / fbank.npy / logits.npy
```

---

## 1. 选型说明：为什么用 AST

| 候选 | 参数量 | ONNX 体积 | 端侧 CPU 延迟 | 结论 |
|---|---|---|---|---|
| **AST (Audio Spectrogram Transformer)** | 87 M | 330 MB | fp32 ≈990 ms/段 · int8 ≈525 ms/段（i9-14900HX，8 线程，CPU EP） | ✅ 选用：精度最好，标签体系是 AudioSet 527 类，提供喧哗、游戏、交谈等语义标签；正常音量由 RMS 门控判定 |
| MobileNetV3 + 自训分类头 | 1.5 M | 6 MB | ≈3 ms | ❌ 需自建训练集，答辩现场解释成本高 |
| YAMNet (MobileNetV1) | 3.7 M | 15 MB | ≈12 ms | 备选：AudioSet 521 类、体积小；但中文标签映射要另做 |
| CLAP / Whisper | >100 M | >400 MB | 慢 | ❌ CLAP 非分类模型；Whisper 做的是 ASR，违反"不做语音识别"的隐私约束 |

> **重要**：Whisper 这类 ASR 模型被明确排除 —— 题目要求"不做语音识别转文字"，
> 而引入 ASR 会让"不保留人声"的承诺在伦理上站不住脚。

---

## 2. 下载原始权重

模型仓库：`MIT/ast-finetuned-audioset-10-10-0.4593`
（在 AudioSet 527 类上微调，输入 10 秒 / 10 帧步长的音频窗口）

需要三个文件：

| 文件 | 用途 | 大小 |
|---|---|---|
| `config.json` | 模型结构 + `id2label`（527 类标签名） | 27 KB |
| `preprocessor_config.json` | 预处理参数（采样率、mel bin 数、归一化 mean/std） | 数百字节 |
| `pytorch_model.bin` | 权重 | 346 MB |

### 国内网络（推荐 hf-mirror 镜像）

```powershell
New-Item -ItemType Directory -Force models\hf_ast
$base = "https://hf-mirror.com/MIT/ast-finetuned-audioset-10-10-0.4593/resolve/main"
foreach ($f in @("config.json","preprocessor_config.json","pytorch_model.bin")) {
  Invoke-WebRequest -Uri "$base/$f" -OutFile "models\hf_ast\$f" -UseBasicParsing -TimeoutSec 1800
}
```

> ⚠️ **仓库名拼写**：必须是 `audioset`，写成 `aedioset` 会返回 `Repository not found`。

### 走代理

```powershell
$base = "https://ghfast.top/https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593/resolve/main"
```

### 大文件被截断怎么办

hf-mirror 传大文件偶尔会在中途断掉。用 `scripts/robust_download.py`（Range 断点续传 + 8 次指数退避）：

```powershell
python scripts\robust_download.py `
  "https://hf-mirror.com/MIT/ast-finetuned-audioset-10-10-0.4593/resolve/main/pytorch_model.bin" `
  -o models\hf_ast\pytorch_model.bin
```

判断是否下载完整：`pytorch_model.bin` 应为 **346,445,675 字节**。

---

## 3. 执行导出

```powershell
python scripts\export_ast_onnx.py --hf-dir models\hf_ast --out-dir models --opset 17
```

参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--hf-dir` | `models/hf_ast` | HF 权重目录 |
| `--out-dir` | `models` | 输出目录 |
| `--opset` | `17` | ONNX opset（ORT 1.22 全面支持） |
| `--skip-export` | — | 跳过 ONNX 导出，只重建标签表与黄金向量（改标签映射时用） |

脚本会依次做 4 件事：

1. **`export_onnx()`** —— 加载 `ASTForAudioClassification`，包一层只输出 logits 的
   `LogitsWrapper`，用 `torch.onnx.export` 导出，`dynamic_axes` 让 batch 维动态：

   ```python
   torch.onnx.export(
       wrapped,
       torch.zeros(1, 1024, 128, dtype=torch.float32),
       str(out_path),
       input_names=["input_values"],
       output_names=["logits"],
       dynamic_axes={"input_values": {0: "batch"}, "logits": {0: "batch"}},
       opset_version=17,
       do_constant_folding=True,
   )
   ```

2. **`build_golden()`** —— 合成一段 3 秒"语音样"信号，写 `golden.wav`（16 bit / 16 kHz / 单声道），
   再用 **与 transformers 完全一致的调用路径** 求参考特征：

   ```python
   waveform = torch.from_numpy(sig.astype(np.float32)).unsqueeze(0)
   fbank = torchaudio.compliance.kaldi.fbank(
       waveform, sample_frequency=16000, window_type="hanning", num_mel_bins=128)
   # 补齐/截断到 1024 帧 → (x - mean) / (std * 2)
   ```

   同时写出 `fbank.npy`（Python 侧）、`fbank.bin`（裸 float32 小端，供 C++ 直接读做数值比对）
   与 `golden_features.json`（shape/dtype/mean/std 元信息）。

3. **`write_meta()`** —— 写 `labels.json`、`label_map.json`，并调用 `write_cpp_labels()`。

4. **`check_onnx()`** —— 用 onnxruntime 跑 `fbank.npy`，得到 `logits.npy`，打印真实输入输出签名。

---

## 4. ★ 预处理规格（必须与 C++ 内核逐位对齐）

这是整个项目**最容易出错**的地方。C++ 内核 `kernel/src/feature_extractor.cpp` 是手写的
kaldi fbank 实现，必须和 `torchaudio.compliance.kaldi.fbank` + `ASTFeatureExtractor`
的结果一致，否则模型输出会完全失真。

### 4.1 波形尺度

transformers 源码里这行是**被注释掉的**：

```python
# waveform = waveform * (2**15)  # Kaldi compliance
```

所以 AST 官方推理输入就是 **[-1, 1] 的 float32 波形**，C++ 侧**不要**做 int16 缩放
（`label_map.json` 里 `input_scale = 1.0`）。

### 4.2 完整处理链（torchaudio `compliance/kaldi.py`）

| 步骤 | 参数 |
|---|---|
| 采样率 | 16000 Hz |
| 窗长 `window_size` | 400 (= 25 ms) |
| 窗移 `window_shift` | 160 (= 10 ms) |
| 补零长度 `padded_window_size` | **512**（`round_to_power_of_two=True` → `next_pow2(400)`） |
| 窗函数 | hanning，`periodic=False` → `0.5 - 0.5*cos(2πn/(N-1))` |
| 去直流 | `remove_dc_offset=True`（每帧减该帧均值） |
| 预加重 | `0.97`，首元素用 **replicate** 填充（即 `x[0]-0.97*x[0]`） |
| 补零位置 | **右侧**补 112 个 0（不是居中） |
| 谱 | `rfft` → 257 个 bin → `abs().pow(2.0)` |
| mel 滤波器 | `num_fft_bins = 512/2 = 256`，`fft_bin_width = 16000/512 = 31.25` Hz，128 个三角带，**右侧补一列 0** → (128, 257) |
| mel 尺度 | kaldi：`mel(f) = 1127*ln(1 + f/700)` |
| 低/高频 | `low_freq=20`，`high_freq=0` → 自动取 nyquist 8000 |
| 对数 | `log(max(x, 1.192092955078125e-07))`（`torch.finfo(float32).eps`） |
| 帧数 | `m = 1 + (num_samples - 400) // 160`（`snip_edges=True`） |

### 4.3 AST 侧的补齐与归一化

```python
# transformers feature_extraction_audio_spectrogram_transformer.py
difference = max_length - n_frames
if difference > 0:  fbank = torch.nn.ZeroPad2d((0,0,0,difference))(fbank)   # 帧维末尾补 0
else:              fbank = fbank[0:max_length, :]                           # 超长截断
normalize = (x - mean) / (std * 2)     # mean=-4.2677393, std=4.5689974
```

> ⚠️ **顺序很关键**：transformers 是 **先补零、再归一化**。
> 所以补零帧归一化后的值不是 0，而是
> `(0 - (-4.2677393)) / (4.5689974 * 2) = **0.46703237**`。
> C++ 实现如果把补零帧直接留 0，模型输入就会和训练分布不一致。

最终输入形状固定为 **(1024, 128)**，顺序是 `[frame, mel_bin]`。

---

## 5. ★ 当前四类：RMS 电平门控 + 语义映射

四类顺序与默认累计时长阈值固定为：

| 索引 | 目标类别 | key | 判定依据 | 默认时长阈值（秒） |
|---|---|---|---|---|
| 0 | 大声喧哗 | `loud_talk` | 高于电平门限后，喊叫等目标语义标签 | 15 |
| 1 | 正常音量 | `normal_volume` | 每段 RMS ≤ `normal_volume_dbfs`，默认 -45 dBFS | 9999 |
| 2 | 游戏外放 | `game_audio` | 高于门限后，游戏/电子音效等目标语义标签 | 45 |
| 3 | 正常交谈 | `normal_talk` | 高于门限后，交谈等目标语义标签 | 9999 |

**电平门控优先于语义标签**：低电平片段统一归正常音量，即使模型认为它是音乐或喊叫。只有 RMS 高于门限才进行语义归类；当目标类别置信度低于 `min_confidence`，或主要标签属于其他声音时，结果保持**未分类**，不硬归正常交谈，也不累加任何一类时长。乐器声（原 `music`）已从四类输出移除，音乐本身不再自动获得一类。

`rms_dbfs` 是每段波形相对数字满刻度的 RMS 电平，**不是 dB SPL 声压级**。`normal_volume_dbfs` 是可配置的业务门限，不是 AST 的 AudioSet 标签，也不需要重新训练模型。`min_confidence` 约束语义判定，不能改变低电平优先规则。9999 秒是可配置的大阈值，不等于无限时长。

### 5.1 改映射后如何生效

```powershell
python scripts\export_ast_onnx.py --skip-export     # 重建标签表与黄金向量，不重导 ONNX
```

会重新生成 `models/ast_labels.h`（C++ 编译期依赖）与 `models/label_map.json`。**改完映射必须重新编译内核**；若要分发便携 exe，还需重建便携包，旧 exe 不会因外部文档或 JSON 变化而更新。

### 5.2 生成标签表与配置的职责

`models/ast_labels.h` 提供预处理常量、527 类细分标签、目标类别 key/中文名与语义映射；`models/label_map.json` 提供 Python/工具使用的元数据。C++ 类别枚举当前为：

```cpp
enum class ClassKey : int {
  loud_talk = 0, normal_volume = 1, game_audio = 2, normal_talk = 3
};
```

正常音量没有对应的 AudioSet 标签数组，其判定依赖内核计算的 RMS 和配置 `normal_volume_dbfs`。内核运行时不解析该 JSON；四类 key/中文名与映射需以当前生成文件和编译产物为准。

---

## 6. 数值一致性验证（三层）

### 6.1 PyTorch ↔ ONNX

```powershell
python scripts\verify_onnx.py
```

期望：**max abs diff ≈ 8.6e-06**，argmax 完全一致。

### 6.2 Python kaldi fbank ↔ 手写 numpy fbank

```powershell
python scripts\check_fbank_spec.py
```

期望：max abs diff **≈ 2.65e-04**（float32 精度级）。

> 这个脚本还发现了一个隐蔽的坑：`np.hanning(401)[:-1] ≠ torch.hann_window(400, periodic=False)`。
> 必须用 `0.5 - 0.5*cos(2πn/(N-1))`。

### 6.3 C++ 内核 ↔ Python 黄金向量 ★

这是最关键的一层 —— 它证明**手写的 C++ 特征提取**和官方实现一致：

```powershell
.\build\bin\dorm_noise_kernel.exe --selftest .\models\golden\fbank.bin .\models\golden\golden.wav
```

期望输出：

```
特征比对: max_abs_diff = 0.006087899
[PASS] C++ 特征与 Python 黄金向量一致
```

内核会读 `golden.wav` → 走自己的 `FeatureExtractor` → 与 `fbank.bin`（Python 参考）
逐元素比较，阈值 0.02。

---

## 7. int8 动态量化（端侧加速，旧版历史实测）

AST 全精度权重 330 MB 对纯 CPU 端侧偏大。已用 ONNX Runtime 动态量化压到 **91 MB**：

```powershell
python scripts\quantize_model.py
```

### 7.1 一条命令的用法

```powershell
python scripts\quantize_model.py `
    --src  models\ast_audioset.onnx `
    --dst  models\ast_audioset_int8.onnx `
    --threads 8
```

脚本会依次做三件事：量化 → 在黄金特征上对比两模型输出 → 打印体积/延迟对比表。

### 7.2 ★必须排除 Conv 的坑

动态量化默认会把 **所有** 权重算子都量化，其中包括 AST patch-embedding 那个
`Conv2d(1, 768, kernel=16×16, stride=10×10)`。一旦它被量化，图里就会出现
`ConvInteger` 算子，而 **ORT CPU EP 没有 ConvInteger 的实现**，加载即报错：

```
NOT_IMPLEMENTED : Could not find an implementation for ConvInteger(10) node
with name '/m/audio_spectrogram_transformer/embeddings/patch_embeddings/projection/Conv_quant'
```

解决办法是**只量化 MatMul / Gemm**，把 Conv 排除掉：

```python
from onnxruntime.quantization import quantize_dynamic, QuantType
quantize_dynamic(
    src, dst,
    op_types_to_quantize=["MatMul", "Gemm"],   # ← 不要省略，否则 Conv 被量化
    weight_type=QuantType.QInt8,
)
```

> 这个 Conv 只有 ~197 K 参数（占全模型 0.2%），排除它对压缩率几乎无影响，
> 却能绕开 CPU EP 不支持 ConvInteger 的坑。

### 7.3 旧版历史实测结果（i9-14900HX，8 线程，CPU EP）

以下分类一致性在移除乐器声、加入 RMS 门控前测得，不代表新版四类验收；性能数据亦应在目标机器复测。

| 指标 | fp32 | int8 | 变化 |
|---|---|---|---|
| 模型体积 | 346.7 MB | **91.0 MB** | **↓ 74 %** |
| 单段推理（内核实测 `infer_ms_avg`） | ≈ 995 ms | **≈ 525 ms** | **1.9×** |
| 单段推理（Python onnxruntime） | 947 ms | 481 ms | 1.97× |
| 黄金特征上的 max 概率偏差 | — | 0.0311 | 可接受 |
| 13 个演示素材的分类 + 细分标签 | — | **13/13 完全一致** | 无回退 |

内核换 int8 模型只要改一个参数：

```powershell
.\build\bin\dorm_noise_kernel.exe --model models\ast_audioset_int8.onnx
```

旧版实测 `piano.wav` 在 int8 下判为当时的「乐器声」0.976（fp32 为 0.968），top 细分标签同为 `Music`。该类别现已移除；新版须按 RMS 门控及未分类规则重新验证。

### 7.4 什么时候该用哪个

| 场景 | 建议 |
|---|---|
| 答辩演示（要展示精度与细分标签） | fp32，330 MB 可接受 |
| 纯 CPU 笔记本 / 树莓派级设备 | int8，91 MB + 1.9× 加速 |
| 需要绝对稳定的置信度数值 | fp32（int8 的置信度会有 ~0.03 抖动） |

---

## 8. 常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| `Repository not found` | 仓库名拼错（`aedioset`） | 必须是 `audioset` |
| `pytorch_model.bin` 只有几百 MB | 下载被截断 | 用 `scripts/robust_download.py` 断点续传 |
| `torch.onnx.export` 报 `onnxscript` 相关错 | onnx/onnxruntime 版本太老 | `pip install -U onnx onnxruntime` |
| ONNX 导出后 C++ 推理结果全乱 | C++ fbank 与官方不一致 | 跑 `--selftest`，再逐条核对第 4 节参数 |
| 改标签映射后内核没生效 | 标签表是编译期常量 | 重新编译内核 |
| ONNX 文件 330 MB 太大 | AST 是 87M 参数全精度 | 用 `scripts/quantize_model.py` 做 int8 动态量化 → 91 MB / 1.9× 加速（见第 7 节，注意排除 Conv） |

---

## 9. 换一个模型怎么办

只要新模型的预处理规格能对上，C++ 内核基本不用改（改 `FeatureParams` 即可）：

1. 修改 `scripts/export_ast_onnx.py` 的 `export_onnx()`（换模型类、换 dummy shape）。
2. 修改 `build_golden()` 里的特征提取调用，**换成新模型官方预处理器**的等价写法。
3. 修改 `build_class_defs()` 的四类映射。
4. 跑 `--skip-export` 之外的全流程，重新生成黄金向量。
5. 跑三层次数值验证（6.1 / 6.2 / 6.3），**必须全绿**再接进内核。
6. 调整 `kernel/include/dn/feature_extractor.h` 的 `FeatureParams` 默认值。

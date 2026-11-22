# 🐳 宿舍噪音智能识别与分类提醒系统

> **C++ 核心推理内核 + Gradio UI 外壳 · 本地 socket IPC · 端侧 ONNX 推理**
> 识别 **大声喧哗 / 正常音量 / 游戏外放 / 正常交谈** 四类音频，统计累计时长，超标实时提醒。
> **全程不落盘原始音频、不保存人声、不做语音识别转文字。**

---

## 📸 效果一览

| 能力 | 实现 | 实测 |
|---|---|---|
| 麦克风实时采集 | miniaudio（WASAPI / CoreAudio / ALSA 自动选后端），16 kHz 单声道 f32 | 分段 5 秒 |
| 特征提取 | **手写** kaldi-fbank 梅尔频谱（自写 radix-2 FFT + 梅尔滤波器组） | 与 Python 黄金向量 max_abs_diff **0.0061** |
| 模型推理 | ONNX Runtime C++ API，AST（AudioSet 527 类）→ ONNX | 动态 batch，CPU fp32 **≈990 ms/段** · int8 **≈525 ms/段**（8 线程，均远快于 5 秒分段周期） |
| 时长统计 | 内核内累计，超阈值触发 alert 推送 | 四类独立计时 |
| UI | Gradio 5.5 + Plotly，4 个 Tab | 纯展示/配置，**不碰音频** |
| 通信 | 本地回环 TCP，JSON-lines 协议 | 127.0.0.1:8765 |

> 表中性能、特征误差及包体大小为既有构建的历史测量，不代表新版四类识别准确率；当前分类规则见下方「当前四类与判定规则」，新版性能与分发包应重新验证。

---

## 🗂 目录结构

```
项目开发/
├── kernel/                      ★ C++ 核心推理内核
│   ├── CMakeLists.txt
│   ├── include/dn/              对外头文件（8 个）
│   │   ├── types.h              结构化数据结构
│   │   ├── feature_extractor.h  kaldi-fbank 梅尔频谱
│   │   ├── classifier.h         ONNX Runtime 推理 + RMS 门控与语义聚合
│   │   ├── pipeline.h           分段 / 统计 / 阈值告警 / 隐私擦除
│   │   ├── capture.h            miniaudio 麦克风采集
│   │   ├── wav_reader.h         离线 WAV 解析（自写）
│   │   ├── ipc_server.h         本地 socket JSON-lines 服务端
│   │   ├── json.h               自写极简 JSON（header-only）
│   │   └── util.h               Windows 编码/路径工具
│   └── src/                     对应实现（7 个 .cpp）
├── ui/                          ★ Gradio UI 外壳
│   ├── app.py                   界面（实时监控/参数配置/离线推理/提醒中心）
│   └── kernel_client.py         IPC 客户端（rid 请求-响应配对）
├── scripts/                     模型转换与数据准备
│   ├── export_ast_onnx.py       ★ HF AST → ONNX + 标签表 + 黄金向量
│   ├── quantize_model.py        ★ int8 动态量化（330 MB → 91 MB）
│   ├── verify_onnx.py           PyTorch ↔ ONNX 数值校验
│   ├── check_fbank_spec.py      numpy fbank ↔ torchaudio 对照
│   ├── e2e_test.py              UI↔内核 端到端联调（四类、配置与真实朗读断言）
│   ├── portable_selftest.py     便携单文件 exe 自检（四类、配置与真实朗读断言）
│   ├── build_portable.py        ★ 构建便携单文件 exe（内核+DLL+模型内嵌）
│   ├── make_demo_audio.py       合成演示音频
│   ├── extract_esc50.py         从 ESC-50 提取真实素材
│   ├── robust_download.py       断点续传下载器
│   └── fetch_real_audio.py      真实音频素材下载
├── models/                      模型与标签
│   ├── ast_audioset.onnx        ★ 330 MB，input[batch,1024,128] → logits[batch,527]
│   ├── ast_audioset_int8.onnx   ★ 91 MB，int8 量化版（旧版实测 1.9× 加速）
│   ├── ast_labels.h             C++ 编译期标签表（自动生成）
│   ├── label_map.json           四类定义 + 预处理参数
│   ├── labels.json              AudioSet 527 类 id→名称
│   ├── hf_ast/                  原始 HF 权重
│   └── golden/                  黄金向量（fbank.bin / golden.wav / logits.npy）
├── third_party/miniaudio.h      单文件音频库
├── .deps/onnxruntime-win-x64-1.22.0/   ONNX Runtime SDK
├── assets/audio_demo/           答辩演示音频（67 个 wav，真实素材 48 个）
├── .cache/assets_src/           素材原始包（parquet 747 MB，**不用打包**）
├── docs/                        ★ 四份文档
│   ├── 编译运行与部署教程.md
│   ├── 模型转换与ONNX导出.md
│   ├── 隐私说明.md
│   └── 答辩演示指引.md
├── build/bin/dorm_noise_kernel.exe      编译产物
├── build/cmake/                        CMake 构建目录
├── build/portable/                     便携版构建目录
├── dist/                               ★ 交付物：单文件可执行 exe
│   ├── 宿舍噪音识别.exe                 102.5 MB（内嵌 int8 模型 + 运行时）
│   └── dorm_noise_standalone.exe        同上（英文名备份）
```

---

## 🚀 快速开始（Windows，3 条命令）

```powershell
cd "C:\Users\qtc91\Deepseeek-Harness工作区\项目开发"

# ① 编译内核
cmake -S kernel -B build\cmake -G Ninja -DCMAKE_BUILD_TYPE=Release `
  -DORT_ROOT="$PWD\.deps\onnxruntime-win-x64-1.22.0" -DMODELS_DIR="$PWD\models"
cmake --build build\cmake --parallel 4

# ② 起内核（终端 A）
.\build\bin\dorm_noise_kernel.exe --model .\models\ast_audioset.onnx

# ③ 起 UI（终端 B）
python ui\app.py
```

浏览器打开 <http://127.0.0.1:7860> → 点「🔌 连接内核」。

> 没有模型？先跑 `python scripts\export_ast_onnx.py --hf-dir models\hf_ast --out-dir models`，
> 详见 [`docs/模型转换与ONNX导出.md`](docs/模型转换与ONNX导出.md)。

---

## 📦 便携单文件版（双击即用，无需装任何东西）

> `dist/宿舍噪音识别.exe` —— **102.5 MB 单个文件**，模型 + ONNX Runtime 运行时都内嵌在里面。

| 用法 | 命令 |
|---|---|
| 双击运行 | 直接双击 exe（自动开内核并监听 8765） |
| 离线推理 | `.\宿舍噪音识别.exe --offline 音频.wav` |
| 只看帮助 | `.\宿舍噪音识别.exe --help` |
| 只解包不运行 | `.\宿舍噪音识别.exe --extract-only D:\某目录` |

**它是怎么做到的**：用 `ld -r -b binary` 把 `dorm_noise_kernel.exe`、`onnxruntime.dll`、
`onnxruntime_providers_shared.dll`、`ast_audioset_int8.onnx` 以资源形式嵌进启动器；
启动时按「先写 `.tmp` 再 `MoveFileEx` 改名」的原子写方式释放到运行目录，**用完的原目录不会多出任何文件**。

释放目录按顺序尝试（每个都写探针文件验证真的可写）：
`%LOCALAPPDATA%\DormNoise\runtime` → `exe 所在目录\DormNoiseRuntime` → `%TEMP%\DormNoiseRuntime`。

**自检**：

```powershell
$env:PYTHONIOENCODING="utf-8"; python scripts\portable_selftest.py
#    期望：FAIL=0（需先重新构建新版便携 exe）
```

**自己重新构建**：

```powershell
python scripts\build_portable.py --out-name "宿舍噪音识别.exe"
#    想要 fp32 版（330 MB 模型）：加 --fp32
```

---

## ✅ 一键自检

```powershell
# ① C++ 特征 ↔ Python 黄金向量
.\build\bin\dorm_noise_kernel.exe --selftest .\models\golden\fbank.bin .\models\golden\golden.wav
#    期望：max_abs_diff = 0.006087899 / [PASS]

# ② 离线推理
.\build\bin\dorm_noise_kernel.exe --offline .\models\ast_audioset.onnx .\assets\audio_demo\real_speech_0.wav
#    期望：class_key = normal_talk, class_zh = 正常交谈, top_label_name = Speech

# ③ UI ↔ 内核 端到端（四类、配置与真实朗读断言）
$env:PYTHONIOENCODING="utf-8"; python scripts\e2e_test.py
#    期望：FAIL=0（断言数量以脚本输出为准）
```

---

## 🧩 架构与职责边界

```
┌──────────────────────────────────────────────────────────────┐
│  进程 A：C++ 内核（dorm_noise_kernel.exe）                    │
│                                                              │
│  麦克风 ──► 内存环形缓冲(≤30s) ──► 分段(5s) ──► SecureZero   │
│                                                     │        │
│                                            梅尔频谱特征        │
│                                                     │        │
│                                        ONNX Runtime 推理      │
│                                                     │        │
│                                         RMS 门控 + 语义聚合    │
│                                                     ▼        │
│  ┌──────────────── 累计时长统计 + 阈值判断 ────────────────┐  │
│  └──────────────────────┬─────────────────────────────────┘  │
└─────────────────────────┼────────────────────────────────────┘
                          │ 本地回环 TCP 127.0.0.1:8765
                          │ JSON-lines（结构化结果，无音频字段）
                          ▼
┌──────────────────────────────────────────────────────────────┐
│  进程 B：Gradio UI（ui/app.py）                              │
│  参数配置 · 实时结果展示 · 时长图表 · 超标提醒 · 文件选择     │
│  ✗ 不采集  ✗ 不推理  ✗ 不解析音频  ✗ 不联网                  │
└──────────────────────────────────────────────────────────────┘
```

**硬边界**：UI 进程从头到尾拿不到一个音频样本。IPC 协议里不存在任何承载音频的字段。

---

## 🎚️ 当前四类与判定规则

| 顺序 | key | 中文名 | 默认累计时长阈值（秒） |
|---|---|---|---|
| 0 | `loud_talk` | 大声喧哗 | 15 |
| 1 | `normal_volume` | 正常音量 | 9999 |
| 2 | `game_audio` | 游戏外放 | 45 |
| 3 | `normal_talk` | 正常交谈 | 9999 |

先计算每段音频的 RMS 相对满刻度电平 `rms_dbfs`：**RMS ≤ `normal_volume_dbfs`（默认 -45 dBFS）优先归为正常音量**，不论其语义标签是什么。只有高于该门限的片段才做语义分类，选择大声喧哗、游戏外放或正常交谈；置信度不足或主要标签不属于这些语义类别时保留为**未分类**，不计入任一类时长，不强行归为正常交谈。乐器声已从四类中移除；高电平乐器/音乐也不能仅因不属喧哗就算正常交谈。

`normal_volume_dbfs` 可通过参数配置或 IPC `set_config` 调整。dBFS 是数字信号相对满刻度电平，受麦克风增益、距离和设备影响，**不是 dB SPL 声压级，也不是校准的环境分贝读数**。9999 秒是较大的可配置阈值，不是无限时长。

---

## 🔒 隐私设计（题目重中之重）

| 约束 | 落地方式 | 代码位置 |
|---|---|---|
| 不存原始音频 | 全项目无 `ofstream`/`fopen` 写音频路径；采集缓冲只在内存 | `kernel/src/capture.cpp` |
| 不保存人声 | 推理完成立刻 `SecureZero` 覆写擦除原始 PCM 与特征 | `kernel/src/pipeline.cpp` |
| 不做语音识别 | 全项目无 ASR 代码；模型只输出 527 类标签概率分布 | — |
| 不留录音文件 | 磁盘上不会产生任何新音频文件（可现场 `Get-ChildItem` 验证） | — |
| UI 不碰音频 | IPC 协议无音频字段；UI 进程无法访问内核内存 | `kernel/src/ipc_server.cpp` |

完整说明见 [`docs/隐私说明.md`](docs/隐私说明.md)。

---

## 📚 文档

| 文档 | 内容 |
|---|---|
| [`docs/编译运行与部署教程.md`](docs/编译运行与部署教程.md) | 依赖准备、CMake+Ninja 编译、运行、IPC 协议全文、验证清单、FAQ、Linux/macOS |
| [`docs/模型转换与ONNX导出.md`](docs/模型转换与ONNX导出.md) | HF→ONNX 步骤、★预处理规格逐位对齐、四类标签映射、三层数值验证、int8 量化 |
| [`docs/隐私说明.md`](docs/隐私说明.md) | 约束逐条落地表、数据流全图、SecureZero 实现、网络行为表 |
| [`docs/答辩演示指引.md`](docs/答辩演示指引.md) | 6 幕演示脚本、评委 Q&A、救场预案、打包清单 |

---

## 🔧 环境说明

| 依赖 | 本项目验证版本 |
|---|---|
| C++ 编译器 | MinGW-w64 GCC 16.1.0（MSVC 2019+ 同样支持） |
| CMake / Ninja | 4.4.5 / 1.13 |
| ONNX Runtime | 1.22.0 CPU（官方 Release zip） |
| Python | 3.11.9 |
| Python 包 | torch 2.5.1+cpu、torchaudio 2.5.1+cpu、transformers 4.44.2、onnx 1.17.0、onnxruntime 1.22.0、gradio 5.5.0、plotly 7.1.0、pyarrow |

> ⚠️ **MinGW 两个必读坑**（CMakeLists 已处理，手写编译时注意）：
> 1. 必须 `-U_stdcall -D_stdcall=`（ORT 头文件用了 MSVC 关键字，否则报几十条假错）
> 2. 必须用 `-G Ninja`（`MinGW Makefiles` 与 CMake 4.x 不兼容）
> 3. ORT API 是动态静态初始化，必须 `#define ORT_API_MANUAL_INIT` + `std::call_once`（否则 exe 启动即 0xC0000005）

---

## 📊 识别效果（旧版历史记录，非当前四类验收）

以下是**移除乐器声、加入正常音量之前**的历史实测，保留作模型输出参考；旧版分类及置信度不能当作新版验证结果。

| 音频 | 旧版判定 | 旧版置信度 | top-1 细分标签 |
|---|---|---|---|
| `piano.wav`（真实钢琴） | 乐器声（现已移除） | 0.968 | Music |
| `real_speech_0.wav`（真实朗读） | 正常交谈 | 0.845 | Speech |
| `real_speech_1.wav` | 正常交谈 | 0.915 | Speech |
| `snare.wav`（真实鼓） | 乐器声（现已移除） | 0.73～0.86 | Drum / Music |
| `sir_duke_fast.wav`（小号） | 乐器声（现已移除） | 0.992 | Trumpet |
| `esc50_clapping_*.wav`（真实鼓掌 6 条） | 旧聚合曾归大声喧哗 | 0.11～0.93 | Clapping / Applause |
| `steam_whistle.wav`（四类之外） | 旧聚合低置信度 | 0.006 | Steam whistle |

**掌声不是人声喊叫，不能作为真实喊叫识别能力的验证证据。** 新版验收应分别检查低电平门控、真实交谈、真实喊叫、真实游戏外放与四类外声音，记录 `rms_dbfs`、门限、语义标签及是否未分类。旧版样本没有证明新版完整四类识别准确率。

---

## ⚡ 端侧加速：int8 动态量化（可选，旧版历史实测）

```powershell
python scripts\quantize_model.py          # → models/ast_audioset_int8.onnx
.\build\bin\dorm_noise_kernel.exe --model models\ast_audioset_int8.onnx
```

| 指标 | fp32 | int8 |
|---|---|---|
| 模型体积 | 346.7 MB | **91.0 MB（↓74%）** |
| 单段推理（8 线程，CPU EP） | ≈ 995 ms | **≈ 525 ms（1.9×）** |
| 13 个演示素材分类 + 细分标签（旧版映射） | 基准 | **13/13 完全一致**，不代表新版四类验收 |

> ⚠️ 量化时**必须排除 Conv**（`op_types_to_quantize=["MatMul","Gemm"]`），
> 否则 AST 的 patch-embedding Conv2d 会变成 `ConvInteger`，ORT CPU EP 直接报 NOT_IMPLEMENTED。
> 详见 [`docs/模型转换与ONNX导出.md` 第 7 节](docs/模型转换与ONNX导出.md)。

---

## 📄 许可与引用

- 模型：[`MIT/ast-finetuned-audioset-10-10-0.4593`](https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593)（AudioSet 527 类）
- 音频库：[miniaudio](https://github.com/mackron/miniaudio)（MIT，单文件）
- 运行时：[ONNX Runtime](https://github.com/microsoft/onnxruntime)（MIT）
- 演示素材：ESC-50（CC BY-NC 3.0）、LibriSpeech（CC BY 4.0）、librosa/pytorch 示例音频

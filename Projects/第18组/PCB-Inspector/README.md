# 微瑕必究 · PCB 图块质检

## 在这台电脑上启动

双击本目录的 **start.cmd**。控制台显示本地地址后，在浏览器打开该地址。左侧切换到“演示批次”，点击“开始检测”。在“逐图复核”切换原图和定位结果，在“批次明细”查看统计，底部可下载离线 HTML 报告和 CSV 明细。关闭启动窗口即可停止服务。

启动器先查找本目录的 `.venv`，再查找当前 Codex 项目已安装的环境。移动系统文件夹到其他电脑后，请先安装下述运行环境。系统启动和检测使用已随包提供的 PCB 专用权重，支持 CPU 及 CUDA。

## 模型与结果

- `model/pcb.pt` 和 `model/release.json` 是经验证集规则选定的部署权重与默认置信度。
- `experiments/` 存放两个模型的结构、逐轮训练日志、按组样本清单、实验指标及测试集的预测和错误明细。另一种结构的最佳权重也随包交付。
- `demo/` 为验证组中 10 对图块。文件名含 test 的是待检图，含 temp 的是清洁模板。每个文件作为一个检测单位，所有演示图像均源自 DeepPCB，仅用于研究与教学。
- `inspection.py` 提供推理、批次汇总与导出。`app.py` 为 Streamlit 入口。

对于本实验，每张原图均为 640 × 640。上传其他尺寸时，模型自动缩放并将输出框映射回输入图像。结果表中的四个数依次为左、上、右、下像素坐标。导出报告中的图例 1–6 分别为断路、短路、缺口、毛刺、多余铜、针孔。批次的图块模拟合格率等于未检出缺陷的有效图块数除以有效图块总数。图像解码或推理失败会保留错误记录。

## 在新电脑安装

下列命令在本文件所在目录的 PowerShell 中执行。实验使用 Windows x64 和 Python 3.12。先安装支持本机驱动的 PyTorch。本实验使用的 CUDA 组合见 [PyTorch 官方版本表](https://pytorch.org/get-started/previous-versions/)。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\start.cmd
```

纯 CPU 电脑将第一条 pip 安装命令的索引后缀 cu128 改为 cpu。训练程序面向 NVIDIA GPU。首次安装需要网络，后续使用已训练权重进行本地推理。

## 重现实验

在系统目录放置从 [Ultralytics YOLO11 发布页](https://github.com/ultralytics/assets/releases/tag/v8.3.0) 下载的 yolo11n.pt。使用相同的 Python 环境，PowerShell 中执行以下命令。

```powershell
git clone https://github.com/tangsanli5201/DeepPCB.git DeepPCB
git -C DeepPCB checkout 08e98c4db5922613fb97176eb3d6497d48260cb1
.\.venv\Scripts\python.exe prepare_data.py DeepPCB dataset
.\.venv\Scripts\python.exe train.py --data dataset/data.yaml --weights yolo11n.pt --runs runs --variant baseline
.\.venv\Scripts\python.exe train.py --data dataset/data.yaml --weights yolo11n.pt --runs runs --variant p2
.\.venv\Scripts\python.exe evaluate.py --dataset dataset --runs runs --output evaluated
```

每次复现实验请使用新的 runs 目录，保证评估脚本读取本次训练的两个最佳权重。评估程序首先在验证集上确定两个部署阈值，计算微小 AP50 和预热后的 P95 延迟，写入选择结果后再读取测试集。部署候选为验证集微小 AP50 距最高分不超过 0.005 的模型，候选中选择 P95 较低者。权重和指标保存在 evaluated，确认结果后可用于另一次部署。原始指标用 0–1 比例，报告表格转换为百分数。

## 来源

数据和演示图片致谢 Sanli Tang 等，遵循原作者指定的研究用途。仓库说明见 [DeepPCB](https://github.com/tangsanli5201/DeepPCB)。基础网络与预训练权重来自 [Ultralytics](https://github.com/ultralytics/ultralytics)，相应许可见随包 notices 目录。

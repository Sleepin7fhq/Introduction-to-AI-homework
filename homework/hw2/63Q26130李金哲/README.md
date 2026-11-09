# 人工智能第三次作业：强化学习（实验代码）

一套**零外部依赖（除 numpy / python-docx）**的网格迷宫强化学习实验台，
用 Python 复现作业要求的四组实验，并自动生成图表与 Word 报告。

## 目录结构

| 文件 / 目录 | 说明 |
| --- | --- |
| `rl_core.py` | 网格迷宫环境（随机滑移、陷阱、钥匙、多种奖励函数）、Q-learning、蒙特卡洛控制、值迭代、策略评估 |
| `mazes.py` | 三套 9×9 迷宫（简单版 / 多坑版 / 死胡同版）与奖励实验专用房间 |
| `run_experiments.py` | 跑完四组实验（8~10 个随机种子），输出 `results/summary.json` 与 `results/curves.npz` |
| `plot_kit.py` | 只用 Pillow 实现的轻量绘图工具（没有 matplotlib 依赖） |
| `make_figures.py` | 生成 `figures/` 下的 5 张插图 |
| `build_report.py` | 读取实验结果，生成提交用的 Word 文档 |
| `人工智能第三次作业-强化学习-提交版.docx` | 最终交付的作业文档（11 页） |

## 复现方式

```bash
python run_experiments.py   # 约 90 秒，得到 results/*
python make_figures.py      # 生成 figures/*.png
python build_report.py      # 生成 Word 文档
```

依赖：`numpy`、`python-docx`、`Pillow`（绘图）、`lxml`（python-docx 依赖）。

## 实验一览

| 编号 | 实验 | 主要结论 |
| --- | --- | --- |
| E1 | TD(Q-learning) vs MC 在三种迷宫上的效率 | TD 收敛更快、策略更短；迷宫变复杂后 MC 成功率显著下降 |
| E2 | 稀疏奖励 / 邻近奖励 / 势函数塑形 | 邻近奖励出现「奖励黑客」（刷分 360、成功率 0.09）；PBRS 既加速又不改变最优策略 |
| E3 | 示范质量 → 模仿学习初始化 | 专家示范 3 回合收敛；随机 / 反向示范造成难以恢复的负迁移 |
| E4 | ε 衰减 vs 固定 ε | 收敛速度相近，衰减策略的带探索成功率 0.90+、回报方差明显更小 |

## 实现要点

- **确定性可复现**：所有随机性都来自 `numpy.random.default_rng(seed)`，种子固定。
- **公平对比**：TD 与 MC 使用同一 α、γ、ε 与同一评估协议（每 10 回合、ε=0 贪心评估 20 次）。
- **训练用随机起点**：训练时从迷宫随机普通格出发（保证 MC 有足够探索），评估时固定从起点 S 出发。

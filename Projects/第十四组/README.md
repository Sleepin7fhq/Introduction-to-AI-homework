# 旋律配伴奏 AI（符号域原型）

给一段**已有的单声部旋律**自动配和声与伴奏，输出多轨 MIDI，并可合成 WAV 试听。

这不是神经网络，而是一个**可解释的规则 + 动态规划**系统：调性识别 → 和弦序列搜索 →
声部连接 → 织体生成。它用来回答一个更实际的问题：这类任务到底难在哪、要做多久。

## 快速开始

```bash
# 文本记谱 -> 带伴奏的 MIDI + WAV
python -m melody_accompanist.cli examples/twinkle.txt --style alberti \
    -o output/twinkle.mid --wav output/twinkle.wav

# 也可以直接喂 MIDI（自动挑音区最高的旋律轨，可用 --track 指定）
python -m melody_accompanist.cli 我的旋律.mid --style arpeggio --wav out.wav

# 只看分析结果
python -m melody_accompanist.cli examples/minor_ballad.txt --json
```

依赖：Python 3.10+、numpy（合成 WAV 用）；Pillow 只有画钢琴卷帘图时需要。

## 文本记谱格式

```
tempo 100
meter 4/4
C4 C4 G4 G4 | A4 A4 G4:2 | R:1 F#4:0.5
```

- `音名+八度:时值(拍)`，省略时值默认为 1 拍，支持 `1.5`、`1/2`
- `R` 是休止；`|` 小节线会被忽略；`#` 开头或空格后的 `#` 是注释
- 升号写作 `F#4`，降号写作 `Bb3`

## 织体

| 名称 | 说明 |
| --- | --- |
| `block` | 柱式和弦，适合慢歌铺底 |
| `alberti` | 阿尔贝蒂低音，古典钢琴常用（默认） |
| `arpeggio` | 分解和弦，流行抒情 |
| `waltz` | 圆舞曲式“低音-和弦-和弦”，3/4 拍 |
| `pop` | 低音 + 反拍和弦 |
| `pad` | 长音铺底，弦乐/合成器感觉 |

## 工作流程

1. **解析**：MIDI（自写 SMF 读写，无第三方依赖）或文本记谱 → 音符序列
2. **调性识别**：Krumhansl-Kessler 音级轮廓相关，24 个大小调排序
3. **乐句划分**：按 `--phrase-bars`（默认 4 小节）+ 明显休止切句
4. **和声**：每小节 1/2/4 个和弦槽，候选为调内三和弦、七和弦、副属、借用；
   槽内按“旋律音与和弦的契合度”打分，槽间按功能进行、根音进行、终止式打分，
   用 Viterbi 求全局最优
5. **编配**：声部连接（最小移动、音区跟随旋律）、低音选择、织体展开、力度随旋律起伏
6. **输出**：三轨 MIDI（旋律/和弦/低音）+ 可选的加法合成 WAV

## 目录

```
melody_accompanist/
  theory.py     调性、和弦、候选和弦表
  melody.py     音符/旋律、文本解析、调性识别、乐句
  smf.py        MIDI 读写
  harmonize.py  和弦序列 DP
  arrange.py    声部连接与织体
  synth.py      WAV 合成
  cli.py        命令行
examples/       三个示例旋律
output/         演示输出（MIDI/WAV/钢琴卷帘图）
tests/          自检（python tests/test_all.py）
tools/          调试、画图、基准测试脚本
```

## 已知边界

- 只处理**单声部、节奏基本规整**的旋律；不包含音频转谱、人声分离
- 和声是“教科书式”的：能保证调性、终止式和基本进行，但织体与和声色彩变化有限
- 不支持移调乐器、复杂拍号（5/4、7/8）、自由速度
- 合成音色是占位级别，正式使用请把 MIDI 拖进 DAW 换音源

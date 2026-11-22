# -*- coding: utf-8 -*-
"""交付报告与使用说明书补上 2.1/2.2 的事实。"""
import io

# ---- 交付报告：追加升级章节 ----
R = r'D:\AI\aihw\交付报告.md'
r = io.open(R, encoding='utf-8').read()
if '2.2 采样库' not in r:
    section = '''
---

## 十三、后续升级（2.1 / 2.2）

交付后针对「本地音色像提示音」继续做了两轮升级，**不影响 ACE-Step 的既有能力**：

### 2.1 音色引擎重写

- 重写 `src/music/voices.ts`：三层 Kick、三层军鼓、三连击拍手、sub+mid 双层贝斯、
  3–5 层 detune 主音、共振峰人声切片、每轨独立混响/延迟送出、总线 EQ3 + 驱动；
- 新增 7 个风格预设（`src/music/styles.ts`）：司凤 Rave / 鬼畜切片 / 热梗 Techno /
  Hardstyle / Hyperpop / 经典 EDM / 混沌 Rave；
- 修复「锁定风格不生效」的 bug：以前 `composeSongEx` 会按文本重新推断流派；
- 热梗库 16 → 58 条（42 条带来源与置信度，未核实的标「待核实」）。

### 2.2 采样库与采样器

- 自建 **52 个 one-shot 采样**（48kHz/16bit，CC0 自制，9.1MB，16 个分类）；
- 新增 `src/audio/sampler.ts`：`AudioBufferSourceNode` 触发，支持变调、力度、声像、
  复音、切片；7 套 kit 按风格切换鼓组/贝斯/主音/人声切片；
- 采样不可用（如 `file://` 直开）时自动回退 2.1 合成音色；
- 客观效果：kick 低频占比 34%→46%，air 6.8%→12.2%，离线渲染耗时 14–17s → 1.2–3.0s。

### 关于采样来源的说明

尝试过 MusicRadar（CDN TLS 被拦）、Freesound（仅 MP3 预览）、archive.org（CC0 条目与
描述冲突）、Wikimedia Commons（0 命中），均未能取得合规可用素材，故采样为本项目
DSP 自制（`scripts/build_samples.py`），版权干净、可商用。

### 回归

2.2 完成后重跑：核心 44 + 渲染 31 + 浏览器端到端 22 + ACE 音频闭环 12 + 回退 9
= **118 项全部通过**。
'''
    r = r.rstrip() + '\n' + section
    io.open(R, 'w', encoding='utf-8', newline='\n').write(r)
    print('交付报告 updated')

# ---- 使用说明书：术语与能力描述 ----
M = r'D:\AI\aihw\使用说明书.md'
m = io.open(M, encoding='utf-8').read()
old_term = '| 符号引擎 | 用乐理规则生成音符（MIDI 数据），由 Web Audio 实时合成 |'
new_term = '| 符号引擎 | 用乐理规则生成音符（MIDI 数据），由 Web Audio 播放 one-shot 采样（2.2 起） |'
if old_term in m:
    m = m.replace(old_term, new_term)
old_cap = '- **主旋律、贝斯、和声、鼓组、Riser 全部是音符**，不是一段黑盒音频，可以静音、调音量、导出 MIDI；'
new_cap = ('- **主旋律、贝斯、和声、鼓组、Riser 全部是音符**，不是一段黑盒音频，可以静音、调音量、导出 MIDI；\n'
           '- 音色来自 **52 个自制 one-shot 采样**（48kHz/16bit，CC0），按 7 套 kit 随风格切换；')
if old_cap in m and '52 个自制' not in m:
    m = m.replace(old_cap, new_cap, 1)
io.open(M, 'w', encoding='utf-8', newline='\n').write(m)
print('使用说明书 updated')

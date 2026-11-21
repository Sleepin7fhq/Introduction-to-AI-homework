# -*- coding: utf-8 -*-
"""把 2.2 采样库补进 PPT / 报告 / 讲稿 / 演示文档。"""
import io
import re

# ---------------- PPT ----------------
P = r'D:\AI\aihw\课堂展示\src\build_pptx.py'
s = io.open(P, encoding='utf-8').read()

old_strip = """# 底部：适配层
rect(s, 0.9, 6.05, 11.5, 0.72, fill=PANEL2, line=LINE, radius=0.12)
tx(s, 1.15, 6.19, 3.2, 0.3, '统一后端适配层', 11.5, VIOLET, bold=True)
tx(s, 3.55, 6.2, 8.6, 0.3, '引擎状态实时探测  ·  不可用就如实标注  ·  失败自动回退到符号引擎', 10, TEXT2)"""
new_strip = """# 底部：适配层 + 音色来源
rect(s, 0.9, 5.95, 11.5, 0.92, fill=PANEL2, line=LINE, radius=0.12)
tx(s, 1.15, 6.05, 3.2, 0.28, '统一后端适配层', 11.5, VIOLET, bold=True)
tx(s, 3.55, 6.06, 8.6, 0.28, '引擎状态实时探测  ·  不可用就如实标注  ·  失败自动回退到符号引擎', 10, TEXT2)
tx(s, 1.15, 6.42, 11.0, 0.28, '本地音色：52 个自制 one-shot 采样（CC0）· AudioBufferSourceNode 触发 · 7 套 kit 按风格切换', 10, TEAL)"""
assert old_strip in s
s = s.replace(old_strip, new_strip)

old_s7 = """tx(s, 1.15, 6.14, 11.0, 0.5,
   '真实浏览器端到端：点按钮生成 · 数出 576 个音符 · 播放头真的在走 · 音频 readyState=4 且能播放',
   10, TEXT2)"""
new_s7 = """tx(s, 1.15, 6.12, 11.0, 0.28,
   '真实浏览器端到端：点按钮生成 · 数出 576 个音符 · 播放头真的在走 · 音频 readyState=4 且能播放',
   10, TEXT2)
tx(s, 1.15, 6.44, 11.0, 0.28,
   '采样库：52 个自制 one-shot（48kHz/16bit）· 7 套 kit · 鼓组/贝斯/主音/人声切片全部走真实 WAV',
   10, TEAL)"""
assert old_s7 in s
s = s.replace(old_s7, new_s7)
io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('PPT updated')

# ---------------- 创意报告 ----------------
R = r'D:\AI\aihw\课堂展示\src\make_report.py'
r = io.open(R, encoding='utf-8').read()

old_tech = "'（3）Web Audio 合成与 MIDI 导出：Tone.js 按小节滚动调度，导出标准 MIDI（format 1）；'"
new_tech = ("'（3）Web Audio 合成与 MIDI 导出：Tone.js 按小节滚动调度，导出标准 MIDI（format 1）；'\n"
            "   '（3b）采样库与采样器：自建 52 个 one-shot 采样（48kHz/16bit，CC0 自制），'\n"
            "   '按 7 套 kit 绑定鼓组、贝斯、主音与人声切片，用 AudioBufferSourceNode 触发，'\n"
            "   '支持变调、力度、声像与复音，采样不可用时自动回退合成音色；'")
assert old_tech in r
r = r.replace(old_tech, new_tech)

old_tools = "'验证与材料：自建自动化测试（118 项断言）、Python（python-pptx / python-docx / Pillow）制作展示材料。'"
new_tools = ("'音色：52 个自制 one-shot 采样（numpy DSP 生成，CC0）、AudioBufferSourceNode 采样器；'\n"
             "   '验证与材料：自建自动化测试（118 项断言）、Python（python-pptx / python-docx / Pillow）制作展示材料。'")
assert old_tools in r
r = r.replace(old_tools, new_tools)

old_sum = "'两段真实音频的非静音占比分别为 93.3% 与 98.0%，峰值 −1.00 dBFS；'"
new_sum = ("'本地音色已从振荡器合成升级为 52 个自制 one-shot 采样（7 套 kit 按风格切换）；'\n"
           "   '两段真实音频的非静音占比分别为 93.3% 与 98.0%，峰值 −1.00 dBFS；'")
assert old_sum in r
r = r.replace(old_sum, new_sum)

io.open(R, 'w', encoding='utf-8', newline='\n').write(r)
print('report updated')

# ---------------- 演讲稿 ----------------
SP = r'D:\AI\aihw\课堂展示\演讲稿-3分钟.md'
sp = io.open(SP, encoding='utf-8').read()
old = '左边符号引擎：解析、作曲、编排、Web Audio 合成，毫秒级，产物是音符，能改、能导出 MIDI。'
new = '左边符号引擎：解析、作曲、编排，音色来自 52 个自制采样，毫秒级，产物是音符，能改、能导出 MIDI。'
assert old in sp
sp = sp.replace(old, new)
io.open(SP, 'w', encoding='utf-8', newline='\n').write(sp)
print('speech updated')

# ---------------- 演示脚本 ----------------
DS = r'D:\AI\aihw\演示脚本.md'
ds = io.open(DS, encoding='utf-8').read()
if '司凤 Rave' not in ds:
    anchor = '把「小节」改成 **8**（约 15 秒音频，生成更快）。'
    add = ('把「小节」改成 **8**（约 15 秒音频，生成更快）。\n\n'
           '> 想听这次的采样音色，把「生成引擎」切到**本地符号引擎**，风格选 **司凤 Rave** 或 **Hardstyle**——\n'
           '> 鼓组、贝斯、主音、人声切片全部来自 52 个自制 one-shot 采样。\n')
    assert anchor in ds
    ds = ds.replace(anchor, add, 1)
    io.open(DS, 'w', encoding='utf-8', newline='\n').write(ds)
    print('demo script updated')

# ---------------- 操作卡 ----------------
C = r'D:\AI\aihw\现场演示操作卡.md'
c = io.open(C, encoding='utf-8').read()
if '司凤 Rave' not in c:
    old_row = '| 2. 可编辑 | 引擎切 **本地符号引擎** → 再点**生成音乐** | 时间轴出现五轨音符，和弦 `Gm7 → Fmaj7…` |'
    new_row = '| 2. 可编辑 | 引擎切 **本地符号引擎** → 风格选 **司凤 Rave / Hardstyle** → 再点**生成音乐** | 五轨音符 + 采样鼓组，和弦 `Gm7 → Fmaj7…` |'
    assert old_row in c
    c = c.replace(old_row, new_row)
    io.open(C, 'w', encoding='utf-8', newline='\n').write(c)
    print('demo card updated')

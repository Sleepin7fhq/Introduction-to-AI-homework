# -*- coding: utf-8 -*-
"""在 PPT 技术页和创意报告里点名 7 个风格预设。"""
import io

# PPT：底部那行补风格名
P = r'D:\AI\aihw\课堂展示\src\build_pptx.py'
s = io.open(P, encoding='utf-8').read()
old = "'本地音色：52 个自制 one-shot 采样（CC0）· AudioBufferSourceNode 触发 · 7 套 kit 按风格切换'"
new = "'本地音色：52 个自制采样（CC0）· 7 套 kit：司凤 Rave / Hardstyle / Techno / EDM / 鬼畜切片 …'"
assert old in s
s = s.replace(old, new)
io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('PPT style names added')

# 报告：核心创意里点名 7 个预设
R = r'D:\AI\aihw\课堂展示\src\make_report.py'
r = io.open(R, encoding='utf-8').read()
anchor = "'Drop 时刻大屏打出“06:59 · 再睡五分钟”。')"
add = ("'Drop 时刻大屏打出“06:59 · 再睡五分钟”。'\n"
       "   '目前内置 7 套风格预设：司凤 Rave、鬼畜切片、热梗 Techno、Hardstyle、Hyperpop、'\n"
       "   '经典 EDM、混沌 Rave；每套预设决定 BPM、调式、鼓组、贝斯、主音、人声切片与段落结构。')")
assert anchor in r
r = r.replace(anchor, add, 1)
io.open(R, 'w', encoding='utf-8', newline='\n').write(r)
print('report style names added')

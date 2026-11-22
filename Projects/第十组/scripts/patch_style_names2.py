# -*- coding: utf-8 -*-
"""创意报告：核心创意里点名 7 个风格预设（按实际行内容匹配）。"""
import io

R = r'D:\AI\aihw\课堂展示\src\make_report.py'
r = io.open(R, encoding='utf-8').read()

anchor = "'因此使用 acid 的十六分滚动来模拟闹钟的滴答，Drop 时刻大屏打出“06:59 · 再睡五分钟”。')"
assert anchor in r, 'anchor not found'

add = ("'因此使用 acid 的十六分滚动来模拟闹钟的滴答，Drop 时刻大屏打出“06:59 · 再睡五分钟”。'\n"
       "   '目前内置 7 套风格预设：司凤 Rave、鬼畜切片、热梗 Techno、Hardstyle、Hyperpop、经典 EDM、'\n"
       "   '混沌 Rave；每套预设决定 BPM、调式、鼓组、贝斯、主音、人声切片与段落结构。')")

r = r.replace(anchor, add, 1)
io.open(R, 'w', encoding='utf-8', newline='\n').write(r)
print('report patched with 7 presets')

# -*- coding: utf-8 -*-
"""构建 DSH Studio 2.0 课堂展示 PPT（16:9，深色 DAW 风格）。

所有数据均来自项目实测：4.45GB / 10s / 48kHz / 118 项断言 / 真实 WAV 波形。
"""
import os
import sys

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
A = os.path.join(ROOT, 'assets')
OUT = os.path.join(ROOT, 'DSH-Studio-2.0-课堂展示.pptx')

# ---------- 设计系统 ----------
BG = RGBColor(0x08, 0x0B, 0x10)
PANEL = RGBColor(0x0F, 0x15, 0x1E)
PANEL2 = RGBColor(0x13, 0x1A, 0x24)
LINE = RGBColor(0x1E, 0x27, 0x32)
TEXT = RGBColor(0xE6, 0xED, 0xF7)
TEXT2 = RGBColor(0x9A, 0xA8, 0xBD)
TEXT3 = RGBColor(0x66, 0x74, 0x8A)
CYAN = RGBColor(0x38, 0xBD, 0xF8)
TEAL = RGBColor(0x5E, 0xEA, 0xD4)
VIOLET = RGBColor(0xA7, 0x8B, 0xFA)
AMBER = RGBColor(0xF5, 0x9E, 0x0B)
PINK = RGBColor(0xF4, 0x72, 0xB6)

FONT = 'Microsoft YaHei'
MONO = 'Consolas'

W, H = 13.333, 7.5


def set_font(run, name=FONT):
    run.font.name = name
    rPr = run._r.get_or_add_rPr()
    for tag in ('a:ea', 'a:cs'):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set('typeface', name)


def tx(slide, x, y, w, h, text, size=16, color=TEXT, bold=False, font=FONT,
       align=PP_ALIGN.LEFT, spacing=1.15, anchor=MSO_ANCHOR.TOP, italic=False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    lines = text.split('\n')
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color
        set_font(r, font)
    return box


def rect(slide, x, y, w, h, fill=PANEL, line=None, radius=None, line_w=1.0):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    s = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        try:
            s.adjustments[0] = radius
        except Exception:
            pass
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(line_w)
    s.shadow.inherit = False
    s.text_frame.word_wrap = True
    return s


def alpha(shape, value):
    """给纯色填充加透明度（0-1）。"""
    try:
        fill = shape.fill._xPr.find(qn('a:solidFill'))
        srgb = fill.find(qn('a:srgbClr'))
        el = srgb.makeelement(qn('a:alpha'), {'val': str(int(value * 100000))})
        srgb.append(el)
    except Exception:
        pass


def pill(slide, x, y, w, h, text, fg=CYAN, size=12, border=None, fill=PANEL2, bold=True):
    s = rect(slide, x, y, w, h, fill=fill, line=border or LINE, radius=0.5)
    tf = s.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = 0
    tf.margin_right = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = fg
    set_font(r)
    return s


def pic_fill(slide, path, x, y, w, h, border=True):
    iw, ih = Image.open(path).size
    src_ratio = iw / ih
    target = w / h
    pic = slide.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))
    if src_ratio > target:
        frac = (1 - target / src_ratio) / 2
        pic.crop_left = frac
        pic.crop_right = frac
    else:
        frac = (1 - src_ratio / target) / 2
        pic.crop_top = frac
        pic.crop_bottom = frac
    if border:
        rect(slide, x, y, w, h, fill=None, line=LINE, line_w=1.0)
    return pic


def new_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = BG
    return slide


def chrome(slide, idx, total):
    """统一页脚 + 顶部细线。"""
    rect(slide, 0, 0, W, 0.05, fill=LINE)
    tx(slide, 0.9, 7.0, 6.0, 0.3, 'DSH Studio 2.0  ·  AI 音乐工作站', 9, TEXT3)
    tx(slide, 11.2, 7.0, 1.2, 0.3, '%02d / %02d' % (idx, total), 9, TEXT3, font=MONO, align=PP_ALIGN.RIGHT)


def kicker(slide, text, color=TEAL):
    tx(slide, 0.9, 0.62, 8.0, 0.3, text, 11.5, color, bold=True)
    rect(slide, 0.9, 0.95, 0.55, 0.045, fill=color)


def title(slide, text, size=34, y=1.15, w=11.5):
    tx(slide, 0.9, y, w, 1.1, text, size, TEXT, bold=True, spacing=1.1)


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


prs = Presentation()
prs.slide_width = Inches(W)
prs.slide_height = Inches(H)

# ============================================================
# S1 封面
# ============================================================
s = new_slide(prs)
# 右侧大图（真实界面）
pic_fill(s, os.path.join(A, 'studio.png'), 6.2, 0, 7.12, 7.5, border=False)
# 左侧压暗渐变遮罩（用半透明矩形模拟）
mask = rect(s, 0, 0, 6.9, 7.5, fill=BG)
alpha(mask, 0.93)
mask2 = rect(s, 6.2, 0, 1.35, 7.5, fill=BG)
alpha(mask2, 0.6)

tx(s, 0.9, 1.55, 6.0, 0.3, '“人工智能 +” 创意作品 · 2026', 11.5, TEAL, bold=True)
tx(s, 0.9, 2.0, 5.9, 1.1, 'DSH STUDIO', 58, TEXT, bold=True, spacing=1.0)
tx(s, 0.9, 2.95, 5.9, 0.7, '2.0', 58, CYAN, bold=True, spacing=1.0, font=MONO)
tx(s, 0.9, 4.0, 6.0, 0.9, '把一个热梗，\n做成一首能蹦的歌。', 27, TEXT, bold=True, spacing=1.35)
tx(s, 0.9, 5.35, 5.8, 0.9,
   'AI 音乐工作站 · 8GB 笔记本跑真实神经网络生成\n产物是音符，不是黑盒音频', 13, TEXT2, spacing=1.5)

pill(s, 0.9, 6.35, 1.75, 0.42, 'Meme → Rave', TEAL, 11)
pill(s, 2.75, 6.35, 1.75, 0.42, '双引擎', CYAN, 11)
pill(s, 4.6, 6.35, 1.9, 0.42, '可编辑工程', VIOLET, 11)
notes(s, '（0:00–0:20）大家好，我们的作品叫 DSH Studio 2.0。它只做一件事：把一个网络热梗，变成一首能蹦的电子乐。'
         '注意，不是一段你改不了的音频，而是一份能逐个音符编辑的工程。')

# ============================================================
# S2 创意来源
# ============================================================
s = new_slide(prs)
kicker(s, '01  ·  创意来源')
title(s, '热梗会传播，但不会变成音乐', 34)

cards = [
    ('梗的生命只有几天', '每天都有新梗，但大多停在了表情包和评论区里，没有变成作品。', AMBER),
    ('做电子乐门槛很高', 'DAW、乐理、音色、混音——四座山，挡住绝大多数想玩的人。', PINK),
    ('AI 音乐是个黑盒', '现在能生成音频，但给你一段波形，你改不了任何一个音。', VIOLET),
]
for i, (head, body, color) in enumerate(cards):
    x = 0.9 + i * 4.02
    rect(s, x, 2.5, 3.78, 2.35, fill=PANEL, line=LINE, radius=0.06)
    rect(s, x, 2.5, 0.05, 2.35, fill=color)
    tx(s, x + 0.32, 2.78, 3.2, 0.4, head, 16, TEXT, bold=True)
    tx(s, x + 0.32, 3.32, 3.15, 1.3, body, 13, TEXT2, spacing=1.55)

tx(s, 0.9, 5.3, 11.5, 0.5, '所以我们的问题不是“能不能生成音乐”，而是——', 14, TEXT3)
tx(s, 0.9, 5.75, 11.6, 0.6, '能不能让一个完全不懂乐理的人，把自己的梗直接变成一首可编辑的歌？', 21, TEAL, bold=True)
notes(s, '（0:20–0:45）为什么做这个？三个观察。第一，梗的传播力很强，但生命周期只有几天，大多数最后停在表情包里。'
         '第二，做电子乐门槛很高：DAW、乐理、音色、混音，四座山。第三，现在 AI 音乐很火，但生成的都是黑盒音频，改不了任何一个音。'
         '所以我们真正想解决的是：让不懂乐理的人，把梗直接变成一首可编辑的歌。')

# ============================================================
# S3 Meme-to-Rave
# ============================================================
s = new_slide(prs)
kicker(s, '02  ·  核心创意', VIOLET)
title(s, 'Meme → Rave：五步把梗变成舞曲', 32)

steps = ['输入热梗', '音乐化解读', '编制与参数', '受约束作曲', 'Drop 段落']
x = 0.9
for i, st in enumerate(steps):
    w = 2.02
    pill(s, x, 2.4, w, 0.62, st, TEXT, 12.5, border=RGBColor(0x2A, 0x36, 0x46))
    if i < len(steps) - 1:
        tx(s, x + w + 0.02, 2.45, 0.28, 0.4, '›', 20, CYAN, bold=True, align=PP_ALIGN.CENTER)
    x += w + 0.3

# 左：真实截图
pic_fill(s, os.path.join(A, 'meme.png'), 0.9, 3.35, 6.05, 3.3)

# 右：例子卡
rect(s, 7.25, 3.35, 5.2, 3.35, fill=PANEL2, line=LINE, radius=0.05)
tx(s, 7.55, 3.55, 4.6, 0.35, '「早八打工人」', 15, AMBER, bold=True)
tx(s, 7.55, 3.95, 4.65, 0.35, 'Techno · 138 BPM · 小调', 12, TEXT2, font=MONO)
tx(s, 7.55, 4.42, 4.65, 1.0,
   '早八的焦虑是重复的、机械的、冷的\n所以是 acid 的十六分滚动——\n就是闹钟的滴答。', 12, TEXT, spacing=1.6)
rect(s, 7.55, 5.55, 4.6, 0.02, fill=LINE)
tx(s, 7.55, 5.7, 4.6, 0.3, 'DROP 大屏', 9, TEXT3, bold=True)
tx(s, 7.55, 5.98, 4.6, 0.4, '06:59 · 再睡五分钟', 17, TEAL, bold=True, font=MONO)
notes(s, '（0:45–1:10）核心创意是 Meme-to-Rave。一句热梗进来：先做音乐化解读，再定编制和参数，然后受约束作曲，最后落在 Drop 段落。'
         '比如「早八打工人」——早八的焦虑是重复的、机械的、冷的，所以是 techno、138 BPM，acid 的十六分滚动就是闹钟的滴答。'
         'Drop 那一刻，大屏打的是「06:59，再睡五分钟」。')

# ============================================================
# S4 真实录屏（GIF，放映时自动播放）
# ============================================================
s = new_slide(prs)
kicker(s, '03  ·  真实录屏', TEAL)
title(s, '20 秒，从一句话到一段音频', 32)

gif = os.path.join(ROOT, '演示视频-20s.gif')
mp4 = os.path.join(ROOT, '演示视频-20s.mp4')
poster = os.path.join(ROOT, '演示视频-封面.png')
if os.path.exists(mp4):
    s.shapes.add_movie(
        mp4, Inches(0.9), Inches(1.95), Inches(8.6), Inches(4.84),
        poster_frame_image=poster if os.path.exists(poster) else None,
        mime_type='video/mp4',
    )
elif os.path.exists(gif):
    s.shapes.add_picture(gif, Inches(0.9), Inches(1.95), Inches(8.6), Inches(4.84))
else:
    pic_fill(s, os.path.join(A, 'studio.png'), 0.9, 1.95, 8.6, 4.84)
rect(s, 0.9, 1.95, 8.6, 4.84, fill=None, line=RGBColor(0x2A, 0x36, 0x46))

# 播放提示（浮在视频右下角，避免压到页脚）
hint = rect(s, 6.35, 6.18, 2.95, 0.34, fill=BG, line=RGBColor(0x2A, 0x36, 0x46), radius=0.5)
alpha(hint, 0.82)
tx(s, 6.35, 6.245, 2.95, 0.26, '▶ 点击画面播放 · 有声音', 9, TEAL, bold=True, align=PP_ALIGN.CENTER)


steps = [
    ('0–4 s', '输入热梗，卡片给出音乐化解读', AMBER),
    ('4–5 s', '模型生成（等待已加速剪辑）', CYAN),
    ('5–18 s', '播放真实生成的音频', TEAL),
    ('18–21 s', '波形与引擎状态，收尾', VIOLET),
]
for i, (t, desc, c) in enumerate(steps):
    y = 1.95 + i * 1.24
    rect(s, 9.75, y, 2.7, 1.06, fill=PANEL, line=LINE, radius=0.1)
    tx(s, 9.93, y + 0.12, 1.6, 0.28, t, 10.5, c, bold=True, font=MONO)
    tx(s, 9.93, y + 0.44, 2.36, 0.55, desc, 8.8, TEXT2, spacing=1.35)
notes(s, '（1:06–1:28 期间播放这段视频，边看边说）这是刚才那些操作的完整实录：输入梗、选卡、生成，十几秒出音频，'
         '然后直接播放——你听到的就是模型生成的原始声音。生成等待我做了加速剪辑，现场不用干等。'
         '放映时点一下画面即可开始播放。')

# ============================================================
# S5 产品展示
# ============================================================
s = new_slide(prs)
kicker(s, '03  ·  产品', CYAN)
title(s, '不是黑盒音频，是能改的音符', 32)
pic_fill(s, os.path.join(A, 'studio.png'), 0.9, 2.15, 8.9, 4.7)

legend = [
    ('① AI Producer', '描述 → 流派 / 调性 / BPM / 密度\n附逐条推理理由', CYAN),
    ('② 五轨时间轴', '鼓组 / 贝斯 / 和声 / 主音 / Riser\n和弦轨与段落带可见', VIOLET),
    ('③ 传输条', '真实波形示波器、总线电平\n小节.拍实时读数', TEAL),
]
for i, (h, b, c) in enumerate(legend):
    y = 2.15 + i * 1.6
    rect(s, 10.0, y, 2.45, 1.45, fill=PANEL, line=LINE, radius=0.08)
    tx(s, 10.18, y + 0.13, 2.1, 0.3, h, 10.5, c, bold=True)
    tx(s, 10.18, y + 0.48, 2.12, 0.9, b, 8.5, TEXT2, spacing=1.4)
notes(s, '（1:10–1:40）这是真实运行的界面。左边五条轨：鼓组、贝斯、和声、主音、Riser。中间是时间轴，和弦轨、段落带、每个音符都在。'
         '右边是 AI Producer，你把描述给它，它返回流派、调性、BPM、密度，还有每一条推断的理由。底部这条波形是真的，从 limiter 之后抽出来的信号。')

# ============================================================
# S5 技术实现
# ============================================================
s = new_slide(prs)
kicker(s, '04  ·  技术实现', AMBER)
title(s, '双引擎：一个给结构，一个给波形', 32)

# 左：符号引擎
rect(s, 0.9, 2.3, 5.65, 3.55, fill=PANEL, line=LINE, radius=0.05)
tx(s, 1.15, 2.5, 5.0, 0.35, '本地符号引擎', 15, CYAN, bold=True)
tx(s, 1.15, 2.86, 5.1, 0.3, '算法作曲 · 毫秒级 · 可编辑 · 可导出 MIDI', 9.5, TEXT3)
pipe = ['自然语言解析', '受约束作曲', '段落编排', '采样 / 合成发声']
y = 3.3
for i, p in enumerate(pipe):
    rect(s, 1.15, y, 4.9, 0.42, fill=PANEL2, line=RGBColor(0x22, 0x2C, 0x3A), radius=0.25)
    tx(s, 1.35, y + 0.09, 4.4, 0.28, '%d. %s' % (i + 1, p), 10.5, TEXT2)
    if i < 3:
        tx(s, 3.5, y + 0.36, 0.4, 0.2, '▼', 7, RGBColor(0x33, 0x42, 0x55), align=PP_ALIGN.CENTER)
    y += 0.63

# 右：ACE-Step
rect(s, 6.85, 2.3, 5.55, 3.55, fill=RGBColor(0x0B, 0x14, 0x1A), line=RGBColor(0x1A, 0x33, 0x40), radius=0.05)
tx(s, 7.1, 2.5, 5.0, 0.35, 'ACE-Step 1.5（本机）', 15, TEAL, bold=True)
tx(s, 7.1, 2.86, 5.1, 0.3, '神经网络音频生成 · 真实 WAV', 9.5, TEXT3)
stats = [
    ('2B Turbo · DiT-only', 'INT8 量化 + CPU offload'),
    ('4.45 GB', '8GB 显卡上的显存峰值'),
    ('10 s', '生成 13 秒音频'),
    ('48 kHz float32', '立体声，真实波形'),
]
yy = 3.3
for big, small in stats:
    tx(s, 7.1, yy, 2.2, 0.32, big, 13, TEXT, bold=True, font=MONO)
    tx(s, 7.1, yy + 0.30, 4.9, 0.25, small, 9.5, TEXT3)
    yy += 0.62

# 底部：适配层 + 音色来源
rect(s, 0.9, 5.95, 11.5, 0.92, fill=PANEL2, line=LINE, radius=0.12)
tx(s, 1.15, 6.05, 3.2, 0.28, '统一后端适配层', 11.5, VIOLET, bold=True)
tx(s, 3.55, 6.06, 8.6, 0.28, '引擎状态实时探测  ·  不可用就如实标注  ·  失败自动回退到符号引擎', 10, TEXT2)
tx(s, 1.15, 6.42, 11.0, 0.28, '本地音色：52 个自制采样（CC0）· 7 套 kit：司凤 Rave / Hardstyle / Techno / EDM / 鬼畜切片 …', 10, TEAL)
notes(s, '（1:40–2:20）技术上我们做了双引擎。左边本地符号引擎：解析、作曲、编排、Web Audio 实时合成，毫秒级，产物是音符，能改能导出 MIDI。'
         '右边 ACE-Step 1.5：2B Turbo、INT8、CPU offload，在这台 8GB 显存的笔记本上，峰值 4.45GB，10 秒生成 13 秒 48kHz 音频。'
         '上面是统一适配层：状态实时探测，不可用就如实标注，失败自动回退——绝不拿符号引擎冒充神经网络。')

# ============================================================
# S6 成果
# ============================================================
s = new_slide(prs)
kicker(s, '05  ·  成果与测试', TEAL)
title(s, '真实跑出来的数字', 32)

bigs = [('4.45 GB', '显存峰值'), ('10 s', '生成 13 秒音频'), ('48 kHz', 'float32 立体声'), ('118 项', '自动化断言')]
for i, (v, k) in enumerate(bigs):
    x = 0.9 + i * 2.95
    tx(s, x, 2.25, 2.7, 0.6, v, 27, TEAL if i % 2 == 0 else CYAN, bold=True, font=MONO)
    tx(s, x, 2.92, 2.7, 0.3, k, 10, TEXT3)

tx(s, 0.9, 3.5, 5.9, 0.3, 'Techno · 128 BPM · 11.87 s', 10.5, TEXT2, bold=True)
tx(s, 6.95, 3.5, 5.5, 0.3, '早八 Rave · 138 BPM · 10.62 s', 10.5, TEXT2, bold=True)
pic_fill(s, os.path.join(A, 'wave-techno.png'), 0.9, 3.85, 5.55, 1.5, border=False)
pic_fill(s, os.path.join(A, 'wave-rave.png'), 6.95, 3.85, 5.45, 1.5, border=False)
rect(s, 0.9, 3.85, 5.55, 1.5, fill=None, line=RGBColor(0x2A, 0x36, 0x46))
rect(s, 6.95, 3.85, 5.45, 1.5, fill=None, line=RGBColor(0x2A, 0x36, 0x46))
tx(s, 0.9, 5.5, 11.5, 0.3, '两条真实 WAV 的波形（非静音占比 93.3% / 98.0%，峰值 −1.00 dBFS）', 9.5, TEXT3)

rect(s, 0.9, 6.0, 11.5, 0.78, fill=PANEL, line=LINE, radius=0.1)
tx(s, 1.15, 6.12, 11.0, 0.28,
   '真实浏览器端到端：点按钮生成 · 数出 576 个音符 · 播放头真的在走 · 音频 readyState=4 且能播放',
   10, TEXT2)
tx(s, 1.15, 6.44, 11.0, 0.28,
   '采样库：52 个自制 one-shot（48kHz/16bit）· 7 套 kit · 鼓组/贝斯/主音/人声切片全部走真实 WAV',
   10, TEAL)
notes(s, '（2:20–2:50）结果是真实可验证的。这是两条模型生成的 WAV 的真实波形：11.87 秒和 10.62 秒，非静音占比 93% 和 98%，峰值 −1 dBFS。'
         '整个项目 118 项自动化断言，包括真实浏览器端到端：点按钮、数音符、验证播放头在走、验证音频真的能解码播放。')

# ============================================================
# S7 创新亮点
# ============================================================
s = new_slide(prs)
kicker(s, '06  ·  创新亮点', PINK)
title(s, '四个不一样', 32)

items = [
    ('热梗娱乐化', '把梗的传播力，变成可创作的素材', AMBER),
    ('双引擎', '算法给结构，模型给波形', CYAN),
    ('不伪装', '音频不可编辑，就在界面上写明白', VIOLET),
    ('可回退', '服务挂了，符号引擎顶上继续演', TEAL),
]
for i, (h, b, c) in enumerate(items):
    x = 0.9 + (i % 2) * 5.9
    y = 2.35 + (i // 2) * 2.2
    rect(s, x, y, 5.55, 1.85, fill=PANEL, line=LINE, radius=0.07)
    rect(s, x, y, 0.05, 1.85, fill=c)
    tx(s, x + 0.4, y + 0.32, 4.8, 0.4, h, 18, TEXT, bold=True)
    tx(s, x + 0.4, y + 0.9, 4.8, 0.6, b, 13, TEXT2, spacing=1.45)
notes(s, '（2:50–2:55，快速带过）四个不一样：把热梗的传播力变成创作力；算法和神经网络双引擎；不伪装，音频不能编辑就写明白；能回退，服务挂了符号引擎照样能演。')

# ============================================================
# S8 结尾
# ============================================================
s = new_slide(prs)
rect(s, 0, 0, W, 0.05, fill=LINE)
# 装饰竖线
rect(s, 0.9, 2.2, 0.06, 3.0, fill=TEAL)
tx(s, 1.35, 2.25, 11.0, 1.0, '模型给波形，', 40, TEXT, bold=True)
tx(s, 1.35, 3.25, 11.0, 1.0, '算法给结构，', 40, CYAN, bold=True)
tx(s, 1.35, 4.25, 11.0, 1.0, '人给判断。', 40, TEAL, bold=True)
tx(s, 1.35, 5.55, 11.0, 0.4, 'DSH Studio 2.0  ·  现场可复现：双击「启动演示.bat」', 12, TEXT2)
pill(s, 1.35, 6.1, 2.3, 0.42, '4.45 GB 显存', TEXT3, 10, border=LINE)
pill(s, 3.8, 6.1, 2.1, 0.42, '10 秒生成', TEXT3, 10, border=LINE)
pill(s, 6.05, 6.1, 2.1, 0.42, '118 项断言', TEXT3, 10, border=LINE)
notes(s, '（2:55–3:00）最后一句话：模型给波形，算法给结构，人给判断。谢谢。')

# 统一页脚（封面只留页码，避免压在截图亮部）
total = len(prs.slides._sldIdLst)
for i, slide in enumerate(prs.slides, start=1):
    if i == 1:
        rect(slide, 0, 0, W, 0.05, fill=LINE)
        tx(slide, 11.2, 7.0, 1.2, 0.3, '01 / %02d' % total, 9, TEXT3, font=MONO, align=PP_ALIGN.RIGHT)
    else:
        chrome(slide, i, total)

prs.save(OUT)
print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB', total, 'slides')

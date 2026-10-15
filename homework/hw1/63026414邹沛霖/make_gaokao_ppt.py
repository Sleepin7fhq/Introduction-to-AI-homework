#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成《2026 新高考一卷压轴题（第 19 题）拆解》5 页演示文稿
运行:  python make_gaokao_ppt.py
输出:  gaokao_yazhou_demo.pptx

题目: 2026 年普通高等学校招生全国统一考试（新课标Ⅰ卷 / 新高考一卷）数学 第 19 题（17 分）
      已知 f(x) 定义域为 R，当 x<0 时 f(x)=2^x；
      对任意 x0∈R，定义 D(x0) = { d∈R | f(x0+d) > f(x0) }。
      (1) 若 x≥0 时 f(x)=1-x，求 D(-1)；
      (2) 若 f 为奇函数，f(x1)≤f(x2) 且 x1x2≠0，证明 D(x2)⊆D(x1)；
      (3) 设 f 满足 ①f(x1)≤f(x2)⟹D(x2)⊆D(x1) ②0<x<1 时 f(x)<f(0)，
          证明：(i) f(0)≥1；(ii) f(x) 在 (0,+∞) 上单调递增。
答案: (1) D(-1)=(0, 3/2)；(2) 由奇函数得 x>0 时 f(x)=-2^(-x)，分类比较集合；
      (3)(i) 反证；(ii) 反证 + 链式推理。
面向对象：没有 AI 基础的大一学生；每页只讲一件事，文字尽量少。
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.oxml.ns import qn

# ---------------------------------------------------------------- 基本参数
CJK = "微软雅黑"          # 中文字体（Windows 自带；Mac 可用「苹方」替换）
LATIN = "Segoe UI"        # 西文字体

NAVY = RGBColor(0x14, 0x2A, 0x4C)     # 深蓝：主文字
BLUE = RGBColor(0x2F, 0x6F, 0xED)     # 亮蓝：主色
BLUE_L = RGBColor(0xE9, 0xF0, 0xFE)   # 浅蓝底
GREEN = RGBColor(0x0E, 0x9F, 0x6E)    # 绿：结论
GREEN_L = RGBColor(0xE6, 0xF7, 0xEF)
AMBER = RGBColor(0xE0, 0x8A, 0x1E)    # 橙：提醒
AMBER_L = RGBColor(0xFD, 0xF3, 0xE3)
RED = RGBColor(0xD1, 0x3A, 0x3A)      # 红：易错 / 最难
RED_L = RGBColor(0xFD, 0xEC, 0xEC)
GRAY = RGBColor(0x5B, 0x6B, 0x84)     # 次要文字
GRAY_L = RGBColor(0xF3, 0xF5, 0xF9)
GRAY_BG = RGBColor(0xF7, 0xF9, 0xFC)  # 卡片浅底
LINE = RGBColor(0xDD, 0xE3, 0xEC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

SW, SH = 13.333, 7.5                  # 16:9 页面（英寸）
MARGIN = 0.85
CONTENT_W = SW - 2 * MARGIN
FOOTER = "2026 新高考一卷（新课标Ⅰ卷）· 第 19 题拆解"

prs = Presentation()
prs.slide_width = Inches(SW)
prs.slide_height = Inches(SH)
BLANK = prs.slide_layouts[6]

SUP, SUB = 30000, -25000              # 上下标基线


# ---------------------------------------------------------------- 工具函数
def set_font(rf, size=14, bold=False, color=NAVY, name_cjk=CJK,
             name_latin=LATIN, baseline=None):
    """设置字体：西文 + 中文（东亚）字体都显式指定，避免中文回退成宋体。"""
    f = rf.font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = color
    f.name = name_latin
    rPr = rf._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", name_cjk)
    if baseline is not None:
        rPr.set("baseline", str(baseline))
    return f


def add_text(slide, x, y, w, h, lines, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, line_spacing=1.2, space_after=4):
    """lines: list[list[dict]] —— 每个 dict 是 (text/size/bold/color/baseline)"""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    for i, runs in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_after = Pt(space_after)
        for spec in runs:
            r = p.add_run()
            r.text = spec.get("text", "")
            set_font(r, size=spec.get("size", 14), bold=spec.get("bold", False),
                     color=spec.get("color", NAVY),
                     name_cjk=spec.get("cjk", CJK), name_latin=spec.get("latin", LATIN),
                     baseline=spec.get("baseline"))
    return box


def add_rect(slide, x, y, w, h, fill=WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE,
             radius=0.08, line=None, line_w=1.0):
    sp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    sp.shadow.inherit = False
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = Pt(line_w)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        sp.adjustments[0] = min(radius, 0.12)   # 圆角过大会挤压文字
    sp.text_frame.word_wrap = True
    return sp


def blank_slide(bg=WHITE):
    s = prs.slides.add_slide(BLANK)
    if bg is not None:
        add_rect(s, 0, 0, SW, SH, fill=bg, shape=MSO_SHAPE.RECTANGLE)
    return s


def page_header(slide, title, subtitle=None, page=None, tag=None):
    """统一页头：小色块 + 标题（+ 副标题 / 右上角标签）+ 页脚"""
    add_rect(slide, MARGIN, 0.52, 0.085, 0.46, fill=BLUE, shape=MSO_SHAPE.RECTANGLE)
    add_text(slide, MARGIN + 0.24, 0.46, 9.6, 0.6,
             [[{"text": title, "size": 27, "bold": True, "color": NAVY}]])
    if subtitle:
        add_text(slide, MARGIN + 0.24, 1.14, 11.2, 0.4,
                 [[{"text": subtitle, "size": 13.5, "color": GRAY}]])
    if tag:
        add_text(slide, SW - MARGIN - 3.6, 0.6, 3.6, 0.35,
                 [[{"text": tag, "size": 11.5, "color": GRAY}]], align=PP_ALIGN.RIGHT)
    if page:
        add_text(slide, SW - MARGIN - 1.2, SH - 0.66, 1.2, 0.3,
                 [[{"text": f"{page} / 5", "size": 10.5, "color": GRAY}]],
                 align=PP_ALIGN.RIGHT)
        add_text(slide, MARGIN, SH - 0.66, 8.4, 0.3,
                 [[{"text": FOOTER, "size": 10.5, "color": GRAY}]])


def badge(slide, x, y, d, text, fill=BLUE, size=14, color=WHITE):
    """圆形序号 / 小标记"""
    sp = add_rect(slide, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL, line=None)
    tf = sp.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    set_font(r, size=size, bold=True, color=color)
    return sp


def strip(slide, y, h, runs, fill=BLUE_L, size=13, align=PP_ALIGN.LEFT):
    """整行提示条（浅色底 + 居中一行字）"""
    add_rect(slide, MARGIN, y, CONTENT_W, h, fill=fill, radius=0.14, line=None)
    pad = 0.34
    add_text(slide, MARGIN + pad, y, CONTENT_W - 2 * pad, h,
             [[dict(s, size=s.get("size", size)) for s in runs]],
             align=align, anchor=MSO_ANCHOR.MIDDLE, space_after=0)


# 数学记号小工具：D(x0) / D(x1) / 2^x / 2^{-x} / 下标
# 注意：只用 Noto Sans SC / 微软雅黑 都覆盖的符号（⇒ ⇔ ⊆ ∈ ≤ ≥ ），
#       长箭头 ⟹ (U+27F9)、⟺ (U+27FA) 会显示成方框，不要用。
def Dx(idx, size, color=NAVY, bold=False):
    return [{"text": "D(x", "size": size, "bold": bold, "color": color},
            {"text": idx, "size": size * 0.72, "baseline": SUB, "bold": bold, "color": color},
            {"text": ")", "size": size, "bold": bold, "color": color}]


def D_(size, color=NAVY, bold=False):
    return Dx("0", size, color, bold)


def pw(size, exp, color=NAVY, bold=False):
    return [{"text": "2", "size": size, "bold": bold, "color": color},
            {"text": exp, "size": size * 0.72, "baseline": SUP, "bold": bold, "color": color}]


def sub(t, size, color=GRAY):
    return {"text": t, "size": size, "baseline": SUB, "color": color}


# ================================================================ 第 1 页：标题页
s1 = blank_slide()
add_rect(s1, 0, 0, SW, 0.16, fill=BLUE, shape=MSO_SHAPE.RECTANGLE)
add_rect(s1, 0, 0.16, SW, 0.06, fill=GREEN, shape=MSO_SHAPE.RECTANGLE)
add_rect(s1, SW - 3.2, SH - 3.2, 4.0, 4.0, fill=BLUE_L, shape=MSO_SHAPE.OVAL, line=None)
add_rect(s1, SW - 1.9, SH - 1.9, 2.3, 2.3, fill=WHITE, shape=MSO_SHAPE.OVAL, line=None)

add_text(s1, MARGIN + 0.1, 1.62, 11.4, 0.4,
         [[{"text": "2026 年高考数学 · 新课标全国Ⅰ卷（新高考一卷）", "size": 13.5,
            "bold": True, "color": BLUE}]])
add_text(s1, MARGIN + 0.1, 2.14, 11.6, 1.2,
         [[{"text": "压轴题第 19 题怎么解", "size": 48, "bold": True, "color": NAVY}]])
add_rect(s1, MARGIN + 0.14, 3.52, 1.5, 0.06, fill=GREEN, shape=MSO_SHAPE.RECTANGLE)
add_text(s1, MARGIN + 0.1, 3.80, 11.2, 0.9,
         [[{"text": "新定义「集合 ", "size": 18.5, "color": GRAY}] + D_(18.5, GRAY) +
           [{"text": "」题：读懂定义，就能动手", "size": 18.5, "color": GRAY}]],
         line_spacing=1.3)
add_text(s1, MARGIN + 0.1, 4.62, 11.2, 0.4,
         [[{"text": "面向零基础大一同学 · 5 页看懂 · 约 10 分钟", "size": 12.5,
            "color": GRAY}]])

# ================================================================ 第 2 页：出题背景
s2 = blank_slide()
page_header(s2, "这道题为什么长这样", "全卷最后一题，17 分，考的不是背过的套路。",
            page=2, tag="背景 · 定位")

stats = [("第 19 题", "全卷最后一题", BLUE),
         ("17 分", "全卷最高分值", NAVY),
         ("4 个小问", "难度层层递进", GREEN),
         ("新定义题", "考场上第一次见", AMBER)]
cy, ch, gap = 1.80, 1.12, 0.30
cw = (CONTENT_W - 3 * gap) / 4
for i, (big, small, col) in enumerate(stats):
    cx = MARGIN + i * (cw + gap)
    add_rect(s2, cx, cy, cw, ch, fill=GRAY_BG, radius=0.10, line=LINE, line_w=1.0)
    add_rect(s2, cx, cy, 0.07, ch, fill=col, shape=MSO_SHAPE.RECTANGLE)
    add_text(s2, cx + 0.32, cy + 0.19, cw - 0.5, 0.45,
             [[{"text": big, "size": 19, "bold": True, "color": col}]])
    add_text(s2, cx + 0.32, cy + 0.70, cw - 0.5, 0.32,
             [[{"text": small, "size": 12, "color": GRAY}]])

bullets = [
    ("为什么这么出", "不考「刷过的题型」，考「现场学会一个新定义」的能力。"),
    ("题型在变", "2024 年考「新定义数列」，2025 年考三角函数，2026 年又回到「新定义」。"),
    ("难度分布", "第 (1)(2) 问很基础，第 (3) 问是全卷最难的一问。"),
]
by, bh = 3.20, 2.10
add_rect(s2, MARGIN, by, CONTENT_W, bh, fill=WHITE, radius=0.10, line=LINE, line_w=1.0)
for i, (head, desc) in enumerate(bullets):
    y = by + 0.30 + i * 0.60
    add_rect(s2, MARGIN + 0.34, y + 0.07, 0.16, 0.16, fill=BLUE, shape=MSO_SHAPE.OVAL)
    add_text(s2, MARGIN + 0.72, y - 0.04, 2.1, 0.4,
             [[{"text": head, "size": 14.5, "bold": True, "color": NAVY}]])
    add_text(s2, MARGIN + 2.90, y - 0.04, CONTENT_W - 3.3, 0.4,
             [[{"text": desc, "size": 13, "color": GRAY}]])

strip(s2, 5.58, 0.80,
      [{"text": "给考场上的你：", "bold": True, "color": GREEN},
       {"text": "先把第 (1)(2) 问稳稳拿到手，再去攻最后一问。", "color": GRAY}],
      fill=GREEN_L)

# ================================================================ 第 3 页：考察知识点
s3 = blank_slide()
page_header(s3, "这道题到底在考什么", "没有超纲知识，考的是「把文字翻译成数学」的能力。",
            page=3, tag="知识点 · 考点")

know = [
    ("集合语言", BLUE,
     [D_(13) + [{"text": " 里装的是「步长 d」，不是 x —— 最容易搞错。", "color": GRAY}]]),
    ("分段函数", GREEN,
     [[{"text": "x<0 用 ", "color": GRAY}] + pw(13, "x") +
      [{"text": "，x≥0 换另一段：必须分类讨论。", "color": GRAY}]]),
    ("指数单调性", AMBER,
     [pw(13, "a") + [{"text": " > ", "color": GRAY}] + pw(13, "b") +
      [{"text": " ⇔ a > b，用来解不等式。", "color": GRAY}]]),
    ("逻辑推理", NAVY,
     [[{"text": "f(x", "color": GRAY}, sub("1", 9.4), {"text": ") ≤ f(x", "color": GRAY},
       sub("2", 9.4), {"text": ") ⇒ ", "color": GRAY}] + Dx("2", 13) +
      [{"text": " ⊆ ", "color": NAVY}] + Dx("1", 13) +
      [{"text": "：正向用、反向用都要会。", "color": GRAY}]]),
]
kw = (CONTENT_W - 0.32) / 2
kh = 1.62
for i, (head, col, lines) in enumerate(know):
    cx = MARGIN + (i % 2) * (kw + 0.32)
    cyy = 1.80 + (i // 2) * (kh + 0.24)
    add_rect(s3, cx, cyy, kw, kh, fill=GRAY_BG, radius=0.10, line=LINE, line_w=1.0)
    add_rect(s3, cx, cyy, 0.07, kh, fill=col, shape=MSO_SHAPE.RECTANGLE)
    add_text(s3, cx + 0.34, cyy + 0.22, kw - 0.6, 0.4,
             [[{"text": head, "size": 16, "bold": True, "color": col}]])
    add_text(s3, cx + 0.34, cyy + 0.78, kw - 0.68, 0.7,
             [[dict(s, size=s.get("size", 12.5)) for s in runs] for runs in lines],
             line_spacing=1.3, space_after=2)

strip(s3, 5.48, 0.90,
      [{"text": "一句话读懂定义：", "bold": True, "color": BLUE},
       {"text": "站定 x", "color": GRAY}, sub("0", 9.4),
       {"text": "，能「往上走」的所有步长 d 组成的集合，就是 ", "color": GRAY}] + D_(13) +
      [{"text": "。", "color": GRAY}],
      fill=BLUE_L)

# ================================================================ 第 4 页：解题步骤（详细版 + 得分点）
s4 = blank_slide()
page_header(s4, "解题步骤与得分点", "四问逐个展开：这一步写什么、分从哪来（分值为参考切分，官方评分细则不公开）。",
            page=4, tag="步骤 · 得分点")

# 每个小问一块：标题（+参考分值）+ 详细步骤 + 得分点
# 分值按「四问共 17 分」标注参考分布，实际以当年官方评分细则为准
def step_line(runs, size=10, color=GRAY):
    return [dict(s, size=s.get("size", size), color=s.get("color", color)) for s in runs]


def tag(text, size=10, color=NAVY, bold=True):
    return {"text": text, "size": size, "color": color, "bold": bold}


SECTIONS = [
    dict(head="第 (1) 问 · 直接算", pts="3 分", color=BLUE, light=BLUE_L, h=1.14,
         steps=[
             step_line([tag("① 求 f(-1)："), {"text": "-1<0 ⇒ f(-1)=2"},
                        {"text": "-1", "size": 7, "baseline": SUP}, {"text": "=1/2。"}]),
             step_line([tag("② d<1 时"), {"text": " -1+d<0，"}] + pw(10, "d-1", GRAY) +
                       [{"text": " > 1/2 ⇒ d>0，得 0<d<1；"}]),
             step_line([tag("③ d≥1 时"), {"text": " -1+d≥0，2-d > 1/2 ⇒ d<3/2，得 1≤d<3/2；"},
                        tag("④ 合并得 "), {"text": "D(-1)=(0,1)∪[1,3/2)="},
                        {"text": "(0,3/2)", "bold": True, "color": GREEN}, {"text": "。"}]),
         ],
         score="得分点 ①算出 f(-1)=1/2　②分 d<1 与 d≥1 两种情况讨论（每种算对得 1 分）　③合并成 (0,3/2)，端点左开右开"),
    dict(head="第 (2) 问 · 用奇函数", pts="4 分", color=GREEN, light=GREEN_L, h=1.14,
         steps=[
             step_line([tag("① 奇函数 ⇒ "), {"text": "x>0 时 f(x)=-f(-x)=-2"},
                        {"text": "-x", "size": 7, "baseline": SUP},
                        {"text": "（题目没给，这一步要自己推）。"}]),
             step_line([tag("② 写出区间：")] + D_(10) +
                       [{"text": " 在 x"}, {"text": "0", "size": 7, "baseline": SUB},
                        {"text": "<0 时为 (0,-x"}, {"text": "0", "size": 7, "baseline": SUB},
                        {"text": ")，x"}, {"text": "0", "size": 7, "baseline": SUB},
                        {"text": ">0 时为 (-∞,-x"}, {"text": "0", "size": 7, "baseline": SUB},
                        {"text": "]∪(0,+∞)。"}]),
             step_line([tag("③ 分类比较："), {"text": "x"}, {"text": "1", "size": 7, "baseline": SUB},
                        {"text": "≤x"}, {"text": "2", "size": 7, "baseline": SUB},
                        {"text": "≤0、0<x"}, {"text": "1", "size": 7, "baseline": SUB},
                        {"text": "≤x"}, {"text": "2", "size": 7, "baseline": SUB},
                        {"text": "、x"}, {"text": "2", "size": 7, "baseline": SUB},
                        {"text": "<0<x"}, {"text": "1", "size": 7, "baseline": SUB},
                        {"text": " 三类，每类都得 D(x"}, {"text": "2", "size": 7, "baseline": SUB},
                        {"text": ")⊆D(x"}, {"text": "1", "size": 7, "baseline": SUB}, {"text": ")。"}]),
         ],
         score="得分点 ①写出 x>0 的表达式得 1 分（写成 x=0 者不得分）　②写出 D 的区间　③三种情况各 1 分　④得 D(x2)⊆D(x1)"),
    dict(head="第 (3) 问 (i) · 反证法", pts="4 分", color=AMBER, light=AMBER_L, h=1.32,
         steps=[
             step_line([tag("① 反设 "), {"text": "f(0)<1；由 p→0"},
                        {"text": "-", "size": 7, "baseline": SUP},
                        {"text": " 时 2"}, {"text": "p", "size": 7, "baseline": SUP},
                        {"text": "→1>f(0)，取 p∈(-1,0) 使 f(p)=2"},
                        {"text": "p", "size": 7, "baseline": SUP}, {"text": ">f(0)。"}]),
             step_line([tag("② 用条件①："), {"text": "取 x"}, {"text": "1", "size": 7, "baseline": SUB},
                        {"text": "=0、x"}, {"text": "2", "size": 7, "baseline": SUB},
                        {"text": "=p，由 f(0)<f(p) 得 D(p)⊆D(0)。"}]),
             step_line([tag("③ 造矛盾："), {"text": "d∈(0,-p) 时 p+d∈(-1,0)，f(p+d)=2"},
                        {"text": "p+d", "size": 7, "baseline": SUP}, {"text": ">2"},
                        {"text": "p", "size": 7, "baseline": SUP},
                        {"text": "=f(p)，故 (0,-p)⊆D(p)⊆D(0)；"}]),
             step_line([{"text": "　　"}, tag("④ 收尾："),
                        {"text": "但 (0,-p)⊂(0,1)，由条件② 得 f(d)<f(0)，即 d∉D(0)，矛盾 ⇒ "},
                        {"text": "f(0)≥1", "bold": True, "color": GREEN}, {"text": "。"}]),
         ],
         score="得分点 ①反设 f(0)<1　②说明存在 p∈(-1,0) 使 2^p>f(0)　③用条件①得 D(p)⊆D(0)　④用条件②导出矛盾并下结论"),
    dict(head="第 (3) 问 (ii) · 链式推理（最难一问）", pts="6 分", color=RED, light=RED_L, h=1.14,
         steps=[
             step_line([tag("① 明确目标："), {"text": "证 0<x"}, {"text": "1", "size": 7, "baseline": SUB},
                        {"text": "<x"}, {"text": "2", "size": 7, "baseline": SUB},
                        {"text": " 时 f(x"}, {"text": "1", "size": 7, "baseline": SUB},
                        {"text": ")<f(x"}, {"text": "2", "size": 7, "baseline": SUB}, {"text": ")。"}]),
             step_line([tag("② 先证符号："), {"text": "先证 x∈(0,1) 时 f(x)≤0，再推广到 x>0 时 f(x)<0。"}]),
             step_line([tag("③ 链式用①："), {"text": "设 0<x"}, {"text": "1", "size": 7, "baseline": SUB},
                        {"text": "<x"}, {"text": "2", "size": 7, "baseline": SUB},
                        {"text": "，把 x"}, {"text": "2", "size": 7, "baseline": SUB},
                        {"text": "-x"}, {"text": "1", "size": 7, "baseline": SUB},
                        {"text": "∈D(x"}, {"text": "1", "size": 7, "baseline": SUB},
                        {"text": ") 链式推出 f(x"}, {"text": "2", "size": 7, "baseline": SUB},
                        {"text": ")>f(x"}, {"text": "1", "size": 7, "baseline": SUB},
                        {"text": ")，即单调递增。"}]),
         ],
         score="得分点 ①写出待证目标　②先证 x>0 时 f(x)<0（关键铺垫）　③链式使用条件①　④得 (0,+∞) 上单调递增"),
]

# 版式：卡片高度按「步骤行数」自动计算，保证得分点条与步骤文字留有间距
LINE_H = 0.186          # 10pt 行高（英寸）
SY, SGAP = 1.58, 0.05   # 起始 y、卡片间距
sy = SY
for sec in SECTIONS:
    n = len(sec["steps"])
    h_text = n * LINE_H                 # 步骤区高度
    hh = 0.29 + h_text + 0.05 + 0.25 + 0.02   # 标题 + 步骤 + 间隔 + 得分点 + 下边距
    col, light = sec["color"], sec["light"]
    add_rect(s4, MARGIN, sy, CONTENT_W, hh, fill=GRAY_BG, radius=0.10, line=LINE, line_w=1.0)
    add_rect(s4, MARGIN, sy, 0.07, hh, fill=col, shape=MSO_SHAPE.RECTANGLE)
    # 小问标题 + 参考分值
    add_text(s4, MARGIN + 0.30, sy + 0.03, 8.0, 0.30,
             [[{"text": sec["head"], "size": 11.5, "bold": True, "color": col}]])
    add_text(s4, SW - MARGIN - 1.3, sy + 0.03, 1.0, 0.30,
             [[{"text": sec["pts"], "size": 10.5, "bold": True, "color": col}]], align=PP_ALIGN.RIGHT)
    # 详细步骤
    add_text(s4, MARGIN + 0.30, sy + 0.29, CONTENT_W - 0.60, h_text,
             sec["steps"], line_spacing=1.08, space_after=0)
    # 得分点（与步骤之间留 0.07 英寸空白）
    sy_score = sy + 0.29 + h_text + 0.05
    add_rect(s4, MARGIN + 0.30, sy_score, CONTENT_W - 0.60, 0.25,
             fill=light, radius=0.16, line=None)
    add_text(s4, MARGIN + 0.42, sy_score, CONTENT_W - 0.84, 0.25,
             [[{"text": sec["score"], "size": 9.5, "color": NAVY}]], anchor=MSO_ANCHOR.MIDDLE)
    sy += hh + SGAP

# ================================================================ 第 5 页：总结
s5 = blank_slide()
page_header(s5, "带走这三句话", "压轴题不可怕：定义读透 → 特例先算 → 逻辑收尾。",
            page=5, tag="总结 · 方法")

takes = [
    ("读懂定义", BLUE,
     ["新定义题的第一步永远是：", "把没见过的符号，", "翻译成一句人话。"]),
    ("先易后难", GREEN,
     ["第 (1)(2) 问套公式就能拿分，", "先把它们做稳，", "再去啃最后一问。"]),
    ("逻辑取胜", AMBER,
     ["包含关系靠反证 + 链式推理，", "不靠灵感，", "靠的是把条件用满。"]),
]
tw = (CONTENT_W - 2 * 0.32) / 3
for i, (head, col, lines) in enumerate(takes):
    tx = MARGIN + i * (tw + 0.32)
    add_rect(s5, tx, 1.85, tw, 2.50, fill=GRAY_BG, radius=0.10, line=LINE, line_w=1.0)
    badge(s5, tx + 0.34, 2.10, 0.56, str(i + 1), fill=col, size=16)
    add_text(s5, tx + 1.05, 2.18, tw - 1.3, 0.45,
             [[{"text": head, "size": 17, "bold": True, "color": NAVY}]])
    add_text(s5, tx + 0.34, 3.00, tw - 0.68, 1.2,
             [[{"text": t, "size": 12.5, "color": GRAY}] for t in lines],
             line_spacing=1.3, space_after=2)

strip(s5, 4.58, 1.00,
      [{"text": "给大一同学：", "bold": True, "color": BLUE},
       {"text": "「定义 → 特例 → 证明」这套流程，读论文、写代码一样好用；", "color": GRAY},
       {"text": "先用自己思路走一遍，再让 AI 帮你逐步检查。", "color": GRAY}],
      fill=BLUE_L)
add_text(s5, MARGIN, 5.86, CONTENT_W, 0.4,
         [[{"text": "压轴题不是天才题，是流程题。", "size": 15, "bold": True, "color": NAVY}]],
         align=PP_ALIGN.CENTER)

# ---------------------------------------------------------------- 备注（讲稿，不占版面）
NOTES = {
    1: """开场（约 1 分钟）
主题：2026 年高考数学新课标Ⅰ卷（新高考一卷）第 19 题，全卷压轴，17 分。
听众定位：没有 AI 基础的大一同学——不需要竞赛基础，只需要高中函数知识。
今天不追求把最后一问讲透，而是把「新定义题」的通用读法讲清楚。""",

    2: """背景补充（约 2 分钟）
1) 卷面结构：新课标Ⅰ卷共 19 题 150 分，第 19 题是解答题最后一题，17 分，为全卷最高分值。
2) 题型趋势：2024 年第 19 题是「新定义数列（可分数列）」，2025 年是三角函数题
   f(x)=5cos x-cos5x，2026 年又回到「新定义」——新定义集合 D(x0) + 函数性质。
   结论：题型不固定，靠背套路没用，考的是现场读懂一个新定义的能力。
3) 难度分布：第 (1)(2) 问属于基础题（(1) 只要会解不等式，(2) 只要会用奇函数），
   第 (3) 问是全卷最难的一问；对大多数同学来说，把 (1)(2) 拿稳就是胜利。
题干与答案已用 6 个独立来源交叉核对（良师宝题库、数学345、21世纪教育网解析、
网易·数海漫游、中国教育在线、CNKI 期刊摘要），并用程序做了数值验证。""",

    3: """知识点讲解要点（约 3 分钟）
1) 集合语言：D(x0)={d | f(x0+d)>f(x0)} 里装的是「步长 d」，不是 x。
   这是本题最大的坑——把 d 当成 x 会全盘跑偏。
2) 分段函数：题设只给了 x<0 时 f(x)=2^x，其余部分由每个小问自己补。
   (1) 补 x≥0 时 f(x)=1-x；(2) 补「f 是奇函数」；(3) 只给抽象条件 ①②。
3) 指数函数单调性：2^a>2^b ⇔ a>b，这是 (1) 解不等式的唯一工具。
4) 逻辑推理：条件 ①「f(x1)≤f(x2) ⇒ D(x2)⊆D(x1)」既是正向条件，也是
   「函数值越小、集合越大」的直观；(3) 里要反复正用、逆用、链式使用。
5) 直观理解：D(x0) 就是「从 x0 出发，能让函数值变大的所有步长」的集合。""",

    4: """【原题】2026 年普通高等学校招生全国统一考试（新课标Ⅰ卷）数学 第 19 题（17 分）
已知函数 f(x) 的定义域为 R，且当 x<0 时，f(x)=2^x。
对任意 x0∈R，定义集合 D(x0)={d∈R | f(x0+d)>f(x0)}。
（1）若当 x≥0 时，f(x)=1-x，求 D(-1)；
（2）若 f(x) 是奇函数，f(x1)≤f(x2)，且 x1x2≠0，证明：D(x2)⊆D(x1)；
（3）设 f(x) 满足：①若 f(x1)≤f(x2)，则 D(x2)⊆D(x1)；②当 0<x<1 时，f(x)<f(0)。
     （i）证明：f(0)≥1；（ii）证明：f(x) 在区间 (0,+∞) 单调递增。

【(1) 详解】f(-1)=2^(-1)=1/2。
  当 d<1 时 -1+d<0，f(-1+d)=2^(d-1)>1/2 ⇔ d-1>-1 ⇔ d>0，得 0<d<1；
  当 d≥1 时 -1+d≥0，f(-1+d)=1-(-1+d)=2-d>1/2 ⇔ d<3/2，得 1≤d<3/2。
  合并：D(-1)=(0,1)∪[1,3/2)=(0,3/2)。

【(2) 要点】奇函数给出 x>0 时 f(x)=-2^(-x)。于是
  x0<0 时 D(x0)=(0,-x0)；x0>0 时 D(x0)=(-∞,-x0]∪(0,+∞)。
  再按 x1≤x2≤0、0<x1≤x2、x2<0<x1 三类比较左右端点，即得 D(x2)⊆D(x1)。
  注意：f(x)=-2^(-x) 是推出来的，不是题设给的——这一步不能省。

【(3)(i) 要点】反证法。设 f(0)<1。
  因为 p 从左侧趋于 0 时 2^p→1>f(0)，可取 p∈(-1,0) 使 f(p)=2^p>f(0)；
  由 ①（取 x1=0, x2=p）得 D(p)⊆D(0)。
  又对任意 d∈(0,-p)：p+d∈(p,0)⊂(-1,0)，f(p+d)=2^(p+d)>2^p=f(p)，故 (0,-p)⊆D(p)。
  于是 (0,-p)⊆D(0)；但 (0,-p)⊂(0,1)，由 ② 得 f(d)<f(0)，即 d∉D(0)，矛盾。
  故 f(0)≥1。

【(3)(ii) 思路】三步：先证 x∈(0,1) 时 f(x)≤0；再推广到 x>0 时 f(x)<0；
  最后设 0<x1<x2，用 ① 做链式推理，把 x2-x1∈D(x1) 导出 f(x2)>f(x1)，
  即 f 在 (0,+∞) 上单调递增。这一问是全卷最难，考场上写不完很正常。

【关于分值的重要说明——讲课时请务必说明】
  官方评分细则不公开：政策上「根据评分参考制定的评分细则按国家秘密级事项管理」，
  省考试院只发布参考答案。网上流传两种互相矛盾的切分：
    · 网传阅卷评分细则：3 + 4 + 4 + 6 = 17（本页采用这一种）
    · 21世纪教育网机构估分：4 + 5 + 4 + 4 = 17
  两者不可同时成立，均非官方，无法确证，只能作为「分从哪来」的参考。
  网传细则中第 (1)(2) 问的踩分点较具体：
    (1) 分类讨论，每种情况计算正确分别得 1 分；不分类、直接由图像得出结论也不扣分；
    (2) 正确写出表达式可得 1 分，但写出 x=0 者不得分；三种情况各 1 分；
    (3) 阅卷严格：用教材外方法而不加证明、画图说明、举例说明者一律扣分；
        并称「不使用反证法一律不得分」（此条来自泄漏件，仅供提醒，不可当作定论）。
  第 (3) 问细则未细分到行的给分点，本页 ①②③④ 是按数学逻辑整理的踩分点。""",

    5: """总结（约 2 分钟）
三句话：读懂定义 → 先易后难 → 逻辑取胜。
给大一同学的延伸：这套「定义 → 特例 → 证明」的流程，读论文、写代码、做实验都一样适用。
和 AI 协作的姿势：先用自己的思路走一遍，再让 AI 逐步检查每一步推导——
能自己讲清每一步，才是真的学会了。

课堂互动建议：现场让同学用一句话复述 D(x0) 的含义；
再让同学算第 (1) 问那支函数在 x0=0 处的 D(0)。
答案：D(0)=∅——因为 f(0)=1 已是「最高点」，任何方向都上不去。
这个例子最能说明「D(x0) 大 = 该点函数值还很低」，值得现场点一下。""",
}

for idx, slide in enumerate(prs.slides, 1):
    if idx in NOTES:
        slide.notes_slide.notes_text_frame.text = NOTES[idx]

# ---------------------------------------------------------------- 保存
prs.save("gaokao_yazhou_demo.pptx")
print(f"已生成 gaokao_yazhou_demo.pptx，共 {len(prs.slides)} 页")

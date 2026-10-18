# -*- coding: utf-8 -*-
"""Streamlined 8-slide deck for 2026 Shanghai Gaokao Problem 21."""
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from lxml import etree

INK   = RGBColor(0x14, 0x21, 0x3D)
SOFT  = RGBColor(0x3A, 0x44, 0x55)
PAPER = RGBColor(0xF8, 0xF5, 0xED)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CORAL = RGBColor(0xC8, 0x55, 0x3D)
TEAL  = RGBColor(0x2F, 0x6B, 0x63)
GOLD  = RGBColor(0xB8, 0x8A, 0x2E)
MUTED = RGBColor(0x74, 0x6F, 0x65)
LINE  = RGBColor(0xD9, 0xD1, 0xC2)
CREAM = RGBColor(0xEF, 0xE7, 0xD7)

SERIF = "Noto Serif SC"
SANS  = "Noto Sans SC"
MATH  = "Cambria Math"

SW, SH = 13.333, 7.5
ML, MR = 0.75, 12.58
CW = MR - ML

prs = Presentation()
prs.slide_width = Inches(SW)
prs.slide_height = Inches(SH)
BLANK = prs.slide_layouts[6]


def set_bg(slide, color=PAPER):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, x, y, w, h, fill=None, line=None, lw=0.75, shape=MSO_SHAPE.RECTANGLE):
    shp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.shadow.inherit = False
    style = shp._element.find(qn('p:style'))
    if style is not None:
        shp._element.remove(style)
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(lw)
    return shp


def _font(run, size, color, bold=False, math=False, serif=False):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = color
    latin = MATH if math else (SERIF if serif else SANS)
    f.name = latin
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn('a:ea'))
    if ea is None:
        ea = etree.SubElement(rPr, qn('a:ea'))
    ea.set('typeface', latin)


def _runs(p, text, size, color, bold=False, serif=False):
    for a, b in [
        (r'\frac{1}{2}', '½'), (r'\frac{1}{4}', '¼'),
        (r'\frac{3}{4}', '¾'), (r'\frac34', '¾'),
        (r'\frac12', '½'), (r'\frac14', '¼'),
        (r'\Leftrightarrow', '⇔'), (r'\Rightarrow', '⇒'),
        (r'\infty', '∞'), (r'\Delta', 'Δ'),
        (r'\le', '≤'), (r'\ge', '≥'), (r'\ne', '≠'),
        (r'\in', '∈'), (r'\to', '→'),
        (r'\cosh', 'cosh'), (r'\min', 'min'),
        (r'\qquad', '    '), (r'\quad', '  '), (r'\ ', ' '),
        (r'\{', '{'), (r'\}', '}'),
    ]:
        text = text.replace(a, b)
    i = 0
    in_math = False
    buf = []
    def flush():
        nonlocal buf
        if not buf:
            return
        r = p.add_run()
        r.text = ''.join(buf)
        _font(r, size, color, bold=bold, math=in_math, serif=serif)
        buf = []
    sup = {'2': '²', '3': '³', '-1': '⁻¹', '-x': '⁻ˣ', '-a': '⁻ᵃ', '+': '⁺'}
    while i < len(text):
        ch = text[i]
        if ch == '$':
            flush()
            in_math = not in_math
            i += 1
            continue
        if in_math and ch in '_^':
            flush()
            kind = ch
            i += 1
            if i < len(text) and text[i] == '{':
                j = text.find('}', i)
                content = text[i + 1:j] if j != -1 else text[i + 1:]
                i = j + 1 if j != -1 else len(text)
            else:
                content = text[i] if i < len(text) else ''
                i += 1
            r = p.add_run()
            if kind == '^' and content in sup:
                r.text = sup[content]
                _font(r, size * (0.9 if content in ('2', '3') else 0.78), color, bold=bold, math=True, serif=serif)
            else:
                r.text = content
                _font(r, size * 0.66, color, bold=bold, math=True, serif=serif)
                r._r.get_or_add_rPr().set('baseline', '-25000' if kind == '_' else '30000')
            continue
        buf.append(ch)
        i += 1
    flush()


def text(slide, x, y, w, h, content, size=15, color=SOFT, bold=False, serif=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, ls=1.25, sa=0):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for idx, para in enumerate(content.split('\n')):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = ls
        p.space_before = Pt(0)
        p.space_after = Pt(sa)
        _runs(p, para, size, color, bold=bold, serif=serif)
    return tb


def header(slide, kicker, title, n, accent=CORAL):
    add_rect(slide, ML, 0.50, 0.50, 0.035, fill=accent)
    text(slide, ML, 0.62, CW, 0.28, kicker, size=9, color=accent, bold=True)
    text(slide, ML, 0.92, CW, 0.55, title, size=26, color=INK, bold=True, serif=True)
    add_rect(slide, ML, 1.55, CW, 0.012, fill=LINE)
    text(slide, MR - 0.9, 7.14, 0.9, 0.24, f"{n:02d} / 07", size=8.5, color=MUTED, align=PP_ALIGN.RIGHT)
    text(slide, ML, 7.14, 6.0, 0.24, "2026 上海高考数学 · 第 21 题", size=8.5, color=MUTED)


def slide(kicker, title, n, accent=CORAL):
    s = prs.slides.add_slide(BLANK)
    set_bg(s)
    header(s, kicker, title, n, accent)
    return s


def num(n, color=CORAL, x=ML, y=1.78, d=0.42):
    add_rect(s, x, y, d, d, fill=color, shape=MSO_SHAPE.OVAL)
    text(s, x, y, d, d, str(n), size=12, color=WHITE, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


# ---------------------------------------------------------------- cover
s = prs.slides.add_slide(BLANK)
set_bg(s)
text(s, ML, 0.85, 8.0, 0.3, "2026 · 上海高考数学 · 第 21 题", size=11, color=CORAL, bold=True)
add_rect(s, ML, 1.25, 1.5, 0.035, fill=CORAL)
text(s, ML, 1.55, 8.6, 1.55, "函数序关系\n与 I 排列", size=44, color=INK, bold=True, serif=True, ls=1.08)
text(s, ML, 3.20, 8.0, 0.4, "解题过程与答案 · 精简版", size=19, color=SOFT, serif=True)
add_rect(s, ML, 3.85, 6.2, 0.012, fill=LINE)
text(s, ML, 4.10, 8.4, 0.8,
     "把定义翻译成 3 个开关，用计数公式处理前两问，\n再用单调性控制开关完成存在性证明。",
     size=14, color=SOFT, ls=1.45)
text(s, ML, 5.55, 8.6, 0.35, "$n_{I}=1+A+AB+C+BC+B$", size=20, color=INK)
text(s, ML, 6.05, 8.6, 0.35,
     "$A=[f_{1}\\le f_{2}]$   $B=[f_{1}\\le f_{3}]$   $C=[f_{2}\\le f_{3}]$",
     size=11, color=MUTED)
# light numeral
text(s, 9.55, 1.15, 3.5, 5.4, "21", size=230, color=RGBColor(0xEB, 0xE3, 0xD4), bold=True,
     serif=True, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
text(s, ML, 6.95, 7.0, 0.25, "2026 SHANGHAI · PROBLEM 21", size=8.5, color=MUTED)


# ---------------------------------------------------------------- statement
s = slide("题目", "题目原文：定义与三问", 2)
add_rect(s, ML, 1.72, CW, 1.78, fill=WHITE)
add_rect(s, ML, 1.72, 0.06, 1.78, fill=CORAL)
text(s, ML + 0.24, 1.82, 0.8, 0.25, "定义", size=9, color=CORAL, bold=True)
text(s, ML + 0.24, 2.10, CW - 0.45, 1.30,
     "已知 $(i,j,k)$ 是 $1,2,3$ 的排列。若对任意 $x\\in I$，都有\n"
     "$f_{1}(x)\\le f_{i}(x)$ 且 $f_{1}(x)+f_{2}(x)\\le f_{i}(x)+f_{j}(x)$，\n"
     "则称 $(i,j,k)$ 为 $I$ 排列，总数记为 $n_{I}$。",
     size=14, color=INK, ls=1.42)

text(s, ML, 3.78, 0.80, 0.3, "（1）", size=13.5, color=CORAL, bold=True, serif=True)
text(s, ML + 0.85, 3.75, 5.25, 1.0,
     "$I=[3,+\\infty)$，$f_{1}=x$，$f_{2}=0$，$f_{3}=x^{2}+1$，\n判断 $(3,1,2)$ 是否为 $I$ 排列。",
     size=13, color=SOFT, ls=1.35)
text(s, 6.75, 3.78, 0.80, 0.3, "（2）", size=13.5, color=TEAL, bold=True, serif=True)
text(s, 7.60, 3.75, 4.85, 1.0,
     "$I=(0,+\\infty)$，$f_{1}=x-1$，$f_{2}=x+m$，$f_{3}=x^{2}$，\n若 $n_{I}=6$，求 $m$ 的取值范围。",
     size=13, color=SOFT, ls=1.35)
add_rect(s, ML, 4.95, CW, 0.01, fill=LINE)
text(s, ML, 5.12, 0.80, 0.3, "（3）", size=13.5, color=GOLD, bold=True, serif=True)
text(s, ML + 0.85, 5.09, CW - 0.9, 1.35,
     "对 $x\\in[0,+\\infty)$，$0<F(x)<1$。令 $I=[a,+\\infty)$，$a>0$，\n"
     "$f_{1}=F(x)$，$f_{2}=\\frac{1}{2}[F(x+a)+F(x-a)]$，$f_{3}=1-e^{-x}$。\n"
     "证明：$F$ 严格减时，存在 $a>0$ 使 $n_{I}\\ge 4$；$F$ 严格增时，存在 $a\\in(0,1)$ 使 $n_{I}\\ne 2$。",
     size=13, color=SOFT, ls=1.42)
text(s, ML, 6.25, CW, 0.3,
     "路线：定义 → 6 个排列 → 3 个开关 → 计数 → 用单调性控制开关",
     size=10, color=MUTED, align=PP_ALIGN.CENTER)


# ---------------------------------------------------------------- decode
s = slide("核心工具", "第一步：把定义拆成 6 个排列", 3, accent=GOLD)
rows = [
    ("排列", "等价条件"),
    ("(1,2,3)", "恒成立"),
    ("(1,3,2)", "$f_{2}\\le f_{3}$"),
    ("(2,1,3)", "$f_{1}\\le f_{2}$"),
    ("(2,3,1)", "$f_{1}\\le f_{2}$ 且 $f_{1}\\le f_{3}$"),
    ("(3,1,2)", "$f_{1}\\le f_{3}$ 且 $f_{2}\\le f_{3}$"),
    ("(3,2,1)", "$f_{1}\\le f_{3}$"),
]
tx, ty, tw = ML, 1.75, 7.35
rh = 0.48
add_rect(s, tx, ty, tw, rh, fill=INK)
text(s, tx + 0.16, ty, 2.0, rh, "排列 $(i,j,k)$", size=11, color=WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
text(s, tx + 2.1, ty, 4.9, rh, "等价条件", size=11, color=WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
for i, (a, b) in enumerate(rows[1:]):
    yy = ty + rh + i * rh
    if i % 2 == 0:
        add_rect(s, tx, yy, tw, rh, fill=WHITE)
    add_rect(s, tx, yy + rh - 0.008, tw, 0.008, fill=LINE)
    text(s, tx + 0.16, yy, 1.85, rh, a, size=13, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, tx + 2.1, yy, 4.9, rh, b, size=13, color=SOFT, anchor=MSO_ANCHOR.MIDDLE)

# formula panel
px, py, pw = 8.45, 1.75, 4.12
add_rect(s, px, py, pw, 3.55, fill=INK)
text(s, px + 0.25, py + 0.20, pw - 0.45, 0.25, "计数公式", size=9, color=GOLD, bold=True)
text(s, px + 0.25, py + 0.58, pw - 0.45, 0.85,
     "$A=[f_{1}\\le f_{2}]$\n$B=[f_{1}\\le f_{3}]$\n$C=[f_{2}\\le f_{3}]$",
     size=11, color=RGBColor(0xDD, 0xD5, 0xC6), ls=1.45)
add_rect(s, px + 0.25, py + 1.55, pw - 0.50, 0.01, fill=RGBColor(0x4A, 0x5A, 0x72))
text(s, px + 0.25, py + 1.75, pw - 0.45, 0.55, "$n_{I}=1+A+AB+C+BC+B$", size=17, color=WHITE)
text(s, px + 0.25, py + 2.55, pw - 0.45, 0.7,
     "$n_{I}=6\\Leftrightarrow A=B=C=1$\n$n_{I}\\ge 4$：$B=C=1$ 或 $A=B=1$",
     size=9.5, color=GOLD, ls=1.35)
text(s, px + 0.25, py + 3.22, pw - 0.45, 0.22,
     "记 $[P]=1$ 若 $P$ 真，否则为 $0$。", size=8, color=RGBColor(0xB8, 0xC2, 0xD0))
text(s, ML, 5.68, CW, 0.55,
     "例：$(3,1,2)$ 需 $f_{1}\\le f_{3}$ 且 $f_{2}\\le f_{3}$；$k$ 不参与不等式，只需看 $(i,j)$。",
     size=11, color=MUTED)


# ---------------------------------------------------------------- (1)(2)
s = slide("第 (1)(2) 问", "直接验证与参数范围", 4, accent=TEAL)
# left
text(s, ML, 1.72, 5.7, 0.3, "（1）判断 $(3,1,2)$", size=14, color=CORAL, bold=True, serif=True)
text(s, ML, 2.12, 5.6, 1.35,
     "$f_{1}\\le f_{3}$：$x\\le x^{2}+1$\n"
     "$\\Leftrightarrow (x-\\frac12)^{2}+\\frac34>0$，恒成立；\n"
     "$f_{2}\\le f_{3}$：$0\\le x^{2}+1$，恒成立。",
     size=12.5, color=SOFT, ls=1.38)
text(s, ML, 3.55, 5.6, 0.35, "所以 $(3,1,2)$ 是 $I$ 排列。", size=15, color=TEAL, bold=True)
add_rect(s, ML, 4.10, 5.35, 0.01, fill=LINE)
text(s, ML, 4.28, 5.7, 0.3, "（2）$n_{I}=6$ 的情形", size=14, color=TEAL, bold=True, serif=True)
text(s, ML, 4.68, 5.6, 1.8,
     "$n_{I}=6\\Leftrightarrow A=B=C=1$。\n"
     "$A$：$m\\ge -1$；\n"
     "$B$：$x-1\\le x^{2}$，恒成立；\n"
     "$C$：$m\\le x^{2}-x$ 恒成立 $\\Leftrightarrow m\\le-\\frac14$。",
     size=12.3, color=SOFT, ls=1.38)
# right answer block
add_rect(s, 6.55, 1.72, 0.01, 4.95, fill=LINE)
text(s, 7.00, 1.80, 5.3, 0.3, "答案", size=9, color=GOLD, bold=True)
text(s, 6.95, 2.12, 5.5, 0.75, "$m\\in[-1,-\\frac14]$", size=28, color=INK, bold=True)
text(s, 7.00, 2.95, 5.2, 0.35, "闭区间：两个端点都取得到", size=10.5, color=MUTED)
text(s, 7.00, 3.65, 5.2, 1.8,
     "端点检验：\n"
     "$m=-1$：$A$ 取等号，其余成立；\n"
     "$m=-\\frac14$：$C$ 在 $x=\\frac12$ 取等号，其余成立。",
     size=11.5, color=SOFT, ls=1.45)
text(s, 7.00, 5.55, 5.2, 0.9,
     "记忆：上界来自 $f_{2}\\le f_{3}$，\n下界来自 $f_{1}\\le f_{2}$。",
     size=10.5, color=MUTED, ls=1.4)


# ---------------------------------------------------------------- decreasing
s = slide("第 (3) 问①", "$F$ 严格递减：让 $f_{3}$ 主导", 5, accent=CORAL)
steps = [
    ("1", "设 $L$ 为 $F(x)$ 当 $x\\to+\\infty$ 时的极限，则 $L\\le F(0)<1$。"),
    ("2", "取 $a>0$ 充分大，使\n$F(a)+e^{-a}<1$，$\\frac12[F(0)+F(a)]+e^{-a}<1$。"),
    ("3", "对 $x\\ge a$：\n$f_{1}(x)\\le F(a)<1-e^{-a}\\le f_{3}(x)$；\n$f_{2}(x)\\le\\frac12[F(a)+F(0)]<1-e^{-a}\\le f_{3}(x)$。"),
    ("4", "故 $B=C=1$，$n_{I}=4+2A\\ge 4$。"),
]
ys = [1.75, 2.38, 3.30, 4.45]
for (n, body), yy in zip(steps, ys):
    num(n, CORAL, x=ML, y=yy)
    if n == "3":
        add_rect(s, ML + 0.65, yy - 0.02, CW - 0.65, 1.05, fill=WHITE)
        text(s, ML + 0.85, yy + 0.08, CW - 1.0, 0.95, body, size=12.5, color=SOFT, ls=1.45)
    else:
        text(s, ML + 0.65, yy - 0.02, CW - 0.75, 0.9, body, size=12.5, color=SOFT, ls=1.35)
add_rect(s, ML, 5.55, CW, 0.58, fill=CORAL)
text(s, ML + 0.25, 5.55, CW - 0.5, 0.58, "$n_{I}=4+2A\\ge 4$，所以存在 $a>0$ 满足要求。",
     size=14, color=WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
text(s, ML, 6.38, CW, 0.45,
     "关键：$a\\to+\\infty$ 时，两式左边分别趋于 $L$ 与 $\\frac12[F(0)+L]$，都小于 1。",
     size=9.5, color=MUTED, ls=1.3)


# ---------------------------------------------------------------- increasing
s = slide("第 (3) 问②", "$F$ 严格递增：先证 $A=0$，再分情形", 6, accent=TEAL)
add_rect(s, ML, 1.70, CW, 1.05, fill=WHITE)
text(s, ML + 0.22, 1.78, CW - 0.45, 0.3, "引理", size=9, color=TEAL, bold=True)
text(s, ML + 0.22, 2.04, CW - 0.45, 0.65,
     "若 $f_{1}\\le f_{2}$ 在 $[a,+\\infty)$ 上恒成立，令 $u_{n}=F((n+1)a)$，则 $2u_{n}\\le u_{n-1}+u_{n+1}$。\n"
     "差 $d_{n}=u_{n+1}-u_{n}$ 不减，$d_{0}>0$，故 $u_{n}\\to+\\infty$，与 $u_{n}<1$ 矛盾。所以 $A=0$。",
     size=10.5, color=SOFT, ls=1.35)
# case 1
text(s, ML, 3.00, 5.7, 0.3, "情形 1：存在 $x_{0}>0$ 使 $F(x_{0})>f_{3}(x_{0})$", size=12, color=CORAL, bold=True)
text(s, ML, 3.38, 5.6, 1.9,
     "取 $x_{0}$ 为连续点，令 $a\\to0^{+}$，则\n"
     "$f_{2}(x_{0})\\to F(x_{0})>f_{3}(x_{0})$。\n"
     "取 $0<a<\\min\\{1,x_{0}\\}$ 充分小，则\n"
     "$B=C=0$。又 $A=0$，所以 $n_{I}=1$。",
     size=11.5, color=SOFT, ls=1.42)
# case 2
text(s, 6.55, 3.00, 5.2, 0.3, "情形 2：$F(x)\\le f_{3}(x)$ 恒成立", size=12, color=TEAL, bold=True)
text(s, 6.55, 3.38, 5.3, 1.9,
     "此时 $B=1$。对 $x\\ge a$，\n"
     "$f_{2}(x)\\le\\frac12[f_{3}(x+a)+f_{3}(x-a)]$\n"
     "$=1-e^{-x}\\cosh a<f_{3}(x)$，\n"
     "故 $C=1$，$n_{I}=4+2A\\ge 4$。",
     size=11.5, color=SOFT, ls=1.42)
add_rect(s, ML, 5.22, CW, 0.58, fill=TEAL)
text(s, ML + 0.25, 5.22, CW - 0.5, 0.58, "两种情形都有 $n_{I}\\ne 2$，所以②得证。",
     size=14, color=WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
text(s, ML, 6.05, CW, 0.5,
     "注：单调函数的连续点稠密；若 $x_{0}$ 为间断点，在其右侧附近仍保持 $F>f_{3}$，取其中的连续点即可。",
     size=9, color=MUTED, ls=1.3)


# ---------------------------------------------------------------- summary
s = slide("总结", "答案与方法", 7, accent=GOLD)
answers = [
    ("（1）", "是 $I$ 排列"),
    ("（2）", "$m\\in[-1,\\ -\\frac14]$"),
    ("（3）①", "存在 $a>0$，$n_{I}\\ge 4$"),
    ("（3）②", "存在 $a\\in(0,1)$，$n_{I}\\ne 2$"),
]
for i, (lab, val) in enumerate(answers):
    yy = 1.78 + i * 0.82
    add_rect(s, ML, yy, 0.05, 0.55, fill=CORAL if i < 2 else TEAL)
    text(s, ML + 0.20, yy, 1.1, 0.3, lab, size=10, color=MUTED)
    text(s, ML + 1.25, yy - 0.05, 5.5, 0.5, val, size=16, color=INK, bold=True)
add_rect(s, 7.00, 1.72, 0.01, 3.35, fill=LINE)
text(s, 7.35, 1.78, 5.0, 0.3, "三个关键词", size=9, color=GOLD, bold=True)
text(s, 7.35, 2.15, 5.0, 3.5,
     "翻译：6 个排列 → 3 个开关 $A,B,C$。\n\n"
     "计数：$n_{I}=1+A+AB+C+BC+B$；\n$n_{I}=6$ 要全开。\n\n"
     "控制：递减取大 $a$，让 $f_{3}$ 主导；\n递增先证 $A=0$，再用小 $a$ 或 $B=C=1$ 分类。",
     size=12, color=SOFT, ls=1.45)
text(s, ML, 5.35, CW, 0.8,
     "新定义题的通用路径：先翻译，再计数，最后用单调性控制关键开关。",
     size=15, color=INK, serif=True, align=PP_ALIGN.CENTER)
text(s, ML, 6.45, CW, 0.3, "2026 上海高考数学 · 第 21 题 · 解析完", size=9, color=MUTED,
     align=PP_ALIGN.CENTER)


prs.core_properties.title = "2026上海高考数学第21题解析（精简版）"
prs.core_properties.author = "DeepSeek Harness"
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "2026上海高考数学21题解析_精简版.pptx")
prs.save(out)
print(out, len(prs.slides._sldIdLst))

# -*- coding: utf-8 -*-
"""Build the 2026 Shanghai Gaokao Problem 21 solution deck."""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from lxml import etree

# ---------- palette ----------
INK      = RGBColor(0x14, 0x21, 0x3D)
INK_SOFT = RGBColor(0x2B, 0x3A, 0x55)
PAPER    = RGBColor(0xF8, 0xF6, 0xF1)
CREAM    = RGBColor(0xFF, 0xFD, 0xF8)
WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
CORAL    = RGBColor(0xD1, 0x49, 0x5B)
CORAL_L  = RGBColor(0xF7, 0xE4, 0xE6)
GOLD     = RGBColor(0xC9, 0xA2, 0x27)
GOLD_L   = RGBColor(0xF4, 0xEC, 0xD4)
TEAL     = RGBColor(0x2A, 0x6F, 0x6B)
TEAL_L   = RGBColor(0xDE, 0xEE, 0xEA)
MUTED    = RGBColor(0x6B, 0x72, 0x80)
LINE     = RGBColor(0xDC, 0xD5, 0xC7)
GHOST    = RGBColor(0x23, 0x3F, 0x5E)

SERIF = "Noto Serif SC"
SANS  = "Noto Sans SC"
MATH  = "Cambria Math"

SW, SH = 13.333, 7.5
ML = 0.75
MR = 12.58
CW = MR - ML

prs = Presentation()
prs.slide_width = Inches(SW)
prs.slide_height = Inches(SH)
BLANK = prs.slide_layouts[6]


# ---------- low level helpers ----------
def set_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def no_shadow(shape):
    try:
        shape.shadow.inherit = False
    except Exception:
        pass


def add_rect(slide, x, y, w, h, fill=None, line=None, lw=0.75, shape=MSO_SHAPE.RECTANGLE, radius=None):
    shp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    no_shadow(shp)
    # python-pptx adds a <p:style> with effectRef=2, which LibreOffice renders as a shadow.
    style = shp._element.find(qn('p:style'))
    if style is not None:
        shp._element.remove(style)
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        try:
            shp.adjustments[0] = radius
        except Exception:
            pass
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


def _set_font(run, size, color, bold=False, math=False, serif=False, italic=False):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.color.rgb = color
    latin = MATH if math else (SERIF if serif else SANS)
    ea = MATH if math else (SERIF if serif else SANS)
    f.name = latin
    rPr = run._r.get_or_add_rPr()
    ea_el = rPr.find(qn('a:ea'))
    if ea_el is None:
        ea_el = etree.SubElement(rPr, qn('a:ea'))
    ea_el.set('typeface', ea)


def _add_runs(p, text, size, color, bold=False, serif=False, italic=False):
    """Mini markup: $...$ math; _{...}/^{...} inside math."""
    # Convert the small LaTeX subset used in the source into Unicode.
    for a, b in [
        (r'\frac{1}{2}', '½'), (r'\frac{1}{4}', '¼'),
        (r'\frac12', '½'), (r'\frac14', '¼'), (r'\frac{3}{4}', '¾'),
        (r'\Leftrightarrow', '⇔'), (r'\Rightarrow', '⇒'),
        (r'\infty', '∞'), (r'\Delta', 'Δ'),
        (r'\le', '≤'), (r'\ge', '≥'), (r'\ne', '≠'),
        (r'\in', '∈'), (r'\to', '→'),
        (r'\cosh', 'cosh'), (r'\min', 'min'), (r'\lim', 'lim'),
        (r'\qquad', '    '), (r'\quad', '  '), (r'\ ', ' '),
        (r'\{', '{'), (r'\}', '}'), (r'\,', ''), (r'\;', ' '),
    ]:
        text = text.replace(a, b)
    i = 0
    in_math = False
    buf = []
    def flush():
        nonlocal buf
        if not buf:
            return
        s = ''.join(buf)
        r = p.add_run()
        r.text = s
        _set_font(r, size, color, bold=bold, math=in_math, serif=serif, italic=italic)
        buf = []
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
                if j == -1:
                    content = text[i + 1:]
                    i = len(text)
                else:
                    content = text[i + 1:j]
                    i = j + 1
            else:
                content = text[i] if i < len(text) else ''
                i += 1
            sup_map = {
                '2': '²', '3': '³', '1': '¹', '0': '⁰', '+': '⁺', '-': '⁻',
                '-1': '⁻¹', '-x': '⁻ˣ', '-a': '⁻ᵃ', 'n': 'ⁿ', 'k': 'ᵏ',
            }
            r = p.add_run()
            if kind == '^' and content in sup_map:
                # Unicode superscripts render reliably in both PowerPoint and LibreOffice.
                r.text = sup_map[content]
                factor = 0.92 if content in ('1', '2', '3', '0') else 0.78
                _set_font(r, size * factor, color, bold=bold, math=True, serif=serif, italic=italic)
            else:
                r.text = content
                _set_font(r, size * 0.66, color, bold=bold, math=True, serif=serif, italic=italic)
                rPr = r._r.get_or_add_rPr()
                rPr.set('baseline', '-25000' if kind == '_' else '30000')
            continue
        buf.append(ch)
        i += 1
    flush()


def add_text(slide, x, y, w, h, text, size=16, color=INK_SOFT, bold=False,
             serif=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             line_spacing=1.2, space_after=0, italic=False, margins=(0, 0, 0, 0)):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.vertical_anchor = anchor
    tf.margin_left, tf.margin_right, tf.margin_top, tf.margin_bottom = [Inches(m) for m in margins]
    paragraphs = text.split('\n')
    for idx, para in enumerate(paragraphs):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_before = Pt(0)
        p.space_after = Pt(space_after)
        _add_runs(p, para, size, color, bold=bold, serif=serif, italic=italic)
    return tb


def add_page(slide, n, total=12, dark=False):
    col = RGBColor(0x8A, 0x93, 0xA3) if not dark else RGBColor(0x9A, 0xA8, 0xBF)
    add_text(slide, MR - 0.9, 7.13, 0.9, 0.25, f"{n:02d} / {total:02d}", size=8.5,
             color=col, align=PP_ALIGN.RIGHT)
    add_text(slide, ML, 7.13, 6.0, 0.25, "函数序关系与 I 排列  ·  2026 上海高考数学 21", size=8.5, color=col)


def header(slide, kicker, title, n, total=12, accent=CORAL):
    add_rect(slide, ML, 0.52, 0.07, 0.52, fill=accent)
    add_text(slide, ML + 0.20, 0.40, CW - 0.2, 0.25, kicker, size=9, color=accent, bold=True)
    add_text(slide, ML + 0.20, 0.64, CW - 0.2, 0.55, title, size=27, color=INK, bold=True, serif=True)
    add_rect(slide, ML, 1.34, CW, 0.012, fill=LINE)
    add_page(slide, n, total)


def content_slide(kicker, title, n, bg=PAPER, accent=CORAL, total=12):
    s = prs.slides.add_slide(BLANK)
    set_bg(s, bg)
    header(s, kicker, title, n, total=total, accent=accent)
    return s


def circle_letter(slide, x, y, d, letter, fill, txt_color=WHITE, size=16):
    add_rect(slide, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    add_text(slide, x, y + 0.01, d, d - 0.02, letter, size=size, color=txt_color,
             bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def pill(slide, x, y, w, h, text, fill, color=WHITE, size=11, bold=True):
    add_rect(slide, x, y, w, h, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
    add_text(slide, x + 0.04, y, w - 0.08, h, text, size=size, color=color, bold=bold,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


# ---------- slide 1: cover ----------
s = prs.slides.add_slide(BLANK)
set_bg(s, INK)
# faint grid on the right
for i in range(7):
    add_rect(s, 9.0 + i * 0.62, 0, 0.008, SH, fill=RGBColor(0x1D, 0x36, 0x52))
for j in range(9):
    add_rect(s, 9.0, 0.55 + j * 0.75, 4.33, 0.008, fill=RGBColor(0x1D, 0x36, 0x52))
add_text(s, 9.35, 0.95, 3.9, 5.6, "21", size=250, color=GHOST, bold=True,
         serif=True, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
# gold rule
add_rect(s, 0.92, 1.22, 1.35, 0.035, fill=GOLD)
add_text(s, 0.92, 0.86, 8.0, 0.3, "2026  ·  上海高考数学  ·  第 21 题", size=11,
         color=GOLD, bold=True)
add_text(s, 0.90, 1.55, 8.2, 1.35, "函数序关系\n与 I 排列", size=42, color=WHITE,
         bold=True, serif=True, line_spacing=1.08)
add_text(s, 0.92, 3.15, 7.6, 0.5, "从定义解码到存在性证明", size=21, color=RGBColor(0xE8, 0xDF, 0xC8),
         serif=True)
add_rect(s, 0.92, 3.82, 5.2, 0.01, fill=RGBColor(0x3A, 0x51, 0x6E))
add_text(s, 0.92, 4.02, 7.0, 0.35, "解题过程  ·  完整答案  ·  方法提炼", size=12.5,
         color=RGBColor(0xB9, 0xC3, 0xD2))
add_text(s, 0.92, 4.50, 7.2, 0.55,
         "把新定义翻译成三个开关，再用单调性控制它们。",
         size=13, color=RGBColor(0xE8, 0xDF, 0xC8), serif=True)
# small math motif
add_text(s, 0.92, 5.55, 7.5, 0.5,
         "$n_{I}=1+A+AB+C+BC+B$", size=18, color=RGBColor(0x8F, 0xA4, 0xC0))
add_text(s, 0.92, 6.15, 7.5, 0.35, "A  f₁≤f₂     B  f₁≤f₃     C  f₂≤f₃", size=10.5,
         color=RGBColor(0x6F, 0x84, 0xA2))
add_text(s, 0.92, 6.95, 5.0, 0.25, "2026 SHANGHAI  ·  PROBLEM 21", size=8.5,
         color=RGBColor(0x7E, 0x91, 0xAC))


# ---------- slide 2: statement (1) ----------
s = content_slide("PROBLEM STATEMENT  /  01", "题目原文（一）：定义与第 (1)(2) 问", 2)
add_rect(s, ML, 1.58, CW, 2.12, fill=CREAM, line=LINE, lw=0.75)
add_rect(s, ML, 1.58, 0.08, 2.12, fill=CORAL)
add_text(s, ML + 0.30, 1.72, CW - 0.55, 0.30, "定义", size=10, color=CORAL, bold=True)
add_text(s, ML + 0.30, 2.02, CW - 0.55, 1.75,
         "已知 $(i,j,k)$ 是 $1,2,3$ 的一个排列。若函数 $f_{1},f_{2},f_{3}$ 对任意 $x\\in I$ 都有\n"
         "$f_{1}(x)\\le f_{i}(x)$  且  $f_{1}(x)+f_{2}(x)\\le f_{i}(x)+f_{j}(x)$，\n"
         "则称 $(i,j,k)$ 是关于 $f_{1},f_{2},f_{3}$ 的一个 $I$ 排列，其总数记为 $n_{I}$。",
         size=15.5, color=INK, line_spacing=1.38)

# question cards
card_y = 3.95
card_h = 2.18
add_rect(s, ML, card_y, 5.78, card_h, fill=WHITE, line=LINE, lw=0.75)
add_text(s, ML + 0.28, card_y + 0.18, 0.8, 0.35, "（1）", size=17, color=CORAL, bold=True, serif=True)
add_text(s, ML + 0.28, card_y + 0.55, 5.22, 1.45,
         "已知 $I=[3,+\\infty)$，$f_{1}(x)=x$，$f_{2}(x)=0$，\n"
         "$f_{3}(x)=x^{2}+1$，判断 $(3,1,2)$ 是否为 $I$ 排列。",
         size=15, color=INK_SOFT, line_spacing=1.35)
add_rect(s, 6.80, card_y, 5.78, card_h, fill=WHITE, line=LINE, lw=0.75)
add_text(s, 6.80 + 0.28, card_y + 0.18, 1.0, 0.35, "（2）", size=17, color=TEAL, bold=True, serif=True)
add_text(s, 6.80 + 0.28, card_y + 0.55, 5.22, 1.45,
         "对 $I=(0,+\\infty)$，$f_{1}(x)=x-1$，$f_{2}(x)=x+m$，\n"
         "$f_{3}(x)=x^{2}$ 满足条件的 $n_{I}=6$，求 $m$ 的取值范围。",
         size=15, color=INK_SOFT, line_spacing=1.35)
add_text(s, ML + 0.28, card_y + 1.62, 5.2, 0.3,
         "提示：代入 $i=3,j=1$，逐条验证。", size=10, color=MUTED)
add_text(s, 6.80 + 0.28, card_y + 1.62, 5.2, 0.3,
         "提示：$n_{I}=6\\Leftrightarrow A=B=C=1$。", size=10, color=MUTED)
add_text(s, ML, 6.45, CW, 0.3,
         "注：条件中不出现 $f_{k}$；$k$ 由 $i,j$ 唯一确定。",
         size=10.5, color=MUTED, italic=False)


# ---------- slide 3: statement (3) ----------
s = content_slide("PROBLEM STATEMENT  /  02", "题目原文（二）：第 (3) 问", 3, accent=TEAL)
add_text(s, ML, 1.56, CW, 0.35,
         "对 $x\\in[0,+\\infty)$，都有 $0<F(x)<1$。令 $I=[a,+\\infty)$（$a>0$），",
         size=14.5, color=INK_SOFT)
# function cards
fy = 2.02
add_rect(s, ML, fy, 3.55, 1.18, fill=WHITE, line=LINE)
add_text(s, ML + 0.18, fy + 0.12, 0.7, 0.3, "f₁", size=12, color=CORAL, bold=True)
add_text(s, ML + 0.18, fy + 0.42, 3.2, 0.6, "$f_{1}(x)=F(x)$", size=15, color=INK)
add_text(s, ML + 0.18, fy + 0.83, 3.2, 0.25, "原函数", size=9, color=MUTED)
add_rect(s, 4.46, fy, 4.55, 1.18, fill=WHITE, line=LINE)
add_text(s, 4.64, fy + 0.12, 0.7, 0.3, "f₂", size=12, color=TEAL, bold=True)
add_text(s, 4.64, fy + 0.42, 4.25, 0.6, "$f_{2}(x)=\\frac{1}{2}[F(x+a)+F(x-a)]$", size=15, color=INK)
add_text(s, 4.64, fy + 0.83, 4.25, 0.25, "对称平均", size=9, color=MUTED)
add_rect(s, 9.17, fy, 3.41, 1.18, fill=WHITE, line=LINE)
add_text(s, 9.35, fy + 0.12, 0.7, 0.3, "f₃", size=12, color=GOLD, bold=True)
add_text(s, 9.35, fy + 0.42, 3.1, 0.6, "$f_{3}(x)=1-e^{-x}$", size=15, color=INK)
add_text(s, 9.35, fy + 0.83, 3.1, 0.25, "指数参照", size=9, color=MUTED)

# conclusions
cy = 3.55
add_rect(s, ML, cy, 5.78, 2.55, fill=WHITE, line=LINE)
add_rect(s, ML, cy, 5.78, 0.06, fill=CORAL)
add_text(s, ML + 0.30, cy + 0.24, 5.2, 0.35, "①  F 严格递减", size=15, color=CORAL, bold=True)
add_text(s, ML + 0.30, cy + 0.78, 5.1, 1.5,
         "则存在 $a>0$，使\n$n_{I}\\ge 4$。",
         size=22, color=INK, serif=True, line_spacing=1.35)
add_rect(s, 6.80, cy, 5.78, 2.55, fill=WHITE, line=LINE)
add_rect(s, 6.80, cy, 5.78, 0.06, fill=TEAL)
add_text(s, 6.80 + 0.30, cy + 0.24, 5.2, 0.35, "②  F 严格递增", size=15, color=TEAL, bold=True)
add_text(s, 6.80 + 0.30, cy + 0.78, 5.1, 1.5,
         "则存在 $a\\in(0,1)$，使\n$n_{I}\\ne 2$。",
         size=22, color=INK, serif=True, line_spacing=1.35)
add_text(s, ML + 0.30, cy + 2.05, 5.1, 0.35,
         "方法：取大 $a$，让 $f_{3}$ 主导", size=10.5, color=MUTED)
add_text(s, 6.80 + 0.30, cy + 2.05, 5.1, 0.35,
         "方法：先证 $A=0$，再分两种情形", size=10.5, color=MUTED)
add_text(s, ML, 6.55, CW, 0.3,
         "证明只依赖单调性与有界性：$0<F<1$。",
         size=11, color=MUTED)


# ---------- slide 4: decode ----------
s = content_slide("KEY STEP  /  01", "第一步：把定义翻译成 6 个条件", 4, accent=GOLD)
# table
tx, ty = ML, 1.62
tw = 7.30
colw = [2.05, tw - 2.05]
hh = 0.48
rh = 0.53
rows = [
    ("排列 $(i,j,k)$", "等价条件"),
    ("$(1,2,3)$", "恒成立"),
    ("$(1,3,2)$", "$f_{2}\\le f_{3}$"),
    ("$(2,1,3)$", "$f_{1}\\le f_{2}$"),
    ("$(2,3,1)$", "$f_{1}\\le f_{2}$ 且 $f_{1}\\le f_{3}$"),
    ("$(3,1,2)$", "$f_{1}\\le f_{3}$ 且 $f_{2}\\le f_{3}$"),
    ("$(3,2,1)$", "$f_{1}\\le f_{3}$"),
]
# header
add_rect(s, tx, ty, tw, hh, fill=INK)
add_text(s, tx + 0.16, ty, colw[0] - 0.2, hh, rows[0][0], size=11.5, color=WHITE, bold=True,
         anchor=MSO_ANCHOR.MIDDLE)
add_text(s, tx + colw[0] + 0.16, ty, colw[1] - 0.2, hh, rows[0][1], size=11.5, color=WHITE, bold=True,
         anchor=MSO_ANCHOR.MIDDLE)
for i, (a, b) in enumerate(rows[1:]):
    yy = ty + hh + i * rh
    add_rect(s, tx, yy, tw, rh, fill=(CREAM if i % 2 == 0 else WHITE))
    add_rect(s, tx, yy + rh - 0.01, tw, 0.01, fill=LINE)
    add_text(s, tx + 0.16, yy, colw[0] - 0.2, rh, a, size=14.5, color=INK, bold=True,
             anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, tx + colw[0] + 0.16, yy, colw[1] - 0.2, rh, b, size=14.5, color=INK_SOFT,
             anchor=MSO_ANCHOR.MIDDLE)
add_rect(s, tx, ty, tw, hh + 6 * rh, fill=None, line=LINE, lw=0.75)

# formula panel
px, py, pw, ph = 8.38, 1.62, 4.20, 3.66
add_rect(s, px, py, pw, ph, fill=INK)
add_text(s, px + 0.28, py + 0.18, pw - 0.5, 0.3, "计数公式", size=9.5, color=GOLD, bold=True)
add_text(s, px + 0.28, py + 0.55, pw - 0.5, 0.65,
         "$A=1$ 当 $f_{1}\\le f_{2}$，否则 $A=0$", size=11.5, color=RGBColor(0xD7, 0xDE, 0xE9))
add_text(s, px + 0.28, py + 0.95, pw - 0.5, 0.65,
         "$B=1$ 当 $f_{1}\\le f_{3}$，否则 $B=0$", size=11.5, color=RGBColor(0xD7, 0xDE, 0xE9))
add_text(s, px + 0.28, py + 1.35, pw - 0.5, 0.65,
         "$C=1$ 当 $f_{2}\\le f_{3}$，否则 $C=0$", size=11.5, color=RGBColor(0xD7, 0xDE, 0xE9))
add_rect(s, px + 0.28, py + 1.95, pw - 0.56, 0.012, fill=RGBColor(0x3C, 0x55, 0x77))
add_text(s, px + 0.28, py + 2.10, pw - 0.5, 0.55,
         "$n_{I}=1+A+AB+C+BC+B$", size=17, color=WHITE, serif=False)
add_text(s, px + 0.28, py + 2.78, pw - 0.5, 0.55,
         "$n_{I}=6\\Leftrightarrow A=B=C=1$", size=10.5, color=GOLD)
add_text(s, px + 0.28, py + 3.25, pw - 0.5, 0.3,
         "三个开关，决定六个排列", size=10, color=RGBColor(0x9F, 0xB0, 0xC7))
add_text(s, ML, 5.62, CW, 0.55,
         "例：$(3,1,2)$ 需 $f_{1}\\le f_{3}$，且 $f_{1}+f_{2}\\le f_{3}+f_{1}\\Leftrightarrow f_{2}\\le f_{3}$。  "
         "$k$ 不出现在不等式中，故只需看 $(i,j)$。",
         size=12, color=MUTED, line_spacing=1.35)
add_text(s, ML, 6.30, CW, 0.3,
         "六个排列对应三个开关；$n_{I}$ 最大为 $6$。",
         size=10.5, color=MUTED)


# ---------- slide 5: part (1) ----------
s = content_slide("PART  (1)  /  VERIFY", "第 (1) 问：直接验证", 5, accent=CORAL)
add_text(s, ML, 1.55, CW, 0.4, "$(3,1,2)$ 是否为 $I$ 排列？", size=20, color=INK, bold=True, serif=True)
# check cards
for k, (num, formula, detail, color) in enumerate([
    ("①", "$f_{1}(x)\\le f_{3}(x)$",
     "$x\\le x^{2}+1\\ \\Leftrightarrow\\ x^{2}-x+1>0$，$\\Delta=-3<0$，恒成立。", CORAL),
    ("②", "$f_{2}(x)\\le f_{3}(x)$",
     "$0\\le x^{2}+1$，恒成立。", TEAL),
]):
    yy = 2.18 + k * 1.30
    add_rect(s, ML, yy, CW, 1.12, fill=WHITE, line=LINE)
    circle_letter(s, ML + 0.22, yy + 0.24, 0.55, num, color, size=15)
    add_text(s, ML + 0.95, yy + 0.13, 3.1, 0.35, formula, size=16, color=INK, bold=True)
    add_text(s, ML + 0.95, yy + 0.55, CW - 1.2, 0.45, detail, size=14.5, color=INK_SOFT)
# conclusion
add_rect(s, ML, 4.95, CW, 1.12, fill=TEAL)
add_text(s, ML + 0.35, 4.95, 0.65, 1.12, "✓", size=26, color=WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
add_text(s, ML + 1.05, 4.95, CW - 1.3, 1.12,
         "所以 $(3,1,2)$ 是 $I$ 排列。", size=22, color=WHITE, bold=True, serif=True,
         anchor=MSO_ANCHOR.MIDDLE)
add_text(s, ML, 6.35, CW, 0.5,
         "对应 $i=3,j=1$：第一式化为 $f_{1}\\le f_{3}$，第二式化为 $f_{2}\\le f_{3}$。",
         size=11.5, color=MUTED)


# ---------- slide 6: part (2) conditions ----------
s = content_slide("PART  (2)  /  SIX SWITCHES", "第 (2) 问：$n_{I}=6$ 意味着三个开关全开", 6, accent=TEAL)
add_text(s, ML, 1.52, CW, 0.4,
         "由计数公式，$n_{I}=6\\ \\Leftrightarrow\\ A=B=C=1$。逐一验证：",
         size=14.5, color=INK_SOFT)
items = [
    ("A", "A：$f_{1}\\le f_{2}$", "$x-1\\le x+m\\ \\Leftrightarrow\\ m\\ge -1$", CORAL),
    ("B", "B：$f_{1}\\le f_{3}$", "$x-1\\le x^{2}\\ \\Leftrightarrow\\ x^{2}-x+1>0$，恒成立", TEAL),
    ("C", "C：$f_{2}\\le f_{3}$", "$x+m\\le x^{2}$ 对一切 $x>0$ 成立 $\\Leftrightarrow\\ m\\le -\\frac{1}{4}$", GOLD),
]
for k, (letter, head, body, color) in enumerate(items):
    yy = 2.18 + k * 1.08
    add_rect(s, ML, yy, CW, 0.92, fill=WHITE, line=LINE)
    circle_letter(s, ML + 0.22, yy + 0.19, 0.54, letter, color, size=17)
    add_text(s, ML + 0.95, yy + 0.10, 4.8, 0.35, head, size=15.5, color=INK, bold=True)
    add_text(s, ML + 0.95, yy + 0.48, CW - 1.15, 0.38, body, size=13.5, color=INK_SOFT)
# small derivation for C
add_text(s, ML + 0.95, 5.35, CW - 1.1, 0.32,
         "因为 $x^{2}-x=(x-\\frac{1}{2})^{2}-\\frac{1}{4}$，最小值在 $x=\\frac{1}{2}$ 处取得。",
         size=10.5, color=MUTED)
# conclusion
add_rect(s, ML, 5.92, CW, 0.78, fill=INK)
add_text(s, ML + 0.30, 5.92, 3.2, 0.78, "取交集：", size=12, color=RGBColor(0xB9, 0xC3, 0xD2),
         anchor=MSO_ANCHOR.MIDDLE)
add_text(s, ML + 2.05, 5.92, CW - 2.3, 0.78,
         "$-1\\le m\\le -\\frac{1}{4}$", size=25, color=WHITE, bold=True,
         anchor=MSO_ANCHOR.MIDDLE)


# ---------- slide 7: part (2) answer ----------
s = content_slide("PART  (2)  /  ANSWER", "第 (2) 问：答案与端点检验", 7, accent=GOLD)
# answer card
add_rect(s, ML, 1.62, 4.95, 2.30, fill=INK)
add_text(s, ML + 0.32, 1.78, 4.3, 0.3, "m 的取值范围", size=9.5, color=GOLD, bold=True)
add_text(s, ML + 0.30, 2.12, 4.4, 0.9, "$m\\in[-1,-\\frac{1}{4}]$", size=30, color=WHITE, bold=True)
add_text(s, ML + 0.32, 3.12, 4.3, 0.35, "闭区间：两个端点都能取到", size=10.5,
         color=RGBColor(0xC8, 0xD2, 0xDF))
# number line
nx0, nx1 = 6.35, 12.35
ny = 2.95
add_rect(s, nx0, ny, nx1 - nx0, 0.014, fill=INK_SOFT)
# map values -1.2 .. 0.2
def mapx(v):
    return nx0 + (v + 1.2) / 1.4 * (nx1 - nx0)
p1, p2 = mapx(-1.0), mapx(-0.25)
add_rect(s, p1, ny - 0.09, p2 - p1, 0.18, fill=CORAL)
# ticks
for v, lab in [(-1.0, "−1"), (-0.25, "−¼")]:
    xx = mapx(v)
    add_rect(s, xx - 0.008, ny - 0.14, 0.016, 0.28, fill=INK)
    add_rect(s, xx - 0.035, ny - 0.035, 0.07, 0.07, fill=INK, shape=MSO_SHAPE.OVAL)
    add_text(s, xx - 0.45, ny + 0.18, 0.9, 0.3, lab, size=13, color=INK, bold=True, align=PP_ALIGN.CENTER)
add_text(s, p1 - 0.25, ny - 0.68, p2 - p1 + 0.5, 0.3,
         "$-1\\le m\\le -\\frac14$", size=11.5, color=CORAL, bold=True, align=PP_ALIGN.CENTER)
add_text(s, nx1 + 0.05, ny - 0.20, 0.4, 0.3, "m", size=10, color=MUTED, bold=True)

# endpoint cards
ey = 4.22
add_rect(s, ML, ey, 5.78, 1.05, fill=WHITE, line=LINE)
add_text(s, ML + 0.22, ey + 0.16, 1.1, 0.3, "$m=-1$", size=14, color=INK, bold=True)
add_text(s, ML + 0.22, ey + 0.52, 5.3, 0.35,
         "A 取等号；C 成立（$-1\\le -\\frac14$）。", size=11.5, color=INK_SOFT)
add_rect(s, 6.80, ey, 5.78, 1.05, fill=WHITE, line=LINE)
add_text(s, 7.02, ey + 0.16, 2.0, 0.3, "$m=-\\frac{1}{4}$", size=14, color=INK, bold=True)
add_text(s, 7.02, ey + 0.52, 5.3, 0.35,
         "C 在 $x=\\frac12$ 取等号；A 成立。", size=11.5, color=INK_SOFT)
add_text(s, ML, 5.62, CW, 0.65,
         "两个端点都使 6 个排列全部成立，所以答案是闭区间 $[-1,-\\frac14]$。",
         size=14.5, color=INK, line_spacing=1.3)
add_text(s, ML, 6.45, CW, 0.35,
         "记忆点：$m$ 的上界由 $f_{2}\\le f_{3}$ 给出，下界由 $f_{1}\\le f_{2}$ 给出。",
         size=10.5, color=MUTED)


# ---------- slide 8: part (3) roadmap ----------
s = content_slide("PART  (3)  /  ROADMAP", "第 (3) 问：两条证明路线", 8, accent=CORAL)
# left column
lx, ly, lw_, lh = ML, 1.62, 5.78, 4.55
add_rect(s, lx, ly, lw_, lh, fill=WHITE, line=LINE)
add_rect(s, lx, ly, lw_, 0.07, fill=CORAL)
add_text(s, lx + 0.30, ly + 0.24, lw_ - 0.5, 0.35, "F 严格递减", size=18, color=CORAL, bold=True, serif=True)
bullets_l = [
    "取 $a>0$ 充分大。",
    "让 $f_{3}$ 同时高于 $f_{1},f_{2}$。",
    "于是 $B=C=1$。",
    "计数公式给出 $n_{I}=4+2A\\ge 4$。",
]
for i, b in enumerate(bullets_l):
    yy = ly + 0.82 + i * 0.72
    add_rect(s, lx + 0.32, yy + 0.10, 0.10, 0.10, fill=CORAL, shape=MSO_SHAPE.OVAL)
    add_text(s, lx + 0.58, yy, lw_ - 0.85, 0.65, b, size=13.5, color=INK_SOFT, line_spacing=1.22)
# right column
rx = 6.80
add_rect(s, rx, ly, lw_, lh, fill=WHITE, line=LINE)
add_rect(s, rx, ly, lw_, 0.07, fill=TEAL)
add_text(s, rx + 0.30, ly + 0.24, lw_ - 0.5, 0.35, "F 严格递增", size=18, color=TEAL, bold=True, serif=True)
bullets_r = [
    "先证 $A=0$ 对一切 $a>0$ 成立。",
    "若存在 $x$ 使 $F(x)>f_{3}(x)$，取小 $a$ 得 $B=C=0$。",
    "若 $F(x)\\le f_{3}(x)$ 恒成立，则 $B=C=1$。",
    "两种情形分别得到 $n_{I}=1$ 或 $n_{I}\\ge 4$。",
]
for i, b in enumerate(bullets_r):
    yy = ly + 0.82 + i * 0.72
    add_rect(s, rx + 0.32, yy + 0.10, 0.10, 0.10, fill=TEAL, shape=MSO_SHAPE.OVAL)
    add_text(s, rx + 0.58, yy, lw_ - 0.85, 0.72, b, size=13.0, color=INK_SOFT, line_spacing=1.20)
add_rect(s, lx + 0.30, 5.55, lw_ - 0.60, 0.40, fill=CORAL_L)
add_text(s, lx + 0.48, 5.55, lw_ - 0.85, 0.40, "取大 $a$：$f_{3}$ 压住 $f_{1},f_{2}$", size=10.5, color=CORAL, bold=True,
         anchor=MSO_ANCHOR.MIDDLE)
add_rect(s, rx + 0.30, 5.55, lw_ - 0.60, 0.40, fill=TEAL_L)
add_text(s, rx + 0.48, 5.55, lw_ - 0.85, 0.40, "取小 $a$：在 $x=a$ 处比较", size=10.5, color=TEAL, bold=True,
         anchor=MSO_ANCHOR.MIDDLE)
add_rect(s, ML, 6.38, CW, 0.55, fill=GOLD_L)
add_text(s, ML + 0.25, 6.38, CW - 0.45, 0.55,
         "共同点：不硬算 $n_{I}$，而是控制 $A,B,C$ 三个开关。",
         size=12.5, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)


# ---------- slide 9: increasing lemma ----------
s = content_slide("PART  (3)  /  LEMMA", "关键引理：F 递增时，A=0 恒成立", 9, accent=TEAL)
add_rect(s, ML, 1.58, CW, 0.88, fill=TEAL_L, line=TEAL, lw=0.75)
add_text(s, ML + 0.28, 1.58, CW - 0.5, 0.88,
         "对任意 $a>0$，$f_{1}\\le f_{2}$ 不可能在 $[a,+\\infty)$ 上恒成立。",
         size=15.5, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
steps = [
    ("1", "反设 $2F(x)\\le F(x-a)+F(x+a)$ 对一切 $x\\ge a$ 成立。"),
    ("2", "令 $u_{n}=F((n+1)a)$，则 $2u_{n}\\le u_{n-1}+u_{n+1}$（$n\\ge 1$）。"),
    ("3", "差 $d_{n}=u_{n+1}-u_{n}$ 单调不减，且 $d_{0}=F(2a)-F(a)>0$。"),
    ("4", "故 $u_{n}\\ge u_{0}+n d_{0}\\to+\\infty$，与 $u_{n}<1$ 矛盾。"),
]
for i, (num, txt) in enumerate(steps):
    yy = 2.80 + i * 0.78
    circle_letter(s, ML + 0.10, yy + 0.02, 0.48, num, TEAL, size=13)
    add_text(s, ML + 0.80, yy, CW - 0.9, 0.66, txt, size=14.5, color=INK_SOFT,
             anchor=MSO_ANCHOR.MIDDLE)
add_rect(s, ML, 6.12, CW, 0.62, fill=INK)
add_text(s, ML + 0.28, 6.12, CW - 0.5, 0.62,
         "所以 $A=0$：对每个 $a>0$，总存在 $x\\ge a$ 使 $f_{1}(x)>f_{2}(x)$。",
         size=13.5, color=WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)


# ---------- slide 10: decreasing ----------
s = content_slide("PART  (3)  /  DECREASING", "第 (3) 问①：F 严格递减", 10, accent=CORAL)
# step 1
add_text(s, ML, 1.55, 0.55, 0.4, "1", size=18, color=CORAL, bold=True)
add_text(s, ML + 0.52, 1.52, CW - 0.6, 0.5,
         "设 $L$ 为 $F(x)$ 当 $x\\to+\\infty$ 时的极限。因 $F$ 严格递减且 $F(0)<1$，故 $L\\le F(0)<1$。",
         size=13.5, color=INK_SOFT)
# step 2
add_text(s, ML, 2.22, 0.55, 0.4, "2", size=18, color=CORAL, bold=True)
add_text(s, ML + 0.52, 2.18, CW - 0.6, 0.55,
         "取 $a>0$ 充分大，使下面两式同时成立：",
         size=13.5, color=INK_SOFT)
add_rect(s, ML + 0.52, 2.68, 6.40, 0.95, fill=WHITE, line=LINE)
add_text(s, ML + 0.75, 2.72, 6.00, 0.44,
         "$F(a)+e^{-a}<1$", size=14, color=INK)
add_text(s, ML + 0.75, 3.12, 6.00, 0.44,
         "$\\frac{1}{2}[F(0)+F(a)]+e^{-a}<1$", size=14, color=INK)
add_text(s, 7.75, 2.78, 4.60, 0.85,
         "两式左边当 $a\\to+\\infty$ 时分别趋于\n$L$ 与 $\\frac12[F(0)+L]$，均小于 1。",
         size=10.5, color=MUTED, line_spacing=1.25)
# step 3
add_text(s, ML, 3.90, 0.55, 0.4, "3", size=18, color=CORAL, bold=True)
add_text(s, ML + 0.52, 3.86, CW - 0.6, 0.35,
         "对 $x\\ge a$，由单调性估计：",
         size=13.5, color=INK_SOFT)
add_rect(s, ML + 0.52, 4.30, CW - 0.52, 1.22, fill=WHITE, line=LINE)
add_text(s, ML + 0.80, 4.38, CW - 1.05, 0.50,
         "$f_{1}(x)=F(x)\\le F(a)<1-e^{-a}\\le 1-e^{-x}=f_{3}(x)$",
         size=14, color=INK)
add_text(s, ML + 0.80, 4.88, CW - 1.05, 0.55,
         "$f_{2}(x)=\\frac12[F(x+a)+F(x-a)]\\le\\frac12[F(a)+F(0)]<1-e^{-a}\\le f_{3}(x)$",
         size=14, color=INK)
# step 4
add_text(s, ML, 5.72, 0.55, 0.4, "4", size=18, color=CORAL, bold=True)
add_text(s, ML + 0.52, 5.68, CW - 0.6, 0.45,
         "所以 $B=C=1$，代入计数公式：",
         size=13.5, color=INK_SOFT)
add_rect(s, ML + 0.52, 6.14, CW - 0.52, 0.60, fill=CORAL)
add_text(s, ML + 0.80, 6.14, CW - 1.0, 0.60,
         "$n_{I}=1+A+A+1+1+1=4+2A\\ge 4$",
         size=17, color=WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)


# ---------- slide 11: increasing ----------
s = content_slide("PART  (3)  /  INCREASING", "第 (3) 问②：F 严格递增", 11, accent=TEAL)
add_text(s, ML, 1.50, CW, 0.35,
         "由引理，$A=0$ 对一切 $a>0$ 成立。下面按 $F$ 与 $f_{3}$ 的位置关系分两种情形。",
         size=12.5, color=INK_SOFT)
# case cards
cy = 2.02
cw_ = 5.78
# case 1
add_rect(s, ML, cy, cw_, 3.55, fill=WHITE, line=LINE)
add_text(s, ML + 0.26, cy + 0.14, cw_ - 0.4, 0.3, "情形 1", size=9, color=CORAL, bold=True)
add_text(s, ML + 0.26, cy + 0.40, cw_ - 0.45, 0.55,
         "存在 $x_{0}>0$ 使 $F(x_{0})>f_{3}(x_{0})$",
         size=13.0, color=INK, bold=True, serif=True)
add_text(s, ML + 0.26, cy + 0.98, cw_ - 0.5, 2.35,
         "取 $x_{0}$ 为连续点。令 $a\\to0^{+}$，则\n"
         "$f_{2}(x_{0})\\to F(x_{0})>f_{3}(x_{0})$。\n"
         "取 $0<a<\\min\\{1,x_{0}\\}$ 充分小，\n"
         "在 $x=x_{0}$ 处有 $f_{1}>f_{3}$，$f_{2}>f_{3}$，\n"
         "故 $B=C=0$。又 $A=0$，所以\n"
         "$n_{I}=1$。",
         size=12.2, color=INK_SOFT, line_spacing=1.35)
add_rect(s, ML + 0.26, 5.10, cw_ - 0.52, 0.36, fill=CORAL_L)
add_text(s, ML + 0.42, 5.10, cw_ - 0.8, 0.36, "结果：$n_{I}=1$", size=11, color=CORAL, bold=True,
         anchor=MSO_ANCHOR.MIDDLE)
# case 2
rx = 6.80
add_rect(s, rx, cy, cw_, 3.55, fill=WHITE, line=LINE)
add_text(s, rx + 0.26, cy + 0.14, cw_ - 0.4, 0.3, "情形 2", size=9, color=TEAL, bold=True)
add_text(s, rx + 0.26, cy + 0.40, cw_ - 0.45, 0.55,
         "对一切 $x$，$F(x)\\le f_{3}(x)$",
         size=13.0, color=INK, bold=True, serif=True)
add_text(s, rx + 0.26, cy + 0.98, cw_ - 0.5, 2.35,
         "此时 $B=1$。对 $x\\ge a$，\n"
         "$f_{2}(x)\\le\\frac12[f_{3}(x+a)+f_{3}(x-a)]$\n"
         "$=1-e^{-x}\\cosh a<1-e^{-x}=f_{3}(x)$，\n"
         "故 $C=1$。于是\n"
         "$n_{I}=4+2A\\ge 4$。",
         size=12.2, color=INK_SOFT, line_spacing=1.35)
add_rect(s, rx + 0.26, 5.10, cw_ - 0.52, 0.36, fill=TEAL_L)
add_text(s, rx + 0.42, 5.10, cw_ - 0.8, 0.36, "结果：$n_{I}=4$", size=11, color=TEAL, bold=True,
         anchor=MSO_ANCHOR.MIDDLE)
# conclusion
add_rect(s, ML, 5.78, CW, 0.75, fill=TEAL)
add_text(s, ML + 0.30, 5.78, CW - 0.5, 0.75,
         "两种情形都有 $n_{I}\\ne 2$，所以②得证。",
         size=16, color=WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
add_text(s, ML, 6.68, CW, 0.35,
         "注：单调函数的连续点稠密；若 $x_{0}$ 为间断点，在它右侧附近仍保持 $F>f_{3}$，取其中的连续点即可。",
         size=9.5, color=MUTED)


# ---------- slide 12: summary ----------
s = content_slide("REVIEW  /  THREE IDEAS", "复盘：这道压轴题在考什么？", 12, accent=GOLD)
cards = [
    ("01", "翻译", "6 个排列 → 3 个开关\n$A,B,C$ 把定义变成计数。", CORAL),
    ("02", "计数", "$n_{I}=1+A+AB+C+BC+B$\n$n=6$ 要全开；$n\\ge4$ 有通道。", TEAL),
    ("03", "控制", "递减取大 $a$；递增取小 $a$\n再用离散凸序列排除 $A=1$。", GOLD),
]
for i, (num, title, body, color) in enumerate(cards):
    xx = ML + i * 4.02
    add_rect(s, xx, 1.65, 3.78, 2.78, fill=WHITE, line=LINE)
    add_text(s, xx + 0.26, 1.82, 0.7, 0.35, num, size=10, color=color, bold=True)
    add_text(s, xx + 0.26, 2.12, 3.2, 0.45, title, size=20, color=INK, bold=True, serif=True)
    add_text(s, xx + 0.26, 2.72, 3.25, 1.10, body, size=12.2, color=INK_SOFT, line_spacing=1.38)
    add_rect(s, xx + 0.26, 3.98, 0.55, 0.012, fill=color)
    add_text(s, xx + 0.26, 4.07, 3.2, 0.25,
             ["对应第 (1) 问", "对应第 (2) 问", "对应第 (3) 问"][i], size=9, color=MUTED)
# answer strip
add_rect(s, ML, 4.80, CW, 1.20, fill=INK)
add_text(s, ML + 0.25, 4.90, 1.2, 0.3, "答案", size=9, color=GOLD, bold=True)
ans = [
    ("(1)", "是"),
    ("(2)", "$[-1,\\ -\\frac14]$"),
    ("(3)①", "$n_{I}\\ge 4$"),
    ("(3)②", "$n_{I}\\ne 2$"),
]
widths = [2.6, 3.3, 3.1, 3.3]
xx = ML + 0.25
for (lab, val), w in zip(ans, widths):
    add_text(s, xx, 5.12, w, 0.30, lab, size=9.5, color=RGBColor(0xB9, 0xC3, 0xD2))
    add_text(s, xx, 5.40, w, 0.45, val, size=17, color=WHITE, bold=True)
    xx += w
add_text(s, ML, 6.28, CW, 0.65,
         "新定义题的通用路径：先翻译，再计数，最后用单调性控制关键开关。",
         size=14, color=INK, serif=True, align=PP_ALIGN.CENTER)
add_text(s, ML, 6.78, CW, 0.3, "2026 上海高考数学 · 第 21 题 · 解析完", size=9, color=MUTED,
         align=PP_ALIGN.CENTER)


prs.core_properties.title = "2026上海高考数学第21题解析"
prs.core_properties.subject = "函数序关系与 I 排列"
prs.core_properties.author = "DeepSeek Harness"
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "2026上海高考数学21题解析.pptx")
prs.save(out)
print(out, len(prs.slides.__iter__.__self__._sldIdLst))

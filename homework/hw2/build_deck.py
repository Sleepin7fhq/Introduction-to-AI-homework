# -*- coding: utf-8 -*-
"""2026 新高考Ⅰ卷第14题 —— 讲义式讲稿 PPT（v3）"""
import re
from pptx import Presentation
from pptx.util import Cm, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn

INK = RGBColor(0x1B, 0x1B, 0x1B)
INK2 = RGBColor(0x55, 0x55, 0x55)
INK3 = RGBColor(0x8A, 0x87, 0x82)
GHOST = RGBColor(0xDC, 0xD7, 0xCB)
RED = RGBColor(0x9B, 0x2C, 0x2C)
RULE = RGBColor(0xD4, 0xD0, 0xC6)
RULE2 = RGBColor(0xE7, 0xE3, 0xDA)
CELLN = RGBColor(0xC2, 0xBE, 0xB4)
TINT = RGBColor(0xF3, 0xEF, 0xE5)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

SONG, TNR = "宋体", "Times New Roman"
WS, HS = 33.867, 19.05
L, R = 2.4, 31.4
CW = R - L

prs = Presentation()
prs.slide_width = Cm(WS)
prs.slide_height = Cm(HS)
BLANK = prs.slide_layouts[6]


def _strip_style(shape):
    sp = shape._element
    for el in sp.findall(qn("p:style")):
        sp.remove(el)


def set_ea(run, ea):
    rPr = run._r.get_or_add_rPr()
    el = rPr.find(qn("a:ea"))
    if el is None:
        from lxml import etree
        el = etree.SubElement(rPr, qn("a:ea"))
    el.set("typeface", ea)


def style(run, size, color=INK, bold=False, italic=False, latin=TNR, ea=SONG, baseline=None):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.color.rgb = color
    f.name = latin
    set_ea(run, ea)
    if baseline is not None:
        run._r.get_or_add_rPr().set("baseline", baseline)


def write(par, s, size, color=INK, bold=False, ea=SONG, latin=TNR, ratio=0.94):
    for tok in re.split(r"(_\{[^}]*\}|\^\{[^}]*\})", s):
        if not tok:
            continue
        base, body = None, tok
        if tok.startswith("_{"):
            base, body = "-25000", tok[2:-1]
        elif tok.startswith("^{"):
            base, body = "30000", tok[2:-1]
        roman = body.startswith("!")
        if roman:
            body = body[1:]
        for seg in re.finditer(r"[A-Za-z]+|[^A-Za-z]+", body):
            t = seg.group(0)
            r = par.add_run()
            r.text = t
            it = (not roman) and bool(re.fullmatch(r"[A-Za-z]+", t))
            style(r, size * (ratio if base else 1.0), color, bold, it,
                  latin=latin, ea=ea, baseline=base)


def tb(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Cm(x), Cm(y), Cm(w), Cm(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    return tf


def para(tf, s, size, color=INK, bold=False, align=PP_ALIGN.LEFT,
         before=0, after=0, line=1.5, first=False, ea=SONG, latin=TNR, indent=0.0):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_before = Pt(before)
    p.space_after = Pt(after)
    p.line_spacing = line
    if indent:
        p.left_indent = Cm(indent)
    write(p, s, size, color, bold, ea=ea, latin=latin)
    return p


def txt(slide, x, y, w, s, size, color=INK, bold=False, align=PP_ALIGN.LEFT,
        h=None, line=1.4, before=0):
    h = h if h is not None else size * 0.062 + 0.25
    tf = tb(slide, x, y, w, h)
    para(tf, s, size, color, bold, align=align, first=True, line=line, before=before)
    return tf


def hline(slide, x1, y1, x2, y2, color=RULE, width=0.75):
    ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Cm(x1), Cm(y1), Cm(x2), Cm(y2))
    ln.line.color.rgb = color
    ln.line.width = Pt(width)
    _strip_style(ln)
    return ln


def rect(slide, x, y, w, h, fill=WHITE, line=CELLN, lw=0.75):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(x), Cm(y), Cm(w), Cm(h))
    _strip_style(sh)
    sh.shadow.inherit = False
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(lw)
    sh.text_frame.word_wrap = True
    return sh


def page(slide, idx, section):
    txt(slide, L, 0.9, 18.0, "2026 年新高考Ⅰ卷 · 数学 第 14 题", 9.5, INK3, h=0.5)
    txt(slide, 18.0, 0.9, R - 18.0, section, 9.5, INK3, align=PP_ALIGN.RIGHT, h=0.5)
    hline(slide, L, 1.76, R, 1.76)
    txt(slide, R - 2.0, 17.4, 2.0, f"{idx:02d}", 9.5, INK3, align=PP_ALIGN.RIGHT, h=0.5)


def newslide(idx, section, title, size=28, ty=2.0):
    s = prs.slides.add_slide(BLANK)
    page(s, idx, section)
    txt(s, L, ty, CW, title, size, INK, bold=True, h=size * 0.062 + 0.4, line=1.2)
    return s


def stack(slide, x, y, items, gap, w=None, default_size=22, h=None):
    """逐行放公式：items = [(text, size, color, bold), ...]"""
    w = w if w is not None else CW
    for i, (t, size, color, bold) in enumerate(items):
        txt(slide, x, y + i * gap, w, t, size, color, bold,
            h=h if h is not None else size * 0.062 + 0.3, line=1.2)


GW, GH, GAP = 2.10, 1.00, 0.22


def bx(x0, i):
    return x0 + i * (GW + GAP)


def group_row(slide, x0, y0, n=5, highlight=(), sums=None, top=None,
              gw=GW, gh=GH, gap=GAP):
    for i in range(n):
        x = x0 + i * (gw + gap)
        hi = i in highlight
        rect(slide, x, y0, gw, gh, fill=(TINT if hi else WHITE),
             line=(INK if hi else CELLN), lw=(1.5 if hi else 0.75))
        for k in (1, 2):
            hline(slide, x + gw * k / 3.0, y0 + 0.16, x + gw * k / 3.0, y0 + gh - 0.16,
                  color=(RGBColor(0x8E, 0x8A, 0x80) if hi else RGBColor(0xDE, 0xDA, 0xD1)), width=0.6)
        if sums is not None:
            txt(slide, x - 0.25, y0 + gh + 0.12, gw + 0.5, sums[i], 12.5,
                (INK if hi else INK3), align=PP_ALIGN.CENTER, h=0.6)
        if top is not None:
            tf = tb(slide, x - 0.25, y0 - 0.78, gw + 0.5, 0.7, anchor=MSO_ANCHOR.BOTTOM)
            para(tf, top[i], 11.5, (INK2 if hi else INK3), align=PP_ALIGN.CENTER, first=True)


def bracket(slide, x1, x2, y, color=INK, width=1.1, tick=0.26):
    hline(slide, x1, y, x2, y, color=color, width=width)
    hline(slide, x1, y, x1, y - tick, color=color, width=width)
    hline(slide, x2, y, x2, y - tick, color=color, width=width)


# ---------------- 01 封面 ----------------
s = prs.slides.add_slide(BLANK)
hline(s, L, 2.95, L + 2.6, 2.95, color=RED, width=1.6)
txt(s, L, 3.35, CW, "2026 年普通高等学校招生全国统一考试（新高考Ⅰ卷）数学", 12.5, INK2, h=0.6)
txt(s, L, 4.3, CW, "第 14 题", 56, INK, bold=True, h=2.4, line=1.15)
txt(s, L, 7.55, 22.0, "数列的“三项一组”与等比子列的公比", 23, INK, h=1.2, line=1.4)
txt(s, L, 9.2, 24.0, "分组结构 · 分类讨论 · 取等构造", 14, INK3, h=0.6)
txt(s, L, 11.35, 27.0, "9 项 = 3 组 × 3 项。窗口里含几个整段，决定能列出几个关于 q³ 的等式；三种起点里，只有两种可行。",
    12.5, INK3, h=1.2, line=1.7)

hline(s, L, 14.1, R, 14.1, color=RULE2)
txt(s, L, 14.45, 12.0, "填空题最后一题 · 5 分", 11.5, INK3, h=0.6)
txt(s, L, 15.2, 22.0, "答案　q 的最大值为 ∛(3/2) = ∛12 / 2", 15, INK, h=0.8)

# ---------------- 02 原题 ----------------
s = newslide(2, "一 · 原题", "题目")
rect(s, L, 3.9, CW, 8.25, fill=WHITE, line=RULE, lw=0.75)
tf = tb(s, L + 0.9, 4.3, CW - 1.8, 7.4)
para(tf, "设实数 q 满足：存在数列 {a_{n}}，使得对于任意 n ∈ N^{*}，均有", 21.5, INK, first=True, line=1.75)
para(tf, "a_{1} + a_{2} + ⋯ + a_{3n} = n^{2} + n，", 21.5, INK, line=1.75, indent=0.9)
para(tf, "且 {a_{n}} 中有某连续 9 项 a_{k}, a_{k+1}, ⋯, a_{k+8} 是公比为 q 的等比数列，", 21.5, INK, line=1.75)
para(tf, "则 q 的最大值为 ＿＿＿＿＿＿＿＿．", 21.5, INK, line=1.75, indent=0.9)

txt(s, L, 12.6, CW, "三、填空题（第 12—14 题，每小题 5 分，共 15 分）· 本题为第 14 题，也是全卷填空题的最后一题", 11.5, INK3, h=0.6)
txt(s, L, 13.35, CW, "题面只给两条信息：每连续三项之和；某连续 9 项成等比。两条信息之间，隔着一个“分组”的动作。", 11.5, INK3, h=0.6)

# ---------------- 03 读题 ----------------
s = newslide(3, "二 · 读题", "条件其实只约束“三项之和”")
tf = tb(s, L, 3.95, 15.0, 12.4)
para(tf, "题设对每一项 a_{n} 本身不作要求，可以任意取值；被锁定的只是每连续三项的和。", 19.5, INK, first=True, line=1.95)
para(tf, "于是把数列按每三项一段切开，记第 n 段之和为 B_{n}。", 19.5, INK, before=16, line=1.95)
para(tf, "第二个条件给的是 9 个连续项。9 = 3 × 3，这段窗口与“三段”的分块必然咬合得很紧——这正是后面要分三种情况的原因。",
     19.5, INK, before=16, line=1.95)

x0 = 19.8
txt(s, x0, 3.95, 11.0, "第 n 段，和记作 B_{n}", 11.5, INK2, h=0.6)
bracket(s, x0, x0 + 7.34, 5.12, color=INK, width=1.0, tick=0.22)
for k in range(3):
    rect(s, x0 + k * 2.5, 5.68, 2.42, 1.2, fill=WHITE, line=CELLN)
    txt(s, x0 + k * 2.5, 5.86, 2.42, ["a_{3n−2}", "a_{3n−1}", "a_{3n}"][k], 13.5,
        INK, align=PP_ALIGN.CENTER, h=0.7)

hline(s, x0, 7.55, x0 + 7.34, 7.55, color=RULE2)
txt(s, x0, 7.8, 11.0, "9 项窗口", 14, INK, bold=True, h=0.7)
tf = tb(s, x0, 8.6, 11.2, 1.8)
para(tf, "跨越 2 个或 3 个整段；整段数由 k 除以 3 的余数决定。", 12, INK2, first=True, line=1.7)
txt(s, x0, 9.95, 11.0, "段和之比，才是可用的信息", 12.5, RED, h=0.6)

# ---------------- 04 第一步 ----------------
s = newslide(4, "三 · 转化", "把条件化成“段和”")
stack(s, L, 3.75, [
    ("B_{n} = a_{3n−2} + a_{3n−1} + a_{3n}", 23, INK, False),
    ("= S_{3n} − S_{3n−3}", 23, INK, False),
    ("= (n^{2} + n) − [(n − 1)^{2} + (n − 1)]", 23, INK, False),
    ("= 2n", 23, RED, True),
], gap=1.55, w=20.0)

txt(s, L, 9.55, 20.0, "这里 S_{n} 表示前 n 项和，S_{0} = 0；上式对一切 n ≥ 1 成立。", 11.5, INK2, h=0.7)

txt(s, 21.6, 3.85, R - 21.6, "所以段和依次是", 13, INK2, h=0.6)
txt(s, 21.6, 4.5, R - 21.6, "2, 4, 6, 8, 10, ⋯", 18, INK, h=0.9)
txt(s, 21.6, 5.65, R - 21.6, "公差为 2 的等差数列，\n且恒为正。", 12.5, INK2, h=1.6, line=1.7)

group_row(s, L, 11.25, n=5, sums=["2", "4", "6", "8", "10"],
          top=["B_{1}", "B_{2}", "B_{3}", "B_{4}", "B_{5}"])
txt(s, L, 13.4, CW, "这一步把“和”的信息榨干了：无论 a_{n} 怎么取，段和只能是 2n。段和恒正，最后定 q 的符号时还要用它。",
    13, INK2, h=1.0)

# ---------------- 05 关键一步 ----------------
s = newslide(5, "三 · 转化", "相隔三段，段和之比就是 q 的三次方")
txt(s, L, 3.65, CW, "把连续三项看作一段。整段后移 3 个位置，段内每一项都乘以 q^{3}，于是段和也乘以 q^{3}。",
    17, INK, h=0.9, line=1.6)

y = 7.0
for k in range(3):
    rect(s, L + k * 2.55, y, 2.46, 1.26, fill=WHITE, line=CELLN)
    txt(s, L + k * 2.55, y + 0.24, 2.46, ["x", "xq", "xq^{2}"][k], 14.5,
        INK, align=PP_ALIGN.CENTER, h=0.7)
txt(s, L, y + 1.38, 7.9, "段和　x(1 + q + q^{2})", 12.5, INK2, align=PP_ALIGN.CENTER, h=0.7)

ax1, ax2 = L + 8.2, L + 12.4
hline(s, ax1, y + 0.66, ax2, y + 0.66, color=RED, width=1.2)
txt(s, ax1, y - 0.42, ax2 - ax1, "× q^{3}", 15.5, RED, bold=True, align=PP_ALIGN.CENTER, h=0.7)

b0 = L + 13.3
for k in range(3):
    rect(s, b0 + k * 2.55, y, 2.46, 1.26, fill=TINT, line=INK, lw=1.1)
    txt(s, b0 + k * 2.55, y + 0.24, 2.46, ["xq^{3}", "xq^{4}", "xq^{5}"][k], 14.5,
        INK, align=PP_ALIGN.CENTER, h=0.7)
txt(s, b0, y + 1.38, 8.1, "段和　xq^{3}(1 + q + q^{2})", 12.5, INK2, align=PP_ALIGN.CENTER, h=0.7)

hline(s, L, 11.3, R, 11.3, color=RULE2)
tf = tb(s, L, 11.7, CW, 4.4)
para(tf, "窗口里含两个整段 → 得到 q^{3} = 后一段段和 ÷ 前一段段和；", 16, INK, first=True, line=1.75)
para(tf, "窗口里含三个整段 → 相邻两段之比都要等于 q^{3}。", 16, INK, line=1.75)
para(tf, "前者给上界，后者往往直接矛盾：这就是全题的开关。", 12, INK2, before=10)

# ---------------- 06 三种起点 ----------------
s = newslide(6, "四 · 分类", "起点不同，窗口装下的整段数不同", size=25)
ys = [5.15, 9.2, 13.25]
x0 = L + 0.3
hlg = [(1, 2, 3), (2, 3), (1, 2)]
win = [(1, 3, 0.0), (1, 4, 1 / 3.0), (0, 3, 2 / 3.0)]
notes = [
    ("k = 3m + 1　起点在段首", "三段都完整：2m+2、2m+4、2m+6 须成等比", "矛盾，不成立", RED, True),
    ("k = 3m + 2　起点偏 1 项", "两段完整：2m+4、2m+6，比值 q^{3} = (m+3)/(m+2)", "q^{3} ≤ 3/2，等号于 m = 0", INK, False),
    ("k = 3m　起点偏 2 项", "两段完整：2m+2、2m+4，比值 q^{3} = (m+2)/(m+1)", "q^{3} ≤ 3/2，等号于 m = 1", INK, False),
]
sums = ["2m", "2m+2", "2m+4", "2m+6", "2m+8"]
for i, y in enumerate(ys):
    group_row(s, x0, y, n=5, highlight=hlg[i], sums=sums)
    i1, i2, off = win[i]
    x1 = bx(x0, i1) + off * GW
    x2 = bx(x0, i2) + off * GW + GW
    bracket(s, x1, x2, y - 0.24, width=1.0, tick=0.22)
    txt(s, x1, y - 1.05, 5.0, "9 项窗口", 10.5, INK3, h=0.6)

for i, y in enumerate(ys):
    txt(s, 14.9, y - 0.12, R - 14.9, notes[i][0], 13.5, INK, bold=True, h=0.7)
    txt(s, 14.9, y + 0.7, R - 14.9, notes[i][1], 11.5, INK2, h=0.9)
    txt(s, 14.9, y + 1.55, R - 14.9, notes[i][2], 11.5, notes[i][3], bold=notes[i][4], h=0.7)

# ---------------- 07 情形一 ----------------
s = newslide(7, "四 · 分类", "起点在段首：三段要同时成等比")
txt(s, L, 3.6, CW, "9 项恰好是三个整段，段和依次为 2m+2、2m+4、2m+6。三数成等比，要求相邻比值相等：",
    16, INK, h=0.8, line=1.6)
stack(s, L + 2.2, 5.15, [
    ("(m + 2) / (m + 1) = (m + 3) / (m + 2)", 22, INK, False),
    ("⇔　(m + 2)^{2} = (m + 1)(m + 3)", 22, INK, False),
    ("⇔　m^{2} + 4m + 4 = m^{2} + 4m + 3", 22, INK, False),
    ("⇔　4 = 3", 22, RED, True),
], gap=1.62, w=24.0)

hline(s, L, 11.9, R, 11.9, color=RULE2)
tf = tb(s, L, 12.3, CW, 4.2)
para(tf, "两边永远差 1，与 m 无关。起点在段首的窗口不存在。", 16, INK, first=True, line=1.75)
para(tf, "顺带说明：若只要求连续 8 项，段首起点的窗口里只有两个整段，可以取到 q^{3} = 2；正是“9”多塞进一个整段，才把这个取法堵死。",
     12, INK2, before=8, line=1.65)

# ---------------- 08 情形二三 ----------------
s = newslide(8, "四 · 分类", "剩下两种起点：q³ 都不超过 3/2", size=27)
txt(s, L, 3.6, CW, "情形二　k = 3m + 2", 14, INK, bold=True, h=0.7)
txt(s, L, 4.45, CW, "q^{3} = B_{m+3} / B_{m+2} = (2m + 6) / (2m + 4) = 1 + 1/(m + 2) ≤ 3/2，等号于 m = 0（k = 2）",
    17, INK, h=0.9)

txt(s, L, 6.35, CW, "情形三　k = 3m", 14, INK, bold=True, h=0.7)
txt(s, L, 7.05, CW, "q^{3} = B_{m+2} / B_{m+1} = (2m + 4) / (2m + 2) = 1 + 1/(m + 1) ≤ 3/2，等号于 m = 1（k = 3）",
    17, INK, h=0.9)

hline(s, L, 8.85, R, 8.85, color=RULE2)
tf = tb(s, L, 9.2, CW, 2.2)
para(tf, "两个比值其实出自同一串数：3/2, 4/3, 5/4, 6/5, ⋯（递减，趋于 1）；", 14, INK2, first=True, line=1.75)
para(tf, "情形二从 m = 0 起、情形三从 m = 1 起，所以最大值只能落在 3/2。", 14, INK2, line=1.75)

tf = tb(s, L, 12.0, CW, 4.6)
para(tf, "段和为正 ⇒ q^{3} > 0 ⇒ q > 0，于是　q ≤ ∛(3/2)。", 20, INK, first=True, line=1.6)
para(tf, "上界到手，还差一步：等号能不能取到。", 12, INK3, before=12)

# ---------------- 09 取等 ----------------
s = newslide(9, "五 · 取等", "把等号兑现：构造一条合乎条件的数列")
txt(s, L, 3.85, CW, "取 k = 2（分类中情形二的等号），q = ∛(3/2)，令首项 x = 4 / [q^{2}(1 + q + q^{2})] ≈ 0.8835。",
    16, INK, h=0.9)
stack(s, L + 0.8, 5.55, [
    ("a_{i} = x·q^{ i−2 }　（i = 2, 3, ⋯, 10）", 17, INK, False),
    ("a_{1} = 2 − a_{2} − a_{3}，　a_{11} + a_{12} = 8 − a_{10}", 17, INK, False),
    ("n ≥ 5 时，a_{3n−2} = 2n，a_{3n−1} = a_{3n} = 0", 17, INK, False),
], gap=1.4, w=CW - 1.6)

hline(s, L, 9.95, R, 9.95, color=RULE2)
tf = tb(s, L, 10.3, CW, 5.2)
para(tf, "逐段核对：B_{1} = 2，B_{2} = xq^{2}(1+q+q^{2}) = 4，B_{3} = q^{3}B_{2} = 6，B_{4} = 8，n ≥ 5 时 B_{n} = 2n。",
     16, INK, first=True, line=1.75)
para(tf, "于是 S_{3n} = 2(1 + 2 + ⋯ + n) = n(n + 1) = n^{2} + n，且 a_{2}, ⋯, a_{10} 是公比为 q 的等比数列。条件全部满足。",
     16, INK, before=8, line=1.75)
para(tf, "x 不是凑出来的：由 B_{2} = xq^{2}(1+q+q^{2}) = 4 直接解出。　（k = 3 亦可，情形三的等号由它兑现。）",
     11.5, INK3, before=14, line=1.6)

# ---------------- 10 答案 ----------------
s = newslide(10, "六 · 答案", "结果")
txt(s, L, 3.8, CW, "q 的最大值", 13, INK3, h=0.6)
txt(s, L, 4.5, CW, "∛(3/2)", 50, INK, h=2.4, line=1.15)
txt(s, L, 7.3, CW, "= ∛12 / 2 ≈ 1.1447", 19, INK2, h=0.9)

hline(s, L, 9.5, R, 9.5, color=RULE2)
for i, h in enumerate(["检验对象", "计算", "数值"]):
    txt(s, [L, L + 11.8, L + 20.6][i], 9.85, 8.0, h, 11, INK3,
        align=(PP_ALIGN.RIGHT if i == 2 else PP_ALIGN.LEFT), h=0.5)
hline(s, L, 10.5, R, 10.5, color=RGBColor(0xBF, 0xBB, 0xB2))

rows = [("q^{3}", "3/2", "1.5000"),
        ("B_{2} = a_{4} + a_{5} + a_{6}", "xq^{2}(1 + q + q^{2})", "4.0000"),
        ("B_{3} = a_{7} + a_{8} + a_{9}", "q^{3}B_{2}", "6.0000")]
for i, (a, b, c) in enumerate(rows):
    y = 10.7 + i * 1.3
    txt(s, L, y, 11.4, a, 14.5, INK, h=0.7)
    txt(s, L + 11.8, y, 8.4, b, 14.5, INK, h=0.7)
    txt(s, L + 20.6, y, R - L - 20.6, c, 14.5, INK, align=PP_ALIGN.RIGHT, h=0.7)

hline(s, L, 14.85, R, 14.85, color=RGBColor(0xBF, 0xBB, 0xB2))
txt(s, L, 15.2, CW, "取 q = ∛(3/2) 与相应的 x 代入，段和与 2n 完全吻合。填空题只写结果。", 11.5, INK3, h=0.6)

# ---------------- 11 拓展 ----------------
s = newslide(11, "七 · 拓展", "为什么是 9", size=26)
txt(s, L, 3.5, CW, "把“连续 9 项”换成“连续 L 项”，结论随 L 变化：", 14, INK, h=0.6)

data = [("L ≤ 7", "起点偏 1 项或偏 2 项时，窗口只含 1 个整段，一个方程管不住 q", "q 无上界"),
        ("L = 8", "段首起点恰含 2 个整段，q^{3} = 4/2 = 2", "最大值 ∛2"),
        ("L = 9、10", "段首起点含 3 个整段而矛盾，只剩偏 1 项、偏 2 项", "最大值 ∛(3/2)"),
        ("L ≥ 11", "任何起点都含至少 3 个整段，比值无法同时成立", "不存在这样的 q")]
for i, (a, b, c) in enumerate(data):
    y = 4.95 + i * 1.92
    txt(s, L, y, 4.2, a, 16, INK, bold=True, h=0.7)
    txt(s, L + 4.6, y + 0.05, 17.0, b, 11.5, INK2, h=1.1, line=1.45)
    txt(s, L + 22.0, y, R - L - 22.0, c, 13.5, (RED if i == 2 else INK), bold=(i == 2),
        align=PP_ALIGN.RIGHT, h=0.7)
    if i < 3:
        hline(s, L, y + 1.5, R, y + 1.5, color=RULE2)

tf = tb(s, L, 13.2, CW, 3.4)
para(tf, "关键只在一处：L = 9 时，段首起点的窗口恰好放下三个整段，2m+2 与 2m+4 的比、2m+4 与 2m+6 的比不可能相等，",
     12, INK, first=True, line=1.7)
para(tf, "“取到 ∛2”的路被堵上，最大值才落到 ∛(3/2)。", 12, INK, line=1.7)

# ---------------- 12 回顾 ----------------
s = newslide(12, "八 · 回顾", "整道题只有三步")
items = [("01", "条件只看段和", "B_{n} = S_{3n} − S_{3n−3} = 2n；段和是首项 2、公差 2 的等差数列"),
         ("02", "相隔三段，比值定型", "段和之比 = q^{3}；窗口含几个整段，就决定能列出几个这样的比"),
         ("03", "分类、上界、取等", "三种起点只剩两种，q^{3} ≤ 3/2；k = 2 时等号确实成立")]
y = 4.15
for i, (num, t1, d) in enumerate(items):
    txt(s, L, y - 0.42, 3.0, num, 34, GHOST, bold=True, h=1.4)
    txt(s, L + 3.2, y, 25.0, t1, 16.5, INK, bold=True, h=0.8)
    txt(s, L + 3.2, y + 0.95, 25.0, d, 12.5, INK2, h=0.9)
    y += 3.15

hline(s, L, 13.85, R, 13.85, color=RULE2)
txt(s, L, 14.25, CW, "答案　q 的最大值为 ∛(3/2) = ∛12 / 2 ≈ 1.1447", 17, INK, bold=True, h=0.9)
txt(s, L, 15.4, CW, "看结构，不看项：先分块，再比块。", 11.5, INK3, h=0.6)

prs.save("2026新高考1卷数学第14题.pptx")
print("saved", len(prs.slides._sldIdLst))

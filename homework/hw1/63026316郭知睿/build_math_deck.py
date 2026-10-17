# -*- coding: utf-8 -*-
"""
《加性唯一性条件下指数和的 L¹、L²、L⁴ 范数估计》PPT 生成脚本
------------------------------------------------------------
- 版式：16:9，深蓝 + 浅灰白学术风
- 公式：MathJax (TeX) → SVG → PNG，按磅值精确落位
- 产物：加性唯一性条件下指数和的范数估计.pptx

运行：source ~/ppt-env/bin/activate && python build_math_deck.py
"""

import json
import os
import shutil
import subprocess

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

# ------------------------------------------------------------------ 设计变量
W, H = 13.3333, 7.5
M = 0.95
RE = W - M
TOTAL = 10

PAPER = "F8FAFD"
INK = "10202F"
INK2 = "33465C"
GRAY = "66788D"
NAVY = "0B2447"
BLUE = "2C5F97"
BLUE_L = "6E9BC8"
SKY = "EAF1F8"
SKY2 = "DCE7F3"
LINE = "D4DEEA"
GOLD = "A9812F"
RED = "A6402D"
WHITE = "FFFFFF"
DARK_CARD = "122E52"
DARK_LINE = "2A4A74"
LIGHT_TXT = "DCE8F7"

CN = "Noto Sans CJK SC"
POS = MSO_SHAPE.RECTANGLE

# ------------------------------------------------------------------ 公式清单
FORMULAS = {
    "cover_r2": dict(tex=r"\int_0^1|f|^2dx=N", size=17, color="#" + LIGHT_TXT),
    "cover_r4": dict(tex=r"\int_0^1|f|^4dx=2N^2-N", size=17, color="#" + LIGHT_TXT),
    "cover_r1": dict(tex=r"\int_0^1|f|dx\geq\frac{1}{2\sqrt N}", size=17, color="#D9C08A"),

    "p2_cond": dict(tex=r"n_1+n_2=n_3+n_4\ \Longrightarrow\ n_1\in\{n_3,n_4\}", size=21),
    "p2_f": dict(tex=r"f(x)=\sum_{n\in S}e^{2\pi i nx}", size=26),
    "p2_ask": dict(tex=r"(1)\ \int_0^1|f|^2dx\qquad(2)\ \int_0^1|f|^4dx\qquad(3)\ \int_0^1|f|dx\geq\frac{1}{2\sqrt N}",
                   size=13.5),

    "p3_equiv": dict(tex=r"\Phi(a,b)=\Phi(c,d)\iff\{a,b\}=\{c,d\}", size=21),
    "p3_fiber": dict(tex=r"\Phi^{-1}(s)=\begin{cases}\varnothing,&s\notin S+S\\ \{(a,a)\},&s=2a\\ \{(a,b),(b,a)\},&s=a+b,\ a\neq b\end{cases}",
                     size=16),

    "p4_l2": dict(tex=r"|f(x)|^2=\sum_{m,n\in S}e^{2\pi i(m-n)x}", size=19),
    "p4_l4": dict(tex=r"|f(x)|^4=\sum_{n_1,n_2,n_3,n_4\in S}e^{2\pi i(n_1+n_2-n_3-n_4)x}", size=16),
    "p4_R": dict(tex=r"\int_0^1|f|^4dx=\#\{(n_1,n_2,n_3,n_4)\in S^4:\ n_1+n_2=n_3+n_4\}=:R", size=15),

    "p5_deriv": dict(tex=r"\begin{aligned}\int_0^1|f(x)|^2dx&=\int_0^1\left(\sum_{m\in S}e^{2\pi i m x}\right)\left(\sum_{n\in S}e^{-2\pi i n x}\right)dx\\"
                              r"&=\sum_{m,n\in S}\int_0^1e^{2\pi i(m-n)x}dx=\sum_{m,n\in S}\delta_{mn}=N\end{aligned}", size=18.5),
    "p5_orth": dict(tex=r"\int_0^1e^{2\pi i kx}dx=\begin{cases}1,&k=0\\ 0,&k\neq0\end{cases}", size=15),
    "p5_res": dict(tex=r"\int_0^1|f(x)|^2dx=N", size=19),

    "p6_def": dict(tex=r"\begin{aligned}\int_0^1|f|^4dx&=\sum_{n_1,n_2,n_3,n_4\in S}\int_0^1e^{2\pi i(n_1+n_2-n_3-n_4)x}dx"
                             r"=\sum_{n_1,\dots,n_4\in S}\delta_{n_1+n_2,\,n_3+n_4}\\"
                             r"&=\sum_{(n_1,n_2)\in S^2}\#\{(n_3,n_4)\in S^2:\ n_3+n_4=n_1+n_2\}\end{aligned}", size=15.5),
    "p6_final": dict(tex=r"R=\underbrace{N}_{n_1=n_2}+\underbrace{2N(N-1)}_{n_1\neq n_2}=2N^2-N", size=20),

    "p7_theta": dict(tex=r"\frac{1}{2}=\theta\cdot1+(1-\theta)\cdot\frac{1}{4}\ \Longrightarrow\ \theta=\frac{1}{3}", size=17),
    "p7_lemma": dict(tex=r"\|f\|_2\leq\|f\|_1^{1/3}\|f\|_4^{2/3}\quad\iff\quad\int_0^1|f|dx\geq"
                          r"\frac{\left(\int_0^1|f|^2dx\right)^{3/2}}{\left(\int_0^1|f|^4dx\right)^{1/2}}", size=17),

    "p8_holder": dict(tex=r"\begin{aligned}\int_0^1|f|^2dx&=\int_0^1|f|^{2/3}\cdot|f|^{4/3}dx\\"
                             r"&\leq\left(\int_0^1|f|dx\right)^{2/3}\left(\int_0^1|f|^4dx\right)^{1/3}\end{aligned}", size=18),
    "p8_chain1": dict(tex=r"N\leq I^{2/3}(2N^2-N)^{1/3}\ \Longrightarrow\ N^3\leq I^2(2N^2-N)"
                            r"\ \Longrightarrow\ I^2\geq\frac{N^2}{2N-1}", size=16.5),
    "p8_chain2": dict(tex=r"I\geq\frac{N}{\sqrt{2N-1}}\geq\frac{N}{\sqrt{2N}}=\sqrt{\frac{N}{2}}\geq\frac{1}{2\sqrt N}", size=20),
    "p8_res": dict(tex=r"\int_0^1|f|dx\geq\frac{1}{2\sqrt N}", size=19),
    "p8_strong": dict(tex=r"\int_0^1|f|dx\geq\frac{N}{\sqrt{2N-1}}\geq\sqrt{\frac{N}{2}}", size=15),

    "p9_sum": dict(tex=r"\int_0^1|f|^2dx=N\qquad\int_0^1|f|^4dx=2N^2-N\qquad\int_0^1|f|dx\geq\frac{1}{2\sqrt N}", size=14),

    "p10_l2": dict(tex=r"\int_0^1|f|^2dx=N", size=21, color="#" + WHITE),
    "p10_l4": dict(tex=r"\int_0^1|f|^4dx=2N^2-N", size=21, color="#" + WHITE),
    "p10_l1": dict(tex=r"\int_0^1|f|dx\geq\frac{1}{2\sqrt N}", size=21, color="#D9C08A"),
}


def render_formulas():
    """渲染公式：有 Node + MathJax 时重排；否则复用 assets/formulas 里已渲染的图片。"""
    meta_path = "assets/formulas/meta.json"
    can_render = bool(shutil.which("node")) and os.path.isdir("tools/math/node_modules")
    if not can_render and os.path.exists(meta_path):
        print("[info] 未检测到 Node/MathJax 依赖，复用 assets/formulas 中已渲染的公式图。")
        with open(meta_path, encoding="utf-8") as f:
            return {m["id"]: m for m in json.load(f)}
    os.makedirs("assets/formulas", exist_ok=True)
    jobs = [{"id": k, **v} for k, v in FORMULAS.items()]
    with open("tools/math/jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False)
    subprocess.run(["node", "render.js", "jobs.json", "../../assets/formulas"],
                   cwd="tools/math", check=True)
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    return {m["id"]: m for m in meta}


META = render_formulas()


def rgb(h):
    return RGBColor.from_string(h)


# ------------------------------------------------------------------ 底层工具
def style_run(r, size=14, bold=False, color=INK, font=CN, spc=0, italic=False, base=None):
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = rgb(color)
    rPr = r._r.get_or_add_rPr()
    if spc:
        rPr.set("spc", str(int(spc)))
    if base:
        rPr.set("baseline", str(int(base)))
    rPr.get_or_add_latin().set("typeface", font)
    for tag, name in (("a:ea", "ea"), ("a:cs", "cs")):
        el = rPr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rPr, qn(tag))
        el.set("typeface", font)


def tb(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    return tf


def para(tf, text="", size=14, bold=False, color=INK, font=CN, spc=0,
         align=PP_ALIGN.LEFT, before=0, after=0, line=1.25, first=False, italic=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_before = Pt(before)
    p.space_after = Pt(after)
    p.line_spacing = line
    if text:
        r = p.add_run()
        r.text = text
        style_run(r, size, bold, color, font, spc, italic)
    return p


def rich(tf, chunks, size=14, color=INK, font=CN, line=1.25, first=False,
         before=0, after=0, align=PP_ALIGN.LEFT):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_before = Pt(before)
    p.space_after = Pt(after)
    p.line_spacing = line
    for text, kw in chunks:
        r = p.add_run()
        r.text = text
        style_run(r, kw.get("size", size), kw.get("bold", False),
                  kw.get("color", color), kw.get("font", font),
                  kw.get("spc", 0), kw.get("italic", False), kw.get("base"))
    return p


def rect(slide, x, y, w, h, fill=None, line=None, lw=0.75, shape=POS):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.shadow.inherit = False
    style = s._element.find(qn("p:style"))
    if style is not None:
        s._element.remove(style)
    if fill:
        s.fill.solid()
        s.fill.fore_color.rgb = rgb(fill)
    else:
        s.fill.background()
    if line:
        s.line.color.rgb = rgb(line)
        s.line.width = Pt(lw)
    else:
        s.line.fill.background()
    s.text_frame.word_wrap = False
    return s


def hline(slide, x1, x2, y, color=LINE, lw=0.75):
    h = max(lw / 72.0, 0.008)
    return rect(slide, x1, y - h / 2, x2 - x1, h, fill=color)


def vline(slide, x, y1, y2, color=LINE, lw=0.75):
    w = max(lw / 72.0, 0.008)
    return rect(slide, x - w / 2, y1, w, y2 - y1, fill=color)


def bg(slide, color):
    s = rect(slide, 0, 0, W, H, fill=color)
    sp = s._element
    sp.getparent().remove(sp)
    slide.shapes._spTree.insert(2, sp)


def fimg(slide, fid, x=None, y=None, cx=None, cy=None, right=None, maxw=None, scale=1.0):
    m = META[fid]
    w, h = m["w"] / 72.0 * scale, m["h"] / 72.0 * scale
    if maxw and w > maxw:
        k = maxw / w
        w, h = w * k, h * k
    if cx is not None:
        x = cx - w / 2
    if right is not None:
        x = right - w
    if cy is not None:
        y = cy - h / 2
    slide.shapes.add_picture(f"assets/formulas/{fid}.png", Inches(x), Inches(y), Inches(w), Inches(h))
    return w, h


def fh(fid):
    return META[fid]["h"] / 72.0


def fw(fid):
    return META[fid]["w"] / 72.0


# ------------------------------------------------------------------ 版式骨架
def footer(slide, page, dark=False):
    c = "8FA3BC" if dark else "93A2B4"
    tf = tb(slide, M, 7.08, 9.0, 0.2)
    para(tf, "加性唯一性条件下指数和的 L¹、L²、L⁴ 范数估计", size=8, color=c, first=True, spc=30)
    tf = tb(slide, RE - 1.2, 7.08, 1.2, 0.2)
    para(tf, f"{page:02d} / {TOTAL}", size=8, color=c, first=True, align=PP_ALIGN.RIGHT, spc=30)


def content_slide(prs, eyebrow, title, lead=None, page=None):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s, PAPER)
    rect(s, 0, 0, 0.09, H, fill=NAVY)
    tf = tb(s, M, 0.40, 9.4, 0.22)
    para(tf, eyebrow, size=9, bold=True, color=BLUE, spc=240, first=True, line=1.0)
    hline(s, M, RE, 0.70, LINE, 0.75)
    tf = tb(s, M, 0.84, 11.4, 0.56)
    para(tf, title, size=27, bold=True, color=INK, first=True, line=1.05)
    if lead:
        tf = tb(s, M, 1.46, 11.2, 0.3)
        para(tf, lead, size=12.5, color=GRAY, first=True, line=1.1)
    footer(s, page)
    return s


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def badge(slide, x, y, n, d=0.30, color=BLUE):
    rect(slide, x, y, d, d, fill=color)
    tf = tb(slide, x, y + 0.035, d, 0.22)
    para(tf, n, size=10, bold=True, color=WHITE, align=PP_ALIGN.CENTER, first=True)


def card(slide, x, y, w, h, fill=SKY, line=None, accent=None):
    rect(slide, x, y, w, h, fill=fill, line=line)
    if accent:
        rect(slide, x, y, 0.045, h, fill=accent)


def flow(slide, x, y, items, bw=2.30, gap=0.45, h=0.38, fs=10.5):
    cx = x
    for i, t in enumerate(items):
        last = (i == len(items) - 1)
        rect(slide, cx, y, bw, h, fill="D6E5F4" if last else SKY)
        tf = tb(slide, cx, y + 0.085, bw, 0.22)
        para(tf, t, size=fs, color=INK2, align=PP_ALIGN.CENTER, first=True)
        cx += bw
        if not last:
            tf = tb(slide, cx, y + 0.06, gap, 0.24)
            para(tf, "→", size=11, color=BLUE, align=PP_ALIGN.CENTER, first=True)
            cx += gap


def mini(slide, x, y, w, rows, cw=1.45, fs=10.5, highlight=(), row_h=0.325, head=None):
    yy = y
    if head:
        tf = tb(slide, x, yy, cw, 0.22)
        para(tf, head[0], size=8.5, bold=True, color=GRAY, spc=80, first=True)
        tf = tb(slide, x + cw, yy, w - cw, 0.22)
        para(tf, head[1], size=8.5, bold=True, color=GRAY, spc=80, first=True)
        yy += 0.26
        hline(slide, x, x + w, yy - 0.04, LINE, 0.6)
    for i, (a, b) in enumerate(rows):
        col = RED if i in highlight else INK2
        tf = tb(slide, x, yy, cw, 0.24)
        para(tf, a, size=fs, color=col, first=True)
        tf = tb(slide, x + cw, yy, w - cw, 0.24)
        para(tf, b, size=fs, bold=(i in highlight), color=col, first=True)
        hline(slide, x, x + w, yy + 0.275, LINE, 0.5)
        yy += row_h
    return yy


def deflist(slide, x, y, w, rows, cw=1.35, row_h=0.345, fs=9.5):
    rect(slide, x, y, w, 0.34, fill=NAVY)
    tf = tb(slide, x + 0.14, y + 0.075, cw, 0.22)
    para(tf, "符号", size=9, bold=True, color=WHITE, first=True)
    tf = tb(slide, x + cw + 0.14, y + 0.075, w - cw - 0.2, 0.22)
    para(tf, "含义", size=9, bold=True, color=WHITE, first=True)
    yy = y + 0.34
    for i, (chunks, desc) in enumerate(rows):
        if i % 2 == 0:
            rect(slide, x, yy, w, row_h, fill="F1F5FA")
        tf = tb(slide, x + 0.14, yy + 0.085, cw, 0.22)
        rich(tf, chunks, size=fs, color=INK2, first=True)
        tf = tb(slide, x + cw + 0.14, yy + 0.085, w - cw - 0.2, 0.22)
        para(tf, desc, size=fs, color=INK2, first=True)
        yy += row_h
    return yy


def set_borders(cell, color=LINE, sides=("B",), lw=0.75):
    tcPr = cell._tc.get_or_add_tcPr()
    for s in ("L", "R", "T", "B"):
        for el in tcPr.findall(qn("a:ln" + s)):
            tcPr.remove(el)
    order = {"L": 0, "R": 1, "T": 2, "B": 3}
    for i, s in enumerate(sorted(sides, key=lambda k: order[k])):
        ln = etree.Element(qn("a:ln" + s))
        ln.set("w", str(int(lw * 12700)))
        ln.set("cap", "flat")
        ln.set("cmpd", "sng")
        ln.set("algn", "ctr")
        fill = etree.SubElement(ln, qn("a:solidFill"))
        clr = etree.SubElement(fill, qn("a:srgbClr"))
        clr.set("val", color)
        etree.SubElement(ln, qn("a:prstDash")).set("val", "solid")
        tcPr.insert(i, ln)


def table(slide, x, y, w, h, data, col_w, fs=10, hfs=9.5, header=True,
          header_fill=NAVY, header_color=WHITE, zfill="F1F5FA", row_h=None,
          first_bold=False, align=None, pad=0.12):
    rows, cols = len(data), len(data[0])
    gf = slide.shapes.add_table(rows, cols, Inches(x), Inches(y), Inches(w), Inches(h))
    tbl = gf.table
    for flag in ("first_row", "horz_banding", "first_col", "last_row", "last_col", "vert_banding"):
        setattr(tbl, flag, False)
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    if row_h:
        for i, rh in enumerate(row_h):
            tbl.rows[i].height = Inches(rh)
    for ri, row in enumerate(data):
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.margin_left = Inches(pad)
            cell.margin_right = Inches(pad)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            is_head = header and ri == 0
            if is_head:
                fill, color, bold, size = header_fill, header_color, True, hfs
            else:
                fill = zfill if (ri % 2 == 0) else PAPER
                color = INK2
                bold = bool(first_bold and ci == 0)
                size = fs
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(fill)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.line_spacing = 1.0
            if align and ci < len(align):
                p.alignment = align[ci]
            r = p.add_run()
            r.text = str(val)
            style_run(r, size, bold, color)
            set_borders(cell, LINE if not is_head else header_fill,
                        ("B",) if not is_head else (), 0.75)
    return tbl


# ------------------------------------------------------------------ 建 PPT
prs = Presentation()
prs.slide_width = Inches(W)
prs.slide_height = Inches(H)


# ================================================================== 01 封面
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s, NAVY)
rect(s, 0, 0, 0.09, H, fill=GOLD)

tf = tb(s, M, 0.70, 8.0, 0.24)
para(tf, "COMPETITION  SOLUTION   ·   15  PTS", size=9, bold=True, color="7FA6CF", spc=300, first=True)

tf = tb(s, M, 1.48, 9.9, 2.1)
para(tf, "加性唯一性条件下", size=41, bold=True, color=WHITE, first=True, line=1.22)
para(tf, "指数和的 L¹、L²、L⁴ 范数估计", size=41, bold=True, color=WHITE, line=1.22)

rect(s, M, 3.66, 2.25, 0.035, fill=GOLD)

tf = tb(s, M, 3.90, 10.8, 0.35)
para(tf, "二、（本题 15 分）｜条件 → 展开 → 积分 → 计数 → 不等式", size=13, color="AFC5DE", first=True)

labels = [("L² 范数", "cover_r2"), ("L⁴ 范数", "cover_r4"), ("L¹ 下界", "cover_r1")]
for i, (lab, fid) in enumerate(labels):
    cx = M + 1.85 + i * 3.72
    tf = tb(s, cx - 1.6, 5.18, 3.2, 0.22)
    para(tf, lab, size=9, bold=True, color="7FA6CF", spc=160, align=PP_ALIGN.CENTER, first=True)
    fimg(s, fid, cx=cx, y=5.52)
for x in (M + 3.70, M + 7.42):
    vline(s, x, 5.10, 6.55, "2A4A74", 0.75)

tf = tb(s, M, 6.92, 8.0, 0.25)
para(tf, "主讲人：＿＿＿＿＿＿　　日期：＿＿＿＿＿＿", size=9, color="7E97B6", first=True, spc=40)

notes(s, "本题只有三个动作：用正交性算 L² 范数，用加性唯一性数四元组算 L⁴ 范数，"
         "再用 Hölder 插值把两个已知矩翻译成 L¹ 的下界。今天这十页就按这条主线走："
         "先把条件翻译成“无序对唯一”，再把积分翻译成计数，最后用插值一步收口。")


# ================================================================== 02 重述
s = content_slide(prs, "01 · 问题重述", "问题重述与符号说明",
                  "先固定对象与记号：集合、条件、函数、目标。", 2)

tf = tb(s, M, 1.86, 6.0, 0.28)
para(tf, "S ⊂ ℤ，|S| = N ≥ 1：N 个互不相同的整数。", size=13, color=INK2, first=True)

card(s, M, 2.30, 6.05, 1.40, fill=SKY, accent=BLUE)
tf = tb(s, M + 0.22, 2.42, 5.6, 0.22)
para(tf, "加性唯一性条件", size=9.5, bold=True, color=BLUE, spc=120, first=True)
fimg(s, "p2_cond", x=M + 0.22, y=2.66, maxw=5.5)
tf = tb(s, M + 0.22, 3.34, 5.7, 0.22)
para(tf, "四元组 n₁,…,n₄ 取自 S；结论即 n₁ ∈ {n₃, n₄}", size=9.5, color=GRAY, first=True)

tf = tb(s, M, 3.96, 4.0, 0.22)
para(tf, "指数和", size=9.5, bold=True, color=BLUE, spc=120, first=True)
fimg(s, "p2_f", x=M, y=4.24, maxw=5.7)
tf = tb(s, M, 5.46, 5.9, 0.22)
para(tf, "x ∈ [0, 1]，以 1 为周期；f 复值，|f| 非负", size=9.5, color=GRAY, first=True)

rows = [
    ([("S", {})], "整数集合，|S| = N"),
    ([("n", {})], "S 中的元素（k = 1,2,3,4）"),
    ([("f", {})], "指数和（复值函数）"),
    ([("|f|", {})], "复数模（非负实值）"),
    ([("‖f‖", {})], "p 阶范数（p = 1, 2, 4）"),
    ([("δ", {})], "Kronecker 符号 δ(m,n)"),
    ([("R", {})], "四元组计数"),
]
deflist(s, 7.32, 1.86, 5.05, rows, cw=1.20, row_h=0.345, fs=9.5)

tf = tb(s, 7.32, 4.94, 5.0, 0.22)
para(tf, "待 求", size=9.5, bold=True, color=BLUE, spc=200, first=True)
hline(s, 7.32, RE, 5.16, LINE, 0.75)
fimg(s, "p2_ask", x=7.32, y=5.24, maxw=5.05)
tf = tb(s, 7.32, 5.92, 5.05, 0.4)
para(tf, "第 (2) 问要求：无论 S 如何取，下界一致成立。", size=9, color=GRAY, first=True, line=1.3)

notes(s, "先立记号：S 是 N 个整数，条件里的四个指标都取自 S。注意条件的写法可以等价写成 "
         "n₁ ∈ {n₃, n₄}，这样后面说“无序对唯一”时不用再加括号解释。f 是复值函数，取模之后才是非负实数，"
         "所以每一步积分都是对 |f| 做的。")

# ================================================================== 03 条件解读
s = content_slide(prs, "02 · 条件解读", "条件解读：无序对的唯一性",
                  "条件不是说“和互不相同”，而是说“和相同 ⇒ 无序对相同”。", 3)

fimg(s, "p3_equiv", x=M, y=1.94, maxw=6.1)

tf = tb(s, M, 2.80, 6.2, 0.28)
rich(tf, [("(⇒) ", {"bold": True, "color": BLUE}),
          ("a+b=c+d ⇒ a=c（则 b=d）或 a=d（则 b=c）⇒ {a,b}={c,d}", {"color": INK2})],
     size=11.5, first=True, line=1.3)
tf = tb(s, M, 3.20, 6.2, 0.28)
rich(tf, [("(⇐) ", {"bold": True, "color": BLUE}),
          ("反之 {a,b}={c,d} ⇒ a=c 或 a=d，条件结论自动成立", {"color": INK2})],
     size=11.5, first=True, line=1.3)

fimg(s, "p3_fiber", x=M, y=3.92, maxw=5.5)
tf = tb(s, M, 5.34, 6.2, 0.28)
rich(tf, [("原像大小 ∈ {0,1,2}：", {"color": INK2}),
          ("对角 1 个，非对角 2 个。", {"bold": True, "color": BLUE})], size=11, first=True)

tf = tb(s, 7.10, 1.88, 5.2, 0.25)
para(tf, "S = {0,1,3}：六个无序对 → 六个不同的和", size=10.5, bold=True, color=INK, first=True)
mini(s, 7.10, 2.20, 4.0, [("{0,0}", "0"), ("{0,1}", "1"), ("{0,3}", "3"),
                          ("{1,1}", "2"), ("{1,3}", "4"), ("{3,3}", "6")],
     cw=1.45, fs=11, head=("无序对", "和"), row_h=0.32)
tf = tb(s, 7.10, 4.56, 5.2, 0.25)
para(tf, "反例 S = {0,1,2}：两个无序对撞到同一个和", size=10.5, bold=True, color=RED, first=True)
mini(s, 7.10, 4.88, 4.0, [("{0,2}", "2"), ("{1,1}", "2")], cw=1.45, fs=11,
     highlight=(0, 1), head=("无序对", "和"), row_h=0.32)
tf = tb(s, 7.10, 5.86, 5.1, 0.3)
para(tf, "两个不同的无序对给出同一个和，唯一性被破坏。", size=9, color=RED, first=True)

tf = tb(s, M, 6.55, 11.4, 0.25)
rich(tf, [("第 6 页的因子 2 正来自这里：", {"color": GRAY}),
          ("非对角原像恰有两个元素 (a,b)、(b,a)。", {"bold": True, "color": BLUE})],
     size=10, first=True)

notes(s, "这一页是全场的地基。唯一性不是“和互不相同”，而是“和相同 ⇒ 无序对相同”。"
         "上面这个 ⇔ 论证只有两行，但它把每个和的原像大小锁死为 1 或 2："
         "对角 a+a 只有一个有序对，非对角 a+b 有 (a,b) 与 (b,a) 两个。第 6 页的因子 2 就是从这里来的。")

# ================================================================== 04 思路
s = content_slide(prs, "03 · 第(1)问 · 思路", "第(1)问思路：展开与正交性",
                  "把积分翻译成计数：正交性只保留指数为 0 的项。", 4)

tf = tb(s, M, 1.66, 11.4, 0.22)
para(tf, "①  L² 范数", size=9.5, bold=True, color=BLUE, spc=180, align=PP_ALIGN.CENTER, first=True)
fimg(s, "p4_l2", cx=W / 2, y=2.06)
flow(s, 1.39, 3.00, ["展开 N² 项", "正交性筛选", "只剩对角项", "得到 N"], bw=2.30, gap=0.45)

tf = tb(s, M, 3.60, 11.4, 0.22)
para(tf, "②  L⁴ 范数", size=9.5, bold=True, color=BLUE, spc=180, align=PP_ALIGN.CENTER, first=True)
fimg(s, "p4_l4", cx=W / 2, y=3.94)
flow(s, 2.77, 4.94, ["展开 N⁴ 项", "积分筛选", "四元组计数"], bw=2.30, gap=0.45)

fimg(s, "p4_R", cx=W / 2, y=5.60)
tf = tb(s, M, 6.35, 11.4, 0.3)
rich(tf, [("核心：", {"bold": True, "color": GOLD}),
          ("积分只统计指数为 0 的项；|f|⁴ 的积分 = 满足 n₁+n₂ = n₃+n₄ 的有序四元组个数 R。", {"color": INK2})],
     size=10.5, first=True, align=PP_ALIGN.CENTER)

notes(s, "两问的思路其实是同一句话：算积分就是数指数为 0 的项。"
         "L² 展开得到 N² 项，正交性只让 m=n 的 N 项活下来；"
         "L⁴ 展开得到 N⁴ 项，活下来的恰好是 n₁+n₂=n₃+n₄ 的四元组，记作 R。"
         "下面两页分别把 N 和 R 算出来。")

# ================================================================== 05 L2
s = content_slide(prs, "04 · 第(1)问 · L²", "第(1)问计算一：正交性与对角项",
                  "逐项积分，正交性筛出 N 个对角项。", 5)

fimg(s, "p5_deriv", x=M, y=1.90, maxw=7.55)

card(s, M, 4.62, 7.55, 1.18, fill=SKY, accent=BLUE)
tf = tb(s, M + 0.22, 4.72, 6.0, 0.22)
para(tf, "正交性（k ∈ ℤ）", size=9.5, bold=True, color=BLUE, spc=120, first=True)
fimg(s, "p5_orth", x=M + 0.22, y=4.90, maxw=6.6)

gx, gy, cell, gap, n = 9.28, 2.02, 0.40, 0.075, 5
for i in range(n):
    for j in range(n):
        on = i == j
        rect(s, gx + j * (cell + gap), gy + i * (cell + gap), cell, cell,
             fill=BLUE if on else SKY)
        tf = tb(s, gx + j * (cell + gap), gy + i * (cell + gap) + 0.085, cell, 0.2)
        para(tf, "1" if on else "0", size=8, color=WHITE if on else "A8B9CB",
             align=PP_ALIGN.CENTER, first=True)
tf = tb(s, gx - 0.10, gy + n * (cell + gap) + 0.03, 2.95, 0.4)
para(tf, "N×N 项中只有对角 N 项存活", size=8.5, color=GRAY, first=True, line=1.25)

card(s, 9.10, 4.62, 3.30, 1.18, fill=WHITE, line=GOLD)
tf = tb(s, 9.28, 4.74, 2.9, 0.2)
para(tf, "结 果", size=8.5, bold=True, color=GOLD, spc=200, first=True)
fimg(s, "p5_res", x=9.28, y=4.96, maxw=2.95)

tf = tb(s, M, 6.16, 11.4, 0.3)
rich(tf, [("Parseval 视角：", {"bold": True, "color": BLUE}),
          ("f̂(n) = 1_S(n)，故 ‖f‖₂² = Σ|f̂(n)|² = N；这一步与加性唯一性条件无关。", {"color": GRAY})],
     size=9.5, first=True)

notes(s, "推导只有两步：展开，然后逐项积分。有限和，交换积分与求和不需要任何讨论。"
         "正交性把无穷多条项筛成 N 条对角项，每条积分为 1。"
         "要强调：这一步没有用到加性唯一性，任何 N 元整数集都有 ∫|f|²=N。")

# ================================================================== 06 L4
s = content_slide(prs, "05 · 第(1)问 · L⁴", "第(1)问计算二：四元组分类计数",
                  "固定有序对 (n₁,n₂)，按对角 / 非对角分类计数。", 6)

fimg(s, "p6_def", x=M, y=1.86, maxw=11.4)

data = [["情形", "有序对 (n₁,n₂)", "每个的解数", "贡献"],
        ["对角  n₁ = n₂", "N", "1", "N"],
        ["非对角  n₁ ≠ n₂", "N(N−1)", "2", "2N(N−1)"],
        ["合计", "N²", "—", "2N² − N"]]
table(s, M, 3.42, 7.60, 1.85, data, [2.15, 2.05, 1.65, 1.75], fs=10.5, hfs=9.5,
      align=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER])

fimg(s, "p6_final", x=M, y=5.40, maxw=7.2)

card(s, 8.95, 3.48, 3.43, 1.10, fill=SKY, accent=BLUE)
tf = tb(s, 9.15, 3.58, 3.0, 0.2)
para(tf, "对 角", size=8.5, bold=True, color=BLUE, spc=200, first=True)
tf = tb(s, 9.15, 3.84, 3.0, 0.3)
para(tf, "a + a = 2a：只有 (a,a) 一个解", size=10, color=INK2, first=True)
tf = tb(s, 11.55, 3.62, 0.7, 0.6)
para(tf, "1", size=28, bold=True, color=BLUE_L, align=PP_ALIGN.RIGHT, first=True)

card(s, 8.95, 4.72, 3.43, 1.10, fill=SKY, accent=GOLD)
tf = tb(s, 9.15, 4.82, 3.0, 0.2)
para(tf, "非 对 角", size=8.5, bold=True, color=GOLD, spc=200, first=True)
tf = tb(s, 9.15, 5.08, 3.0, 0.3)
para(tf, "a + b：交换次序得到两个解", size=10, color=INK2, first=True)
tf = tb(s, 11.55, 4.86, 0.7, 0.6)
para(tf, "2", size=28, bold=True, color="C9A96A", align=PP_ALIGN.RIGHT, first=True)

tf = tb(s, M, 6.50, 11.4, 0.3)
rich(tf, [("核验：", {"bold": True, "color": BLUE}),
          ("N=1 → 1｜S={0,1} → 6｜S={0,1,3} → 15；非 Sidon 的 S={0,1,2} 得 19 > 15，条件使 L⁴ 取到最小值。",
           {"color": GRAY})], size=9.5, first=True)

notes(s, "这是全场最容易错的一页。固定一个有序对 (n₁,n₂)，问 (n₃,n₄) 有几种。"
         "由第 3 页的等价性，{n₃,n₄}={n₁,n₂}，只有两种次序。"
         "如果 n₁=n₂，两种次序是同一个，只能算 1 个；如果 n₁≠n₂，才是 2 个。"
         "所以 R = N + 2N(N−1) = 2N²−N。千万不要把因子 2 加到对角项上。")

# ================================================================== 07 思路二
s = content_slide(prs, "06 · 第(2)问 · 思路", "第(2)问思路：用插值反解 L¹",
                  "由 L²、L⁴ 两个矩，从下方顶住 L¹。", 7)

card(s, M, 1.86, 5.35, 0.52, fill=SKY)
tf = tb(s, M + 0.18, 1.96, 5.0, 0.3)
rich(tf, [("已知  ", {"bold": True, "color": BLUE, "size": 9}),
          ("∫|f|² = N，∫|f|⁴ = 2N² − N", {"color": INK2})], size=11, first=True)
card(s, 6.65, 1.86, 5.73, 0.52, fill="F5EEDF")
tf = tb(s, 6.83, 1.96, 5.4, 0.3)
rich(tf, [("待证  ", {"bold": True, "color": GOLD, "size": 9}),
          ("∫|f| ≥ 1/(2√N)", {"color": INK2})], size=11, first=True)

card(s, M, 2.60, 3.35, 1.55, fill=WHITE, line=LINE, accent=RED)
tf = tb(s, M + 0.22, 2.70, 3.0, 0.22)
para(tf, "方向陷阱", size=9, bold=True, color=RED, spc=160, first=True)
tf = tb(s, M + 0.22, 2.98, 2.98, 1.0)
para(tf, "Cauchy–Schwarz 只给", size=10, color=INK2, first=True, line=1.3)
para(tf, "‖f‖₁ ≤ ‖f‖₂ = √N", size=10.5, bold=True, color=INK, line=1.35)
para(tf, "这是上界，方向反了。", size=10, color=RED, line=1.3)

fimg(s, "p7_theta", x=4.62, y=2.52, maxw=8.0)

# 指数数轴
ax0, ax1, ay = 4.72, 9.55, 3.62
hline(s, ax0, ax1, ay, "B9C8D9", 1.0)
tf = tb(s, ax0, ay - 0.36, 1.2, 0.22)
para(tf, "1/p 轴", size=8.5, color=GRAY, first=True)
for frac, lab in ((0.25, "1/4"), (0.5, "1/2"), (1.0, "1")):
    px = ax0 + (frac - 0.25) / 0.75 * (ax1 - ax0)
    vline(s, px, ay - 0.10, ay + 0.10, BLUE, 1.2)
    tf = tb(s, px - 0.35, ay + 0.14, 0.7, 0.22)
    para(tf, lab, size=10, color=INK2, align=PP_ALIGN.CENTER, first=True)
px = ax0 + (0.5 - 0.25) / 0.75 * (ax1 - ax0)
rect(s, px - 0.055, ay - 0.055, 0.11, 0.11, fill=GOLD)
tf = tb(s, px - 0.6, ay + 0.40, 1.2, 0.22)
para(tf, "θ = 1/3", size=9, bold=True, color=GOLD, align=PP_ALIGN.CENTER, first=True)

card(s, M, 4.92, 11.43, 1.42, fill=SKY, accent=BLUE)
tf = tb(s, M + 0.22, 5.02, 8.0, 0.22)
para(tf, "引理（Hölder 插值 / 对数凸性）", size=9, bold=True, color=BLUE, spc=120, first=True)
fimg(s, "p7_lemma", x=M + 0.22, y=5.30, maxw=10.9)

tf = tb(s, M, 6.52, 11.4, 0.3)
rich(tf, [("指数不是猜的：", {"bold": True, "color": BLUE}),
          ("解方程 1/2 = θ·1 + (1−θ)/4 得 θ = 1/3，再立方即可反解出 L¹ 的下界。", {"color": GRAY})],
     size=9.5, first=True)

notes(s, "为什么不能直接用 Cauchy–Schwarz？因为它给的是 ‖f‖₁ ≤ ‖f‖₂，方向反了。"
         "正确做法是把 L² 看成 L¹ 与 L⁴ 的插值：1/2 = θ·1 + (1−θ)/4，解出 θ=1/3。"
         "这个引理把“两个已知矩”变成“L¹ 的一个下界”，下一页就是把它代进去。")

# ================================================================== 08 证明
s = content_slide(prs, "07 · 第(2)问 · 证明", "第(2)问证明：插值下界",
                  "Hölder 拆分 → 代入 → 立方 → 开方 → 放缩。", 8)

badge(s, M, 1.90, "1")
w1, h1 = fimg(s, "p8_holder", x=M + 0.48, y=1.86, maxw=7.5)

badge(s, M, 1.86 + h1 + 0.30, "2")
w2, h2 = fimg(s, "p8_chain1", x=M + 0.48, y=1.86 + h1 + 0.26, maxw=7.5)

badge(s, M, 1.86 + h1 + h2 + 0.66, "3")
fimg(s, "p8_chain2", x=M + 0.48, y=1.86 + h1 + h2 + 0.62, maxw=7.6)

card(s, 9.20, 2.35, 3.18, 1.42, fill=WHITE, line=GOLD)
tf = tb(s, 9.38, 2.45, 2.8, 0.2)
para(tf, "结 论", size=8.5, bold=True, color=GOLD, spc=200, first=True)
fimg(s, "p8_res", x=9.38, y=2.76, maxw=2.8)

card(s, 8.96, 4.28, 3.42, 1.05, fill=SKY)
tf = tb(s, 9.12, 4.38, 3.1, 0.2)
para(tf, "每一步的依据", size=8.5, bold=True, color=BLUE, spc=100, first=True)
tf = tb(s, 9.12, 4.62, 3.1, 0.6)
para(tf, "① Hölder（共轭指数 3/2, 3）", size=8.5, color=INK2, first=True, line=1.35)
para(tf, "② 代入 N、2N²−N　③ 立方", size=8.5, color=INK2, line=1.35)
para(tf, "④ √(2N−1) ≤ √(2N)，2N ≥ 1", size=8.5, color=INK2, line=1.35)

card(s, M, 5.72, 11.43, 0.96, fill="F6F8FB", line=LINE)
tf = tb(s, M + 0.20, 5.82, 6.4, 0.22)
para(tf, "加强说明（不替代原证明）", size=8.5, bold=True, color=GOLD, spc=120, first=True)
tf = tb(s, M + 0.20, 6.06, 6.9, 0.5)
para(tf, "实际得到更强估计，对 N ≥ 1 比题目要求强至少 N 倍；题目下界只是它的宽松推论。",
     size=8.5, color=GRAY, first=True, line=1.25)
fimg(s, "p8_strong", x=8.30, y=5.86, maxw=3.9)

tf = tb(s, M, 6.80, 11.4, 0.2)
para(tf, "N = 1 时 S = {n}，|f| ≡ 1，三个积分都为 1，结论与加强估计同时取等号。",
     size=8, color=GRAY, first=True)

notes(s, "四步。第一步 Hölder，共轭指数 3/2 和 3，把 |f|² 拆成 |f|^{2/3}·|f|^{4/3}；"
         "第二步把 N 和 2N²−N 代进去；第三步立方，解出 I ≥ N/√(2N−1)；"
         "第四步用 √(2N−1) ≤ √(2N) 放大，再注意 2N ≥ 1，就得到 1/(2√N)。"
         "顺便说一句，这个估计其实强得多——N/√(2N−1) ≈ √(N/2)，题目要的只是它的一个宽松推论。")

# ================================================================== 09 总结
s = content_slide(prs, "08 · 方法与易错", "方法总结与易错点",
                  "三条主线，四个陷阱。", 9)

tf = tb(s, M, 1.84, 5.4, 0.22)
para(tf, "三条主线", size=9, bold=True, color=BLUE, spc=180, first=True)

items = [("01", "正交性 → L²", "指数为 0 的项才存活，只剩 N 个对角项"),
         ("02", "Sidon 计数 → L⁴", "对角 1 个、非对角 2 个，R = 2N² − N"),
         ("03", "Hölder 插值 → L¹", "θ = 1/3 由 1/2 = θ + (1−θ)/4 解出")]
for i, (n, t, d) in enumerate(items):
    y = 2.14 + i * 1.22
    tf = tb(s, M, y - 0.02, 0.6, 0.3)
    para(tf, n, size=11, bold=True, color=BLUE_L, first=True)
    tf = tb(s, M + 0.55, y - 0.04, 4.9, 0.3)
    para(tf, t, size=13.5, bold=True, color=INK, first=True)
    tf = tb(s, M + 0.55, y + 0.30, 4.9, 0.5)
    para(tf, d, size=9.5, color=GRAY, first=True, line=1.3)

vline(s, 6.42, 1.86, 5.42, LINE, 0.75)

tf = tb(s, 6.78, 1.84, 5.6, 0.22)
para(tf, "四个陷阱", size=9, bold=True, color=RED, spc=180, first=True)

traps = [("因子 2 到处加", "对角项 (a,a) 交换后不变，系数是 1"),
         ("有序对 / 无序对混用", "非对角无序对贡献 4 个有序四元组"),
         ("用 Cauchy–Schwarz 证下界", "它给的是上界，方向反了"),
         ("忘记 N = 1 边界", "S = {n} 时三个积分都是 1")]
for i, (t, d) in enumerate(traps):
    y = 2.10 + i * 0.82
    rect(s, 6.78, y + 0.07, 0.10, 0.10, fill=RED)
    tf = tb(s, 7.00, y - 0.03, 5.2, 0.28)
    para(tf, t, size=11.5, bold=True, color=INK, first=True)
    tf = tb(s, 7.00, y + 0.27, 5.2, 0.28)
    para(tf, d, size=9, color=GRAY, first=True)

card(s, M, 5.30, 11.43, 0.52, fill=WHITE, line=LINE, accent=GOLD)
tf = tb(s, M + 0.24, 5.42, 11.0, 0.3)
rich(tf, [("一句话：", {"bold": True, "color": GOLD}),
          ("唯一性条件把“和”的原像压到 1 或 2，积分随即变成可数的组合计数，再用插值接到 L¹。", {"color": INK2})],
     size=10.5, first=True)

tf = tb(s, M, 5.98, 11.4, 0.22)
para(tf, "证明链条", size=8.5, bold=True, color=GRAY, spc=180, first=True)
chain = ["条件", "展开", "积分", "计数", "不等式", "结论"]
cx = M
for i, t in enumerate(chain):
    wbox = 1.55
    rect(s, cx, 6.24, wbox, 0.36, fill=NAVY if i == len(chain) - 1 else SKY)
    tf = tb(s, cx, 6.31, wbox, 0.22)
    para(tf, t, size=9.5, color=WHITE if i == len(chain) - 1 else INK2,
         align=PP_ALIGN.CENTER, first=True)
    cx += wbox
    if i < len(chain) - 1:
        tf = tb(s, cx, 6.29, 0.34, 0.22)
        para(tf, "›", size=12, color=BLUE, align=PP_ALIGN.CENTER, first=True)
        cx += 0.34

notes(s, "三条主线对应三种技术：正交性负责 L²，Sidon 计数负责 L⁴，Hölder 插值负责把两个矩接到 L¹。"
         "四个陷阱里最值钱的是第一条：因子 2 只在非对角出现。"
         "另外提醒一句，由 |f(0)| = N 可以直接得到 ∫|f| ≥ 1，说明题目下界很宽松——"
         "所以真正的考点是插值这条路，而不是这个常数。")

# ================================================================== 10 结尾
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s, NAVY)
rect(s, 0, 0, 0.09, H, fill=GOLD)

tf = tb(s, M, 0.66, 8.0, 0.24)
para(tf, "CONCLUSION", size=9, bold=True, color="7FA6CF", spc=300, first=True)
tf = tb(s, M, 1.06, 8.0, 0.6)
para(tf, "核心结论", size=32, bold=True, color=WHITE, first=True)
rect(s, M, 1.80, 1.6, 0.03, fill=GOLD)

cards = [("L² 范数", "p10_l2", "正交性 · 对角项"),
         ("L⁴ 范数", "p10_l4", "唯一性 + 有序对计数"),
         ("L¹ 下界", "p10_l1", "Hölder 插值 · θ = 1/3")]
for i, (lab, fid, sub) in enumerate(cards):
    x = M + i * 3.84
    rect(s, x, 2.22, 3.55, 2.05, fill=DARK_CARD, line=DARK_LINE, lw=0.75)
    tf = tb(s, x + 0.28, 2.42, 3.0, 0.22)
    para(tf, lab, size=9, bold=True, color="7FA6CF", spc=180, first=True)
    fimg(s, fid, cx=x + 1.78, cy=3.22, maxw=3.0)
    tf = tb(s, x + 0.28, 3.92, 3.0, 0.22)
    para(tf, sub, size=8.5, color="9FB6D0", first=True)

tf = tb(s, M, 5.02, 11.4, 0.32)
para(tf, "唯一性条件  →  每个和的原像 ≤ 2 个  →  L⁴ 可精确计数  →  与 L² 一起锁定 L¹",
     size=12, color="C7D8EA", first=True)
hline(s, M, RE, 5.52, DARK_LINE, 0.75)

tf = tb(s, M, 5.78, 11.4, 0.6)
para(tf, "方法关键词：正交性　·　Sidon 计数　·　对数凸性", size=10, color="8FA8C6", first=True, spc=60)

tf = tb(s, M, 6.62, 6.0, 0.3)
para(tf, "谢谢观看｜欢迎提问", size=11, color="7E97B6", first=True, spc=80)

notes(s, "收尾时把三条结论和方法一一对应：看到 L² 想正交性，看到 L⁴ 想四元组计数，"
         "看到“由两个矩推第三个矩”想 Hölder 插值。"
         "一句话总结：加性唯一性把每个和的原像压到 1 或 2 个，于是积分变成可数的组合计数，"
         "再与 L² 一起把 L¹ 从下方顶住。")

out = "加性唯一性条件下指数和的范数估计.pptx"
prs.save(out)
print("saved", out)

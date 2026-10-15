# -*- coding: utf-8 -*-
"""Build 实践题-说明与代码索引.docx (no PDF is produced)."""
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = r"D:\All_resource\大学\大一\人工智能导论\作业\第二次作业题"
OUT = rf"{ROOT}\实践题-说明与代码索引.docx"
CODE_DIR = rf"{ROOT}\代码"

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.top_margin, sec.bottom_margin = Cm(2.4), Cm(2.2)
sec.left_margin, sec.right_margin = Cm(2.6), Cm(2.4)

normal = doc.styles["Normal"]
normal.font.name = "Times New Roman"
normal.font.size = Pt(11)
normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
normal.paragraph_format.line_spacing = 1.4
normal.paragraph_format.space_after = Pt(4)


def set_run(run, ascii_font="Times New Roman", ea="宋体", size=11, bold=False, color=None):
    run.font.name = ascii_font
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), ea)
    if color:
        run.font.color.rgb = color


def para(text="", *, size=11, bold=False, indent=True, align=None,
         ea="宋体", before=0, after=4, color=None, ascii_font="Times New Roman"):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.4
    if indent:
        p.paragraph_format.first_line_indent = Pt(size * 2)
    if align is not None:
        p.alignment = align
    if text:
        set_run(p.add_run(text), ascii_font, ea, size, bold, color)
    return p


def h1(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(8)
    set_run(p.add_run(text), ea="黑体", size=15, bold=True,
            color=RGBColor(0x1F, 0x3B, 0x73))
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", "8"), ("w:space", "3"), ("w:color", "1F3B73")):
        bottom.set(qn(k), v)
    pbdr.append(bottom)
    pPr.append(pbdr)
    return p


def h2(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(5)
    set_run(p.add_run(text), ea="黑体", size=12, bold=True,
            color=RGBColor(0x2E, 0x5C, 0x9E))
    return p


def formula(text, size=12):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(8)
    set_run(p.add_run(text), ascii_font="Cambria Math", size=size, bold=True)
    return p


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def table(data, widths=None, size=10, header=True, mono_col=None):
    t = doc.add_table(rows=len(data), cols=len(data[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            cell = t.cell(i, j)
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.15
            is_head = header and i == 0
            fnt = "Consolas" if (mono_col is not None and j == mono_col and not is_head) else "Times New Roman"
            set_run(p.add_run(str(val)), ascii_font=fnt, ea="黑体" if is_head else "宋体",
                    size=size, bold=is_head)
            if is_head:
                shade(cell, "DCE6F1")
    if widths:
        for j, w in enumerate(widths):
            for row in t.rows:
                row.cells[j].width = Cm(w)
    return t


def code_block(text, size=8.5):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.05
    p.paragraph_format.left_indent = Pt(6)
    set_run(p.add_run(text), ascii_font="Consolas", ea="宋体", size=size)
    return p


# ============================================================ TITLE
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
t.paragraph_format.space_after = Pt(2)
set_run(t.add_run("人工智能导论 · 第二次作业题 · 实践题"), ea="黑体", size=19, bold=True,
        color=RGBColor(0x1F, 0x3B, 0x73))

st = doc.add_paragraph()
st.alignment = WD_ALIGN_PARAGRAPH.CENTER
st.paragraph_format.space_after = Pt(4)
set_run(st.add_run("原题 · 来源 · 提示词 · 代码文件索引"), ea="楷体", size=12,
        color=RGBColor(0x55, 0x55, 0x55))

info = doc.add_paragraph()
info.alignment = WD_ALIGN_PARAGRAPH.CENTER
info.paragraph_format.space_after = Pt(12)
set_run(info.add_run("姓名：____________　　学号：____________　　日期：____________"),
        size=10.5, color=RGBColor(0x66, 0x66, 0x66))

# ============================================================ 一、原题
h1("一、原题")
para("题目取自教材照片（本目录下的 IMG_20261015_185014.jpg），逐字转录如下：")
para("11. 设数列 {aₙ} 满足 a₁ = 1，aₙ₊₁ = aₙ + 1/aₙ（n = 1, 2, ⋯），证明数列 {aₙ} 发散，"
     "并求极限 lim(n→∞) aₙ²/n。")
formula("a₁ = 1,　aₙ₊₁ = aₙ + 1/aₙ　(n = 1, 2, ⋯)")
para("求证两件事：① 数列 {aₙ} 发散；② 求极限 lim(n→∞) aₙ²/n。", bold=True)

# ============================================================ 二、来源
h1("二、来源")
table([
    ["项目", "内容"],
    ["教材", "《工科数学分析习题课教程》"],
    ["位置", "第 17 页　第 11 题"],
    ["原题图片来源", "IMG_20261015_185014.jpg（本目录下教材拍照）"],
    ["题目类型", "数列极限证明（单调性/放缩 + 阶的估计）"],
], widths=[3.4, 12.4])

# ============================================================ 三、提示词
h1("三、提示词")
para("（按作业要求，此项留空。）")
box_p = doc.add_paragraph()
box_p.paragraph_format.space_before = Pt(4)
box_p.paragraph_format.space_after = Pt(6)
pPr = box_p._p.get_or_add_pPr()
pbdr = OxmlElement("w:pBdr")
for side in ("top", "left", "bottom", "right"):
    e = OxmlElement(f"w:{side}")
    for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "6"), ("w:color", "BFBFBF")):
        e.set(qn(k), v)
    pbdr.append(e)
pPr.append(pbdr)
set_run(box_p.add_run("\n\n\n"), size=11)

# ============================================================ 四、解答要点
h1("四、解答要点")
para("核心思路：直接看 aₙ₊₁ − aₙ = 1/aₙ 只能说明递增，判断不了发散；"
     "而 aₙ₊₁² − aₙ² = 2 + 1/aₙ² 把“常数 2”和 n 联系了起来，是关键一步。")

h2("1. 平方差分与恒等式")
formula("aₙ₊₁² − aₙ² = 2 + 1/aₙ²")
para("从 k = 1 累加到 n − 1，中间项逐项相消：")
formula("aₙ² = 2n − 1 + Sₙ,　其中 Sₙ = Σ(k=1…n−1) 1/aₖ²")

h2("2. 证明发散")
para("因 Sₙ > 0，有 aₙ² ≥ 2n − 1，故 aₙ ≥ √(2n − 1) → +∞，"
     "所以 {aₙ} 发散（趋于 +∞）。")

h2("3. 求极限")
para("两边除以 n：")
formula("aₙ²/n = 2 − 1/n + Sₙ/n")
para("由 aₖ ≥ √(2k − 1) > √(2k)/√2 得 1/aₖ² ≤ 2/(2k) = 1/k，于是")
formula("Sₙ ≤ Σ 1/k ≤ 1 + ln n　⟹　Sₙ/n ≤ (1 + ln n)/n → 0")
para("故", bold=True)
formula("lim(n→∞) aₙ²/n = 2")
para("数值验证（高精度计算）：n = 10³ 时为 2.003178，n = 10⁴ 时为 2.000433，"
     "n = 10⁵ 时为 2.000055，与理论值 2 一致；恒等式 aₙ² = 2n − 1 + Sₙ 在 n = 10⁵ 时"
     "误差小于 10⁻⁵³。")

# ============================================================ 五、代码文件索引
h1("五、代码文件索引")
para("全部临时代码保存在本目录下的 代码/ 文件夹中，清单如下：")
files = [
    ["文件名", "作用", "运行方式"],
    ["代码/sequence_numeric.py",
     "高精度（45 位）迭代计算 aₙ，检验恒等式 aₙ² = 2n − 1 + Sₙ，并给出 aₙ²/n 的收敛数据",
     "python sequence_numeric.py"],
    ["代码/make_figures.py",
     "用 Pillow 生成数值验证页的收敛曲线图与预留图片区域的占位图",
     "python make_figures.py"],
    ["代码/build_ppt.py",
     "以 东南大学PPT.pptx 为模板生成 实践题v1.pptx（删除 91 页示例页、沿用模板版式）",
     "python build_ppt.py"],
    ["代码/inspect_template.py",
     "解析模板的主题字体/配色与各版式的图片占位符几何，为排版提供依据",
     "python inspect_template.py"],
    ["代码/metrics.py",
     "第二次作业第二题（混淆矩阵指标）的计算与校验脚本",
     "python metrics.py"],
    ["代码/calculus.py",
     "第二次作业第四题（偏导数 z = x² + y² − x/y + xy）的数值校验脚本",
     "python calculus.py"],
]
table(files, widths=[4.4, 8.6, 3.0], size=9.5, mono_col=0)   # 4.4+8.6+3.0 = 16.0 cm

para("说明：脚本使用 Python 3 与 python-docx / python-pptx / Pillow 等库；"
     "运行 build_ppt.py 会直接覆盖生成 实践题v1.pptx。", before=6)

# ============================================================ 六、交付物
h1("六、交付物清单")
table([
    ["文件", "说明"],
    ["实践题v1.pptx", "由模板另存生成的演示文稿（12 页，未覆盖原始模板）"],
    ["实践题-说明与代码索引.docx", "本文件：原题、来源、留空的提示词、代码文件索引"],
    ["IMG_20261015_185014.jpg", "教材原题照片"],
    ["代码/", "全部临时脚本（6 个）"],
    ["figures/", "脚本生成的图片素材"],
    ["东南大学PPT.pptx", "原始模板（未改动，位于 课件/ 目录）"],
], widths=[6.4, 9.4], size=10)

# ============================================================ 附录：代码
h1("附录：代码留档")
para("以下为 代码/ 文件夹中主要脚本的完整内容，便于随作业一并提交。")
for fn in ("sequence_numeric.py", "make_figures.py", "build_ppt.py"):
    path = os.path.join(CODE_DIR, fn)
    h2(f"代码/{fn}")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            code_block(f.read(), size=8)
    else:
        para(f"（未找到 {fn}）")

doc.save(OUT)
print("saved:", OUT)

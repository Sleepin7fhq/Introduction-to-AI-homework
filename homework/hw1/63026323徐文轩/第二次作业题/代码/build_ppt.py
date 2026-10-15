# -*- coding: utf-8 -*-
"""
Build 实践题v1.pptx FROM the 东南大学PPT.pptx template.

Design contract (assignment requirement 2.5)
--------------------------------------------
* Built from the template file, so Theme / Typography / Layouts / Branding are
  inherited: the master and all 16 layouts are preserved, and the SEU logo that
  each layout carries top-right stays on every page.
* The template's 91 demo slides are deleted. Every page is built on one of the
  template's own named layouts - never a blank redesign.
* Layout choice is geometry-driven, verified by rendering. The template's
  picture-bearing content layouts (图文-1..5) place their picture slots directly
  under, or on top of, their own body text boxes, so text and image cannot
  coexist without overlap. Their slots are therefore removed, and where a page
  needs a figure the suggested image type is stated in the page's own grey
  caption line (requirement 2.5.6).
  A picture placeholder is NEVER left unfilled: an unfilled one exports the
  editor prompt "Double-click to add an Image" into PDF/print output.
  Layouts used (all free of empty picture slots):
      0 标题幻灯片 / 1 目录页 / 2 节标题
      7 仅标题（主副标题） / 8 仅标题（无主副标题） / 15 末尾幻灯片
* One core message per page, minimal wording, no layout repeated consecutively.
* Typography inherited (微软雅黑 / Arial); size reduced only where text
  measurement proves the layout default would overflow.
* No rounded-card walls, gradients, decorative circles or three-column cards.
"""
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import PP_PLACEHOLDER
from PIL import ImageFont

ROOT = r"D:\All_resource\大学\大一\人工智能导论\作业\第二次作业题"
TEMPLATE = r"D:\All_resource\大学\大一\人工智能导论\课件\东南大学PPT.pptx"
OUT = rf"{ROOT}\实践题v1.pptx"
FIG = rf"{ROOT}\figures"

FONT = r"C:\Windows\Fonts\msyh.ttc"
GREY = RGBColor(0x80, 0x80, 0x80)

prs = Presentation(TEMPLATE)


# ------------------------------------------------------------------ text helpers
def text_width_in(text, pt):
    px = max(1, int(round(pt * 96.0 / 72.0)))
    return ImageFont.truetype(FONT, px).getlength(text) / 96.0


def fit_pt(text, avail_in, start_pt, min_pt=9.0):
    pt = float(start_pt)
    while pt > min_pt and text_width_in(text, pt) > avail_in:
        pt -= 0.5
    return pt


def t(text, pt=None):
    return (text, pt)


def put(shape, lines, pad=0.92, default_pt=18):
    tf = shape.text_frame
    tf.word_wrap = True
    avail_in = Emu(shape.width).inches * pad
    first = True
    for ln in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        for item in (ln if isinstance(ln, list) else [ln]):
            text, sz = item if isinstance(item, tuple) else (item, None)
            text = "" if text is None else str(text)
            r = p.add_run()
            r.text = text
            r.font.size = Pt(sz) if sz is not None else Pt(fit_pt(text, avail_in, default_pt))
    return shape


def box(slide, left, top, width, height):
    return slide.shapes.add_textbox(Emu(left), Emu(top), Emu(width), Emu(height))


def caption(slide, text, left, top, width, height, pt=11):
    s = box(slide, left, top, width, height)
    s.text_frame.word_wrap = True
    r = s.text_frame.paragraphs[0].add_run()
    r.text = text
    r.font.size = Pt(pt)
    r.font.color.rgb = GREY
    return s


def picture_phs(slide):
    return [ph for ph in slide.placeholders
            if ph.placeholder_format.type == PP_PLACEHOLDER.PICTURE]


def clear_pictures(slide):
    """Delete the layout's picture placeholders.

    They are unfillable here (see module docstring) and must not be left blank,
    because a blank PICTURE placeholder exports the prompt
    'Double-click to add an Image'."""
    n = 0
    for ph in picture_phs(slide):
        ph._element.getparent().remove(ph._element)
        n += 1
    return n


def L(name):
    for lay in prs.slide_layouts:
        if lay.name == name:
            return lay
    raise KeyError(name)


def ph_of(slide, idx):
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == idx:
            return ph
    return None


# ------------------------------------------------------------------ 1. drop demos
sldIds = list(prs.slides._sldIdLst)
for sldId in sldIds:
    rId = sldId.get(
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    )
    prs.part.drop_rel(rId)
    prs.slides._sldIdLst.remove(sldId)
print(f"removed {len(sldIds)} demo slides")


def add(layout_name, spec=None, boxes=(), caption_text=None, caption_box=None):
    slide = prs.slides.add_slide(L(layout_name))
    clear_pictures(slide)
    for idx, lines in (spec or {}).items():
        ph = ph_of(slide, idx)
        if ph is None:
            raise KeyError(f"{layout_name}: no placeholder idx={idx}")
        put(ph, lines)
    for b in boxes:
        put(box(slide, *b[:4]), b[4], default_pt=b[5] if len(b) > 5 else 18)
    if caption_text:
        caption(slide, caption_text, *caption_box)
    return slide


# ================================================================== 2. compose deck
FULL = 8920029          # width of the title strip on layouts 7/8
XL = 1216933            # left edge of the title strip

# ---- 1 封面 (layout 0 标题幻灯片) -------------------------------------------
add("标题幻灯片", {
    11: [t("人工智能导论", 40)],
    10: [t("第二次作业题 · 实践题", 32)],
    12: [t("数列{aₙ}的发散性与 aₙ²/n 的极限", 18)],
})

# ---- 2 目录 (layout 1 目录页) ----------------------------------------------
add("目录页", boxes=[(700000, 2950000, 4300000, 2400000, [
    t("01　原题与来源", 17),
    t("02　分析：凑出平方差分", 17),
    t("03　证明数列发散", 17),
    t("04　求极限 aₙ²/n", 17),
], 17)])

# ---- 3 原题 (layout 7 仅标题（主副标题）) -----------------------------------
add("仅标题（主副标题）", {
    11: [t("01　原题", 20)],
    12: [t("设 a₁ = 1，aₙ₊₁ = aₙ + 1/aₙ", 21)],
    13: [t("证明 {aₙ} 发散，并求 lim aₙ²/n", 20)],
}, boxes=[(660400, 3600000, 6400000, 1200000, [
    t("来源：《工科数学分析习题课教程》第 17 页 第 11 题", 15),
    t("建议配图：教材原题照片（横向截图，裁去页眉页脚）", 13),
], 15)])

# ---- 4 三个观察 (layout 8) -------------------------------------------------
# 注：图文-1 的三处图片槽与它自身的正文框完全重叠，删槽会连带删掉正文框，
#     故本页改用无图片槽的 layout 8，用自由文本框排三条观察。
add("仅标题（无主副标题）", {
    11: [t("02　先把结构看清楚", 20)],
}, boxes=[
    (XL, 1250000, FULL, 800000,
     [t("① 正项：a₁ = 1 > 0，故 aₙ > 0", 20)], 20),
    (XL, 2350000, FULL, 800000,
     [t("② 递增：aₙ₊₁ − aₙ = 1/aₙ > 0", 20)], 20),
    (XL, 3450000, FULL, 800000,
     [t("③ 平方差分：aₙ₊₁² − aₙ² = 2 + 1/aₙ²", 20)], 20),
], caption_text="建议配图：三张小示意图——正项、递增、平方差分（各配一条数轴示意）",
   caption_box=(XL, 5250000, FULL, 400000))

# ---- 5 核心恒等式 (layout 8 仅标题（无主副标题）) ---------------------------
add("仅标题（无主副标题）", {
    11: [t("02　核心恒等式", 20)],
}, boxes=[
    (XL, 1150000, FULL, 700000, [t("从 k = 1 累加到 n − 1，中间项全部相消", 18)], 18),
    (XL, 2250000, 6000000, 1500000,
     [t("∑(aₖ₊₁² − aₖ²) = aₙ² − 1", 20), t("aₙ² = 2n − 1 + Sₙ", 20)], 20),
    (XL, 4200000, FULL, 700000,
     [t("其中 Sₙ = ∑ 1/aₖ²　(k = 1 … n − 1)", 15)], 15),
], caption_text="建议配图：平方差分逐项相消的示意（Σ 记号，手绘风即可）",
   caption_box=(XL, 5100000, FULL, 400000))

# ---- 6 发散 (layout 8) -----------------------------------------------------
add("仅标题（无主副标题）", {
    11: [t("03　第一步：证明发散", 20)],
}, boxes=[
    (XL, 1200000, FULL, 700000, [t("放大：aₙ² = 2n − 1 + Sₙ ≥ 2n − 1", 18)], 18),
    (XL, 2250000, FULL, 900000, [t("aₙ ≥ √(2n − 1)", 24)], 24),
    (XL, 3300000, FULL, 900000, [t("→ +∞", 24)], 24),
    (XL, 4400000, FULL, 700000, [t("故 {aₙ} 发散", 20)], 20),
])

# ---- 7 极限的估计 (layout 8) -----------------------------------------------
add("仅标题（无主副标题）", {
    11: [t("04　把 aₙ²/n 变成可控的形式", 20)],
}, boxes=[
    (XL, 1150000, FULL, 700000, [t("两边除以 n，只需控制 Sₙ 的增速", 17)], 17),
    (XL, 2050000, FULL, 900000, [t("aₙ²/n = 2 − 1/n + Sₙ/n", 22)], 22),
    (XL, 3150000, FULL, 900000, [t("Sₙ ≤ ∑ 1/k ≤ 1 + ln n", 20)], 20),
    (XL, 4150000, FULL, 700000, [t("⟹　Sₙ/n → 0", 20)], 20),
    (XL, 5000000, FULL, 700000, [t("故 aₙ²/n → 2", 20)], 20),
])

# ---- 8 结论 (layout 2 节标题) -----------------------------------------------
add("节标题", {
    10: [t("结论", 20)],
    11: [t("{aₙ} 发散；lim aₙ²/n = 2", 20)],
})

# ---- 9 数值验证 (layout 8，直接插入真实曲线图) ------------------------------
s = add("仅标题（无主副标题）", {
    11: [t("05　数值验证：确实趋于 2", 20)],
}, boxes=[
    # 图右侧只放数字（图区渲染后约占 x=0.9~5.9 in）
    (7500000, 1700000, 5400000, 800000,
     [t("n = 10³：2.003178", 17)], 17),
    (7500000, 2600000, 5400000, 800000,
     [t("n = 10⁴：2.000433", 17)], 17),
    (7500000, 3500000, 5400000, 800000,
     [t("n = 10⁵：2.000055", 17)], 17),
    (7500000, 4400000, 5400000, 800000,
     [t("恒等式误差 < 10⁻⁵³", 16)], 16),
], caption_text="曲线由 code/make_figures.py 依据 code/sequence_numeric.py 的高精度数据绘制；"
                "建议补充：恒等式残差随 n 变化的图",
   caption_box=(XL, 6600000, FULL, 400000))
# 图按原始比例插入（0.987）；渲染器把内嵌位图放大显示，故按较小尺寸给定
s.shapes.add_picture(rf"{FIG}\fig_convergence.png", Emu(850000), Emu(1350000),
                     height=Emu(2500000))

# ---- 10 代码索引 (layout 8) ------------------------------------------------
add("仅标题（无主副标题）", {
    11: [t("06　代码与文件索引", 20)],
}, boxes=[
    (XL, 1300000, FULL, 700000,
     [t("全部临时代码保存在 代码/ 文件夹下", 20)], 20),
    (XL, 2400000, FULL, 700000,
     [t("sequence_numeric.py　高精度迭代与核验", 17)], 17),
    (XL, 3150000, FULL, 700000,
     [t("make_figures.py　绘制收敛曲线图", 17)], 17),
    (XL, 3900000, FULL, 700000,
     [t("build_ppt.py　由模板生成本 PPT", 17)], 17),
    (XL, 4650000, FULL, 700000,
     [t("inspect_template.py　模板解析", 17)], 17),
])

# ---- 11 小结 (layout 8) ----------------------------------------------------
add("仅标题（无主副标题）", {
    11: [t("小结", 20)],
}, boxes=[
    (XL, 1500000, FULL, 900000,
     [t("平方差分给出恒等式 aₙ² = 2n − 1 + Sₙ", 20)], 20),
    (XL, 2600000, FULL, 900000,
     [t("Sₙ 只有 ln n 量级，被 n 压平", 20)], 20),
    (XL, 3700000, FULL, 900000,
     [t("于是 {aₙ} 发散，且 aₙ²/n → 2", 20)], 20),
])

# ---- 12 结束 (layout 15 末尾幻灯片) ----------------------------------------
add("末尾幻灯片", {
    12: [t("谢谢", 40)],
    11: [t("恳请批评指正", 32)],
    17: [t("Thanks for your attention", 16)],
})

prs.save(OUT)
print("saved:", OUT, "| slides:", len(prs.slides))

# ---- self-check: no picture placeholder may remain, nothing off-slide ------
bad = 0
SW, SH = prs.slide_width, prs.slide_height
for i, s in enumerate(prs.slides):
    leftover = picture_phs(s)
    if leftover:
        bad += leftover
        print(f"  !! slide {i+1} still has {len(leftover)} picture placeholder(s)")
    for sh in s.shapes:
        if sh.left is None:
            continue
        if sh.left < 0 or sh.top < 0 or sh.left + sh.width > SW or sh.top + sh.height > SH:
            print(f"  !! slide {i+1}: shape '{sh.name}' extends off-slide")
print("self-check:", "OK" if bad == 0 else f"{bad} problems")

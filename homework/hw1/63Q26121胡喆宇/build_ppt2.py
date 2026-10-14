# -*- coding: utf-8 -*-
"""
基于「东南大学PPT.pptx」模板生成：
《2025年全国Ⅰ卷数学压轴题（第19题）完整评分解答》
沿用模板的 Theme / Typography / Layout / Branding：
  - 主题色：accent1 = 445437（东南大学深绿）、accent2 = FFCC00（金）
  - 字体系统：Arial + 微软雅黑（Microsoft YaHei）
  - 版式：标题幻灯片 / 仅标题 / 末尾幻灯片 等
  - 品牌元素：校训「止于至善」、Logo、背景装饰图形（保留在版式中）
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

TEMPLATE = r'D:\AI\pptdemo\东南大学PPT.pptx'
OUTPUT = r'D:\AI\pptdemo\高考压轴题完整评分解答2.pptx'
EMBLEM = r'D:\AI\pptdemo\seu_emblem.png'  # 东南大学校徽（取自模板 image20.png）

# ---- 品牌色（取自模板 theme1.xml 的 clrScheme「SEU」）----
GREEN = RGBColor(0x44, 0x54, 0x37)   # accent1 东南大学深绿
GOLD  = RGBColor(0xB8, 0x8A, 0x00)   # accent2 金色（加深，保证正文对比度）
DARK  = RGBColor(0x21, 0x21, 0x21)   # 正文深灰
GRAY  = RGBColor(0x59, 0x59, 0x59)   # 次要说明
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT = '微软雅黑'  # 模板 East Asian 字体（theme major/minor 的 ea）

# ----------------------------------------------------------------------
# 基础工具
# ----------------------------------------------------------------------
def set_run(run, size=15, bold=False, color=DARK, italic=False):
    run.font.name = FONT          # 设置 latin typeface（ea 由主题继承 = 微软雅黑）
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color


def clear_slides(prs):
    """删除模板中全部演示幻灯片，保留母版/版式/主题/品牌元素。"""
    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst):
        rId = sldId.get(qn('r:id'))
        prs.part.drop_rel(rId)
        sldIdLst.remove(sldId)


def finalize_slide(slide, page_no):
    """在每个新幻灯片上补回品牌页脚：校训「止于至善」+ 页码。

    python-pptx 的 add_slide 不会把 DATE/FOOTER/SLIDE_NUMBER 占位符从版式克隆到
    幻灯片上，因此这里用文本框在版式相同位置手动补回，保持模板品牌元素。
    """
    # 校训（模板 DATE 占位符位置：0.72, 6.82）
    tf = add_box(slide, 0.72, 6.82, 3.66, 0.40)
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = '止于至善'; set_run(r, size=12, color=GRAY)
    # 页码（模板 SLIDE_NUMBER 占位符位置：9.60, 6.82，右对齐）
    tf = add_box(slide, 9.60, 6.82, 3.00, 0.40)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    r = p.add_run(); r.text = str(page_no); set_run(r, size=12, color=GRAY)


def set_ph(slide, idx, text, size=20, bold=False, color=DARK, align=None):
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == idx:
            tf = ph.text_frame
            tf.text = text
            p = tf.paragraphs[0]
            if align is not None:
                p.alignment = align
            for run in p.runs:
                set_run(run, size=size, bold=bold, color=color)
            return ph
    return None


def add_box(slide, x, y, w, h):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    return tf


def add_emblem(slide, x, y, size):
    """加入东南大学校徽（圆形透明背景，按正方形尺寸放置）。"""
    return slide.shapes.add_picture(EMBLEM, Inches(x), Inches(y), Inches(size), Inches(size))


def render_blocks(tf, blocks):
    """blocks: list of (kind, text)；kind ∈ h/b/n/r/gap"""
    first = True
    for kind, text in blocks:
        if kind == 'gap':
            p = tf.add_paragraph()
            p.space_after = Pt(4)
            continue
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        run = p.add_run()
        run.text = text
        if kind == 'h':
            set_run(run, size=16, bold=True, color=GREEN)
            p.space_before = Pt(10)
            p.space_after = Pt(4)
        elif kind == 'b':
            set_run(run, size=15, bold=False, color=DARK)
            p.space_before = Pt(2)
            p.space_after = Pt(3)
        elif kind == 'n':
            set_run(run, size=13, bold=False, color=GRAY)
            p.space_before = Pt(1)
            p.space_after = Pt(3)
        elif kind == 'r':
            set_run(run, size=16, bold=True, color=GREEN)
            p.space_before = Pt(8)
            p.space_after = Pt(3)


def content_slide(prs, layout8, title, blocks, page_no):
    slide = prs.slides.add_slide(layout8)
    set_ph(slide, 11, title, size=20, bold=True, color=GREEN)
    finalize_slide(slide, page_no)
    tf = add_box(slide, 0.72, 1.28, 11.9, 5.4)
    render_blocks(tf, blocks)
    return slide


# ----------------------------------------------------------------------
# 构建
# ----------------------------------------------------------------------
prs = Presentation(TEMPLATE)
clear_slides(prs)
assert len(prs.slides._sldIdLst) == 0, 'slides not cleared'

L_TITLE = prs.slide_layouts[0]   # 标题幻灯片
L_BLANK = prs.slide_layouts[8]   # 仅标题（无主副标题）

page = 0

# ================= 第 1 页：标题页 =================
page += 1
s = prs.slides.add_slide(L_TITLE)
set_ph(s, 11, '2025 年全国高考 · 新课标Ⅰ卷 · 数学', size=20, bold=True, color=GOLD)
set_ph(s, 10, '压轴题 · 完整评分解答', size=34, bold=True, color=DARK)
set_ph(s, 12, 'Scoring & Full Solution — The Final Problem (No.19)', size=15, color=GRAY)
finalize_slide(s, page)
# 东南大学校徽（左下角品牌印章）
add_emblem(s, 0.75, 4.55, 1.35)
# 补充信息行（校徽右侧）
tf = add_box(s, 2.35, 4.60, 4.6, 1.2)
p = tf.paragraphs[0]; r = p.add_run(); r.text = '讲解视角：资深高考数学阅卷老师'; set_run(r, 14, False, GRAY)
p = tf.add_paragraph(); r = p.add_run(); r.text = '面向对象：高三备考学生'; set_run(r, 14, False, GRAY)
p = tf.add_paragraph(); r = p.add_run(); r.text = '第 19 题（满分 17 分）'; set_run(r, 14, False, GRAY)

# ================= 第 2 页：审题与考点 =================
page += 1
content_slide(prs, L_BLANK, '审题与考点', [
    ('h', '题目'),
    ('b', '设函数 f(x) = 5cos x − cos 5x。'),
    ('b', '(1) 求 f(x) 在 [0, π/4] 上的最大值；'),
    ('b', '(2) 给定 θ ∈ (0, π)，设 a 为实数，证明：存在 y ∈ [a−θ, a+θ]，使 cos y ≤ cos θ；'),
    ('b', '(3) 若存在 φ，使对任意 x 都有 5cos x − cos(5x+φ) ≤ b，求 b 的最小值。'),
    ('h', '已知与未知'),
    ('b', '已知：f(x)=5cos x − cos 5x；θ∈(0,π)、a∈R；φ 为可自由选取的参数。'),
    ('b', '未知：(1) 区间最大值；(2) 一个存在性结论；(3) b 的最优下界，即 min φ [ max x (5cos x − cos(5x+φ)) ]。'),
    ('h', '可能考点'),
    ('b', '① 三角恒等变换（和差化积、cos5x 展开） ② 导数与单调性求最值 ③ 基本不等式'),
    ('b', '④ 余弦函数解集与周期性 ⑤ 区间覆盖 + 反证法 ⑥ 特值法与上下界夹逼'),
], page)

# ================= 第 3 页：第(1)问 分析与方法一 =================
page += 1
content_slide(prs, L_BLANK, '第(1)问 · 分析与方法一（导数法）', [
    ('b', '目标：求 f(x) = 5cos x − cos 5x 在 [0, π/4] 上的最大值。'),
    ('n', '分析：f 可导，用导数判断单调性求最值（通法）。'),
    ('b', '① 求导：f \'(x) = −5sin x + 5sin 5x = 5(sin 5x − sin x)。'),
    ('b', '② 和差化积：sin 5x − sin x = 2cos 3x · sin 2x，故 f \'(x) = 10cos 3x · sin 2x。'),
    ('b', '③ x ∈ (0, π/4) 时，2x ∈ (0, π/2)，故 sin 2x > 0，f \'(x) 的符号由 cos 3x 决定。'),
    ('b', '④ 0 < x < π/6：3x ∈ (0, π/2)，cos 3x > 0 → f \'(x) > 0，f 递增；'),
    ('b', '   π/6 < x < π/4：3x ∈ (π/2, 3π/4)，cos 3x < 0 → f \'(x) < 0，f 递减。'),
    ('b', '⑤ 故 f 在 (0, π/6) 递增、在 (π/6, π/4) 递减，最大值在 x = π/6 处取得。'),
    ('b', '⑥ 计算：f(π/6) = 5cos(π/6) − cos(5π/6) = 5·(√3/2) − (−√3/2) = 3√3。'),
    ('n', '注意：cos(5π/6) = cos(π − π/6) = −cos(π/6) = −√3/2（负号不能丢）。'),
    ('r', '结论：f(x) 在 [0, π/4] 上的最大值为 3√3。'),
], page)

# ================= 第 4 页：第(1)问 方法二 =================
page += 1
content_slide(prs, L_BLANK, '第(1)问 · 方法二（恒等变换 + 基本不等式）', [
    ('n', '思路：把 cos5x 展开成 cos x 的多项式，再用五元均值不等式，避免求导。'),
    ('b', '① 切比雪夫多项式：cos 5x = 16cos⁵x − 20cos³x + 5cos x。'),
    ('b', '② 代入：f(x) = 20cos³x − 16cos⁵x = 4cos³x(5 − 4cos²x)。'),
    ('b', '③ 因式分解：5 − 4cos²x = (√5 − 2cos x)(√5 + 2cos x)。'),
    ('b', '   在 [0, π/4] 上 cos x ≥ √2/2 > 0，且 √5 − 2cos x > 0（因 cos x ≤ 1 < √5/2）。'),
    ('b', '④ 取正数 A=(√15+3)/4、B=(√15−3)/4，满足 A−B=3/2、A+B=√15/2、AB=3/8。'),
    ('b', '⑤ 对五数 cosx、cosx、cosx、A(√5−2cosx)、B(√5+2cosx) 用均值：'),
    ('b', '   五数和 = √5(A+B) + (3−2A+2B)cosx = √5·√15/2 + 0 = 5√3/2（常数）。'),
    ('b', '⑥ 故 f(x) ≤ 4·(√3/2)⁵·(1/AB) = 4·(9√3/32)·(8/3) = 3√3。'),
    ('b', '⑦ x = π/6 时 cos x = √3/2，五数相等，等号成立，f(π/6) = 3√3。'),
    ('r', '结论：最大值为 3√3（与方法一一致）。'),
], page)

# ================= 第 5 页：第(1)问 比较与得分点 =================
page += 1
content_slide(prs, L_BLANK, '第(1)问 · 两种方法比较与得分点', [
    ('h', '两种方法比较'),
    ('b', '方法一（导数法）：系统、稳妥、步骤清晰，是考场首选；需写清单调性依据。'),
    ('b', '方法二（均值法）：不需要求导、形式更漂亮；难点在构造 A、B，使五数和恒为常数。'),
    ('h', '得分点设置（本问约 7 分，模拟评分细则）'),
    ('b', '① 正确求导 f \'(x) = −5sin x + 5sin 5x（或 =10cos 3x·sin 2x）—— 2 分'),
    ('b', '② 符号分析：f 在 (0, π/6) 递增、在 (π/6, π/4) 递减 —— 3 分'),
    ('b', '③ 计算 f(π/6) = 3√3 并写结论 —— 2 分'),
    ('n', '阅卷提示：①求导错误整问失分；②只写结果不写单调性，最多给一半。'),
], page)

# ================= 第 6 页：第(2)问 分析与方法一 =================
page += 1
content_slide(prs, L_BLANK, '第(2)问 · 分析与方法一（解集 + 反证）', [
    ('b', '目标：给定 θ∈(0,π)、a∈R，证明存在 y ∈ [a−θ, a+θ] 使 cos y ≤ cos θ。'),
    ('n', '分析：写出 cos y ≤ cos θ 的解集（“好区间”），说明长度为 2θ 的区间不能整个落在“坏区间”内。'),
    ('b', '① cos y ≤ cos θ 的解集：∪(k∈Z) [2kπ+θ, 2kπ+2π−θ]。'),
    ('n', '   依据：余弦在每个周期 [2kπ, 2kπ+2π] 内先减后增，cos y = cos θ 恰在两端取到。'),
    ('b', '② 反设：对一切 y ∈ [a−θ, a+θ] 都有 cos y > cos θ，即区间全落在坏集 ∪(k∈Z)(2kπ−θ, 2kπ+θ) 内。'),
    ('b', '③ 因 [a−θ, a+θ] 连通、各坏区间互不相交，故必含于某个 (2kπ−θ, 2kπ+θ)。'),
    ('b', '④ 于是 2kπ−θ < a−θ 且 a+θ < 2kπ+θ，即 2kπ < a 且 a < 2kπ，矛盾。'),
    ('r', '结论：反设不成立，故存在 y ∈ [a−θ, a+θ] 使 cos y ≤ cos θ。'),
], page)

# ================= 第 7 页：第(2)问 方法二 =================
page += 1
content_slide(prs, L_BLANK, '第(2)问 · 方法二（取整函数法）', [
    ('n', '思路：用“取整”构造一个整数 k，使区间与某个好区间必然相交。'),
    ('b', '① 解集同前：∪(k∈Z) [2kπ+θ, 2(k+1)π−θ]。'),
    ('b', '② 若 [a−θ, a+θ] 与每个好区间都不相交，则对每个整数 k 必有二者之一：'),
    ('b', '   a+θ < 2kπ+θ（即 k > a/2π），或 a−θ > 2(k+1)π−θ（即 k < a/2π − 1）。'),
    ('b', '③ 取整数 k 满足 a/2π − 1 < k ≤ a/2π（即 k = a/2π 的整数部分）。'),
    ('b', '   该 k 既不满足 k > a/2π，也不满足 k < a/2π − 1，矛盾。'),
    ('r', '结论：故存在 y ∈ [a−θ, a+θ] 使 cos y ≤ cos θ。'),
    ('n', '两法本质：坏区间长 2θ 恰等于 [a−θ, a+θ] 的长度，严格“装不下”。'),
], page)

# ================= 第 8 页：第(2)问 比较与得分点 =================
page += 1
content_slide(prs, L_BLANK, '第(2)问 · 方法比较与得分点', [
    ('h', '两种方法比较'),
    ('b', '方法一（解集 + 连通性反证）：直观、几何直觉强，推荐考场使用。'),
    ('b', '方法二（取整函数法）：更代数化、更严谨，本质相同但表达方式不同。'),
    ('h', '得分点设置（本问约 5 分，模拟评分细则）'),
    ('b', '① 正确写出解集 ∪(k∈Z)[2kπ+θ, 2kπ+2π−θ] —— 2 分'),
    ('b', '② 反证并指出区间必落入某个坏区间内 —— 2 分'),
    ('b', '③ 推出 2kπ < a 且 a < 2kπ 矛盾（或取整构造矛盾），完成证明 —— 1 分'),
    ('n', '阅卷提示：解集写错（如漏周期、端点写错）直接失分；反证假设不写清楚扣 1 分。'),
], page)

# ================= 第 9 页：第(3)问 分析与方法一（上界） =================
page += 1
content_slide(prs, L_BLANK, '第(3)问 · 分析与方法一（上界）', [
    ('b', '目标：求 b 的最小值。记 h_φ(x) = 5cos x − cos(5x+φ)。'),
    ('n', '即求 min φ [ max x h_φ(x) ]：先证“b=3√3 能做到”（上界），再证“任何 φ 都躲不开 3√3”（下界）。'),
    ('h', '上界：找一个 φ，使 h_φ(x) ≤ 3√3 恒成立'),
    ('b', '① 取 φ = 0，则 h₀(x) = 5cos x − cos 5x = f(x)。'),
    ('b', '② 若 cos x ≤ 0：f(x) = 5cos x − cos 5x ≤ 0 + 1 = 1 < 3√3。'),
    ('b', '③ 若 cos x ≥ 0：由第(1)问方法二，f(x) = 4cos³x(5−4cos²x) ≤ 3√3。'),
    ('b', '④ 故对一切 x ∈ R 有 f(x) ≤ 3√3，即取 φ=0、b=3√3 时恒成立。'),
    ('r', '⇒ b 的最小值 ≤ 3√3。'),
], page)

# ================= 第 10 页：第(3)问 方法一（下界） =================
page += 1
content_slide(prs, L_BLANK, '第(3)问 · 方法一（下界）', [
    ('h', '下界：任取 φ，都存在 x 使 h_φ(x) ≥ 3√3'),
    ('b', '① 在第(2)问取 θ = 5π/6、a = φ：存在 y ∈ [φ−5π/6, φ+5π/6] 使 cos y ≤ cos(5π/6) = −√3/2。'),
    ('b', '② 令 x = (y−φ)/5，则 x ∈ [−π/6, π/6]，故 |x| ≤ π/6 → cos x ≥ √3/2 → 5cos x ≥ 5√3/2。'),
    ('b', '③ 又 5x+φ = y，故 cos(5x+φ) = cos y ≤ −√3/2 → −cos(5x+φ) ≥ √3/2。'),
    ('b', '④ 相加：5cos x − cos(5x+φ) ≥ 5√3/2 + √3/2 = 3√3。'),
    ('b', '⑤ 故对任意 φ，都存在 x 使 h_φ(x) ≥ 3√3，即要 h_φ(x) ≤ b 恒成立，必须 b ≥ 3√3。'),
    ('r', '结论：b 的最小值 = 3√3（当 φ = 0 时取到）。'),
], page)

# ================= 第 11 页：第(3)问 方法二（上） =================
page += 1
content_slide(prs, L_BLANK, '第(3)问 · 方法二（|g|≤b 与三等分点 · 上）', [
    ('n', '思路：不依赖前两问，先由“对称性”得 |g_φ(x)| ≤ b，再取三个特殊点推出 b ≥ 3√3。'),
    ('b', '① 记 g_φ(x) = 5cos x − cos(5x+φ)。若 g_φ(x) ≤ b 对一切 x 成立：'),
    ('b', '② g_φ(x+π) = −5cos x − cos(5x+5π+φ) = −5cos x + cos(5x+φ) = −g_φ(x)。'),
    ('n', '   依据：cos(x+π) = −cos x，且 cos(5x+5π+φ) = −cos(5x+φ)（5π 与 π 同奇偶）。'),
    ('b', '③ 故 −g_φ(x) = g_φ(x+π) ≤ b，即 g_φ(x) ≥ −b，于是 |g_φ(x)| ≤ b 对一切 x 成立。'),
    ('b', '④ 令 m = φ/6 − π/6，分别取 x = −φ/6 + π/6、−φ/6 − π/6、−φ/6 + π/2 代入，得'),
    ('b', '   b ≥ 6|cos m|，b ≥ 6|cos(m+π/3)|，b ≥ 6|cos(m−π/3)|。'),
    ('n', '   验证第一式：此时 5x+φ = φ/6+5π/6，g_φ = 5cos(π/6−φ/6) − cos(φ/6+5π/6) = 6cos m。'),
], page)

# ================= 第 12 页：第(3)问 方法二（下） =================
page += 1
content_slide(prs, L_BLANK, '第(3)问 · 方法二（|g|≤b 与三等分点 · 下）', [
    ('b', '⑤ 由上页：|cos m|、|cos(m+π/3)|、|cos(m−π/3)| ≤ b/6。'),
    ('b', '⑥ 由 cos 2t = 2cos²t − 1 = 2|cos t|² − 1，得'),
    ('b', '   cos 2m、cos(2m+2π/3)、cos(2m−2π/3) ≤ 2(b/6)² − 1 = b²/18 − 1。'),
    ('b', '⑦ 若 b < 3√3，则 b²/18 − 1 < 27/18 − 1 = 1/2，故三个余弦都 < 1/2。'),
    ('b', '⑧ 但 2m、2m+2π/3、2m−2π/3 两两相差 2π/3，在单位圆上是三等分点（正三角形）。'),
    ('b', '   而 cos t ≥ 1/2 的弧段（长为 2π/3）必覆盖其中一个点，即某余弦 ≥ 1/2，矛盾。'),
    ('b', '⑨ 故 b < 3√3 不可能，必有 b ≥ 3√3；又 φ=0 时 b=3√3 可行。'),
    ('r', '结论：b 的最小值 = 3√3。'),
], page)

# ================= 第 13 页：第(3)问 比较与得分点 =================
page += 1
content_slide(prs, L_BLANK, '第(3)问 · 方法比较与得分点', [
    ('h', '两种方法比较'),
    ('b', '方法一（递进路线）：(1)→(2)→(3) 环环相扣，计算量小、最自然，是命题人设计的正解，考场首选。'),
    ('b', '方法二（独立证明）：不依赖前两问，但三个特殊点与“三等分点”的几何事实较难想到。'),
    ('h', '得分点设置（本问约 8 分，模拟评分细则）'),
    ('b', '① 取 φ=0 并利用 f(x) ≤ 3√3 得 b ≤ 3√3（上界）—— 2 分'),
    ('b', '② 借第(2)问取 θ=5π/6，构造 y 与 x=(y−φ)/5，得 5cos x ≥ 5√3/2 且 −cos(5x+φ) ≥ √3/2 —— 4 分'),
    ('b', '③ 相加得 h_φ(x) ≥ 3√3，推出 b ≥ 3√3 —— 1 分'),
    ('b', '④ 综合得 b 的最小值为 3√3 —— 1 分'),
], page)

# ================= 第 14 页：易错点与考场建议（倒数第二页） =================
page += 1
content_slide(prs, L_BLANK, '易错点与考场建议', [
    ('h', '易错点'),
    ('b', '① 区间是 [0, π/4]，不是 [0, π]（本题 π/6 恰在区间内，结论不变，但审题须看清）。'),
    ('b', '② cos(5π/6) = −√3/2，负号易丢。'),
    ('b', '③ θ ∈ (0, π)，cos θ 可为负（如 θ=5π/6 时 cos θ = −√3/2），不能默认 cos θ ≥ 0。'),
    ('b', '④ “存在 φ”表示 φ 可自由选取，最优取 φ=0；把 φ 当固定值会走偏。'),
    ('b', '⑤ 等号验证：f(π/6) = 3√3 确实达到上界（非端点，且在区间内）。'),
    ('h', '考场建议'),
    ('b', '① 第(1)问用导数法稳妥拿满，写清单调性依据；'),
    ('b', '② 第(2)问用“解集 + 反证”最快，关键是解集写对；'),
    ('b', '③ 第(3)问走递进路线：上界取 φ=0，下界借第(2)问取 θ=5π/6；'),
    ('b', '④ 时间建议 15–20 分钟；下界一时想不到，先写“取 φ=0 得 b ≤ 3√3”拿到上界分；'),
    ('b', '⑤ 每一步不等式注明依据（和差化积、均值、余弦单调性），避免“显然”。'),
], page)

# ================= 第 15 页：命题逻辑与考察意图（最后一页） =================
page += 1
s15 = content_slide(prs, L_BLANK, '命题人的命题逻辑与考察意图', [
    ('h', '命题逻辑：三问递进，层层铺垫'),
    ('b', '(1) 求 f(x)=5cos x − cos 5x 的最大值 → 提供“上界 3√3”这个工具。'),
    ('b', '(2) 证余弦存在性（区间覆盖）→ 为 (3) 的“下界”提供构造工具。'),
    ('b', '(3) 用 (1)(2) 合成：上界取 φ=0，下界借 (2) 取 θ=5π/6，夹出 b = 3√3。'),
    ('h', '考察意图：数学核心素养'),
    ('b', '① 逻辑推理：存在性证明、反证法、量词（∃φ、∀x）的严谨处理；'),
    ('b', '② 数学运算：三角恒等变换、导数、基本不等式；'),
    ('b', '③ 数学抽象与建模：把“求 b 的最小值”抽象为 min φ [ max x h_φ(x) ]；'),
    ('b', '④ 直观想象：三等分点、区间覆盖、周期性。'),
    ('r', '一句话总结：三问环环相扣，(1)(2) 为 (3) 铺路，考查“用旧结论解决新问题”的高阶能力。'),
], page)
# 校徽（右下角收尾印章）
add_emblem(s15, 11.25, 5.10, 1.50)

prs.save(OUTPUT)
print('saved:', OUTPUT)
print('total slides:', len(prs.slides._sldIdLst))

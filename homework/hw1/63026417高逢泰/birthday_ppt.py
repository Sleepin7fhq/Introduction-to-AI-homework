# -*- coding: utf-8 -*-
"""
用 python-pptx 生成《生日逻辑谜题》课堂演示文稿
—— 经典 Cheryl 生日问题（SASMO 2015）逐步推理 + Python 验证

运行：  python birthday_ppt.py
输出：  birthday.pptx（16:9，共 10 页，黄绿配色）

依赖：  pip install python-pptx
说明：  每页都用"空白版式 + 手写文本框/表格"实现，保证排版可控；
        字体默认 Microsoft YaHei / Consolas，若在 Mac/Linux 上放映，
        把 FONT / MONO 改成 苹方 / 等宽字体即可。
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# ============================================================ 主题：黄绿配色
DARK_GREEN   = RGBColor(0x1B, 0x5E, 0x20)   # 主色：深绿（标题/封面底）
GREEN        = RGBColor(0x2E, 0x7D, 0x32)   # 次色：标准绿（表头）
MID_GREEN    = RGBColor(0x66, 0x99, 0x33)   # 中间绿（装饰）
LIME         = RGBColor(0xAE, 0xE0, 0x5A)   # 亮黄绿（强调线/序号）
LIGHT_LIME   = RGBColor(0xE9, 0xF6, 0xD9)   # 浅黄绿（卡片/表格斑马）
BG           = RGBColor(0xF8, 0xFC, 0xF1)   # 页面底色
YELLOW       = RGBColor(0xF2, 0xA6, 0x1D)   # 黄（重点/答案）
LIGHT_YELLOW = RGBColor(0xFF, 0xF4, 0xCE)   # 浅黄（高亮行）
TEXT         = RGBColor(0x2A, 0x33, 0x2A)   # 正文
GRAY         = RGBColor(0x6E, 0x7A, 0x6E)   # 次要文字
WHITE        = RGBColor(0xFF, 0xFF, 0xFF)
CODE_BG      = RGBColor(0x15, 0x2B, 0x18)   # 代码块底
CODE_TX      = RGBColor(0xD9, 0xEC, 0xC6)   # 代码正文
CODE_KW      = RGBColor(0xFF, 0xD5, 0x4F)   # 代码高亮

FONT = "Microsoft YaHei"     # 中文字体
MONO = "Consolas"            # 代码字体

SLIDE_W, SLIDE_H = 13.333, 7.5
MARGIN = 0.72
CONTENT_W = SLIDE_W - 2 * MARGIN

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(SLIDE_W), Inches(SLIDE_H)
BLANK = prs.slide_layouts[6]


# ============================================================ 基础工具函数
def _set_font(run, font):
    """同时设置西文(latin)、东亚(ea)、复杂文种(cs) 字体，保证中文不乱码。"""
    run.font.name = font
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", font)


def add_rect(slide, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE,
             line_w=1.0, adj=None):
    """画一个矩形/圆角矩形；fill=None 表示无填充。"""
    shp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if adj is not None:                      # 圆角半径（仅圆角矩形可用）
        shp.adjustments[0] = adj
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(line_w)
    shp.shadow.inherit = False
    shp.text_frame.text = ""
    return shp


def add_text(slide, x, y, w, h, text, size=18, bold=False, color=TEXT,
             font=FONT, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             line_spacing=1.2, italic=False):
    """单个文本框（单段）。"""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color
        _set_font(r, font)
    return tb


def add_block(slide, x, y, w, h, items, default_size=16, line_spacing=1.25):
    """多段文本块。items 为 dict 列表：
       {"t": 文本, "size": 字号, "bold": 是否加粗, "color": 颜色,
        "bullet": "•" 前缀或 None, "before": 段前距(pt), "align": 对齐}"""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = it.get("align", PP_ALIGN.LEFT)
        p.line_spacing = it.get("line_spacing", line_spacing)
        p.space_before = Pt(it.get("before", 0))
        bullet = it.get("bullet")
        r = p.add_run()
        r.text = (bullet + " " if bullet else "") + it["t"]
        r.font.size = Pt(it.get("size", default_size))
        r.font.bold = it.get("bold", False)
        r.font.color.rgb = it.get("color", TEXT)
        _set_font(r, it.get("font", FONT))
    return tb


def style_cell(cell, text, size, bold, color, fill, align):
    cell.fill.solid()
    cell.fill.fore_color.rgb = fill
    cell.margin_left = cell.margin_right = Inches(0.08)
    cell.margin_top = cell.margin_bottom = Inches(0.03)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf = cell.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = 1.0
    for k, seg in enumerate(str(text).split("\n")):
        if k:                      # 单元格内换行用真正的 <a:br/>，不要裸 "\n"
            p.add_line_break()
        r = p.add_run()
        r.text = seg
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        _set_font(r, FONT)


def add_table(slide, data, x, y, col_w, row_h=0.44, size=13, header=True,
              header_fill=GREEN, body_fill=WHITE, alt_fill=LIGHT_LIME,
              highlight_rows=(), highlight_fill=LIGHT_YELLOW):
    """data[0] 为表头；col_w 为各列宽度（英寸）；highlight_rows 高亮行号。"""
    rows, cols = len(data), len(data[0])
    gf = slide.shapes.add_table(rows, cols, Inches(x), Inches(y),
                                Inches(sum(col_w)), Inches(row_h * rows))
    tbl = gf.table
    tbl.first_row = header
    tbl.horz_banding = False
    for i, w in enumerate(col_w):
        tbl.columns[i].width = Inches(w)
    for r in range(rows):
        tbl.rows[r].height = Inches(row_h)
        for c in range(cols):
            is_head = header and r == 0
            is_hl = r in highlight_rows
            if is_head:
                fill, color, bold = header_fill, WHITE, True
            elif is_hl:
                fill, color, bold = highlight_fill, DARK_GREEN, True
            elif alt_fill is not None and (r - (1 if header else 0)) % 2 == 1:
                fill, color, bold = alt_fill, TEXT, False
            else:
                fill, color, bold = body_fill, TEXT, False
            align = PP_ALIGN.LEFT if (c == 0 and not is_head) else PP_ALIGN.CENTER
            style_cell(tbl.cell(r, c), str(data[r][c]), size, bold, color, fill, align)
    return gf


def new_slide(bg=BG):
    s = prs.slides.add_slide(BLANK)
    add_rect(s, 0, 0, SLIDE_W, SLIDE_H, fill=bg)
    return s


def add_header(slide, title, kicker=None):
    """内容页统一页眉：左侧黄绿竖条 + 标题 + 下划线 + 右上角小标签。"""
    add_rect(slide, MARGIN, 0.46, 0.16, 0.62, fill=LIME)
    add_text(slide, MARGIN + 0.34, 0.40, CONTENT_W - 3.2, 0.7, title,
             size=27, bold=True, color=DARK_GREEN)
    if kicker:
        add_text(slide, SLIDE_W - MARGIN - 3.0, 0.52, 3.0, 0.4, kicker,
                 size=12, color=MID_GREEN, align=PP_ALIGN.RIGHT)
    add_rect(slide, MARGIN, 1.22, CONTENT_W, 0.035, fill=LIGHT_LIME)
    add_rect(slide, MARGIN, 1.22, 2.6, 0.035, fill=LIME)


def add_footer(slide, page):
    add_text(slide, MARGIN, 7.02, 8.0, 0.3,
             "Cheryl 生日问题（SASMO 2015）· 逻辑推理与 Python 验证",
             size=10, color=GRAY)
    add_text(slide, SLIDE_W - MARGIN - 2.0, 7.02, 2.0, 0.3, f"{page} / 10",
             size=10, color=GRAY, align=PP_ALIGN.RIGHT)


def add_progress(slide, active_index):
    """底部"候选日期"进度条：10 → 5 → 3 → 1。"""
    labels = ["初始候选 10 个", "第 1 步后 5 个", "第 2 步后 3 个", "第 3 步后 1 个"]
    counts = ["10", "5", "3", "1"]
    gap = 0.2
    w = (CONTENT_W - 3 * gap) / 4          # 四格等宽铺满内容区
    x, y, h = MARGIN, 6.25, 0.5
    for i, (lab, cnt) in enumerate(zip(labels, counts)):
        on = i == active_index
        add_rect(slide, x, y, w, h, fill=DARK_GREEN if on else WHITE,
                 line=None if on else LIGHT_LIME, line_w=1.2)
        add_rect(slide, x, y, 0.1, h, fill=YELLOW if on else LIME)
        add_text(slide, x + 0.22, y + 0.06, w - 0.4, 0.22, lab, size=11,
                 bold=on, color=WHITE if on else GRAY)
        add_text(slide, x + 0.22, y + 0.24, w - 0.4, 0.24, cnt + " 个候选",
                 size=12, bold=True, color=LIME if on else MID_GREEN)
        x += w + gap


def add_card(slide, x, y, w, h, title=None, title_color=DARK_GREEN,
             fill=WHITE, line=LIGHT_LIME, accent=LIME, title_size=15,
             body=None, body_size=14):
    """白底圆角卡片：左侧色条 + 可选标题 + 可选正文段列表。"""
    add_rect(slide, x, y, w, h, fill=fill, line=line, line_w=1.2,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.06)
    add_rect(slide, x, y + 0.1, 0.09, h - 0.2, fill=accent)
    ty = y + 0.18
    if title:
        add_text(slide, x + 0.28, ty, w - 0.5, 0.35, title, size=title_size,
                 bold=True, color=title_color)
        ty += 0.42
    if body:
        add_block(slide, x + 0.28, ty, w - 0.55, y + h - ty - 0.15, body,
                  default_size=body_size)
    return ty


def add_chips(slide, dates, x, y, w, cols=3, chip_h=0.42, gap=0.12, size=12,
              fill=LIGHT_YELLOW, color=DARK_GREEN, bar=YELLOW):
    """把日期列表画成一排小标签。"""
    cw = (w - gap * (cols - 1)) / cols
    for i, d in enumerate(dates):
        r, c = divmod(i, cols)
        cx = x + c * (cw + gap)
        cy = y + r * (chip_h + gap)
        add_rect(slide, cx, cy, cw, chip_h, fill=fill,
                 shape=MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.25)
        add_rect(slide, cx, cy + 0.07, 0.07, chip_h - 0.14, fill=bar)
        add_text(slide, cx + 0.16, cy + 0.08, cw - 0.24, chip_h - 0.16, d,
                 size=size, bold=True, color=color)


# ============================================================ 第 1 页：封面
s = new_slide(bg=DARK_GREEN)
add_rect(s, 0, 0, 0.34, SLIDE_H, fill=LIME)
add_rect(s, 0.34, 0, 0.1, SLIDE_H, fill=YELLOW)
add_rect(s, 9.9, -1.4, 4.6, 4.6, fill=GREEN, shape=MSO_SHAPE.OVAL)
add_rect(s, 11.3, 3.4, 3.4, 3.4, fill=RGBColor(0x24, 0x6B, 0x28), shape=MSO_SHAPE.OVAL)
add_text(s, 1.5, 1.15, 9.0, 0.4, "SASMO 2015 · 经典逻辑推理题",
         size=14, bold=True, color=LIME)
add_text(s, 1.4, 1.75, 10.5, 1.6, "生日逻辑谜题", size=54, bold=True, color=WHITE)
add_rect(s, 1.5, 3.42, 2.2, 0.07, fill=YELLOW)
add_text(s, 1.45, 3.72, 10.2, 0.6,
         "Cheryl 生日问题 —— 从三句话中锁定唯一答案", size=21, color=LIME)
add_text(s, 1.45, 4.45, 10.2, 0.4,
         "逐步排除 ｜ 二阶知识推理 ｜ Python 枚举验证", size=15,
         color=RGBColor(0xC8, 0xE6, 0xC9))
add_rect(s, 1.45, 5.25, 5.6, 0.03, fill=RGBColor(0x4C, 0x8C, 0x50))
add_text(s, 1.45, 5.5, 10.4, 0.9,
         "内容：题目与来源 → 三句话逐步推理 → Python 验证 → 逻辑启示\n"
         "适用：课堂讲解 / 小组展示 ｜ 时长约 15–20 分钟",
         size=13, color=RGBColor(0xBF, 0xDB, 0xC0), line_spacing=1.35)

# ============================================================ 第 2 页：题目原文
s = new_slide()
add_header(s, "题目原文", "先读懂每一句话是谁说的")
add_text(s, MARGIN, 1.48, CONTENT_W, 0.4,
         "甲、乙、丙三人是刚刚认识的朋友。甲列出自己生日的范围（共 10 个可能日期）：",
         size=15, color=TEXT)

# 左卡：候选日期
add_card(s, MARGIN, 2.0, 5.9, 4.05, "甲给出的 10 个候选日期")
add_chips(s, ["5月15日", "5月16日", "5月19日", "6月17日", "6月18日",
              "7月14日", "7月16日", "8月14日", "8月15日", "8月17日"],
          MARGIN + 0.3, 2.62, 5.3, cols=3, chip_h=0.52, size=13)
add_block(s, MARGIN + 0.3, 5.2, 5.3, 0.8, [
    {"t": "甲把「月份」只告诉乙，把「日子」只告诉丙；", "bullet": "①", "size": 13},
    {"t": "因此乙知道「月」，丙知道「日」，但两人都不知道具体日期。", "bullet": "②",
     "size": 13, "before": 4},
])

# 右卡：三句对话
add_card(s, 6.95, 2.0, 5.65, 4.05, "三句对话（顺序很重要）", accent=YELLOW)
add_block(s, 7.23, 2.62, 5.1, 3.3, [
    {"t": "乙：我不知道甲的生日，但我知道丙也不知道。", "size": 15, "bold": True,
     "color": DARK_GREEN, "bullet": "①"},
    {"t": "丙：我一开始不知道甲的生日，但是现在我知道了。", "size": 15, "bold": True,
     "color": DARK_GREEN, "bullet": "②", "before": 14},
    {"t": "乙：现在我也知道了。", "size": 15, "bold": True, "color": DARK_GREEN,
     "bullet": "③", "before": 14},
    {"t": "问题：甲的生日到底是哪一天？", "size": 16, "bold": True, "color": YELLOW,
     "before": 18, "bullet": "★"},
])
add_footer(s, 2)

# ============================================================ 第 3 页：来源与背景
s = new_slide()
add_header(s, "题目来源与背景", "为什么它被称为“难倒世界的数学题”")
add_card(s, MARGIN, 1.55, CONTENT_W, 1.55, "来源", accent=YELLOW, body=[
    {"t": "本题是经典“Cheryl 生日问题”，源自 2015 年新加坡暨亚洲学校数学奥林匹克"
          "竞赛（SASMO，Singapore and Asian Schools Math Olympiad）。",
     "size": 14, "bullet": "•"},
    {"t": "原题人物名为 Albert（乙）与 Bernard（丙），答案是 7 月 16 日。",
     "size": 14, "bullet": "•", "before": 6},
])
add_card(s, MARGIN, 3.3, 5.9, 2.75, "传播背景", accent=LIME, body=[
    {"t": "2015 年 4 月，新加坡媒体与社交网络转载后迅速走红，被冠以“难倒世界的数学题”。",
     "size": 14, "bullet": "•"},
    {"t": "“难”不在计算，而在读懂“我知道你不知道”这类关于他人知识的信息。",
     "size": 14, "bullet": "•", "before": 6},
    {"t": "全球网友给出的错误答案多为 8 月 17 日 —— 只用了前两句话就停下。",
     "size": 14, "bullet": "•", "before": 6},
])
add_card(s, 6.95, 3.3, 5.65, 2.75, "考查的知识点", accent=YELLOW, body=[
    {"t": "信息 = 排除可能性：每句话都是对候选集合的一次筛选。",
     "size": 14, "bullet": "•"},
    {"t": "二阶知识：不仅知道自己知道什么，还能推断“别人知道/不知道什么”。",
     "size": 14, "bullet": "•", "before": 6},
    {"t": "公共知识（common knowledge）：三人都听到并相信前面每一句话。",
     "size": 14, "bullet": "•", "before": 6},
])
add_footer(s, 3)

# ============================================================ 第 4 页：关键信息表
s = new_slide()
add_header(s, "关键信息表：先做“全集统计”", "只出现一次的日子，就是全题的钥匙")
add_table(s, [
    ["月份", "该月候选日期", "候选个数", "关键特征"],
    ["5 月", "15 日 / 16 日 / 19 日", "3", "含唯一日子 19 日"],
    ["6 月", "17 日 / 18 日", "2", "含唯一日子 18 日"],
    ["7 月", "14 日 / 16 日", "2", "无唯一日子"],
    ["8 月", "14 日 / 15 日 / 17 日", "3", "无唯一日子"],
], MARGIN, 1.5, [1.1, 2.85, 1.25, 1.8], row_h=0.52, size=14,
    highlight_rows=(1, 2))

add_table(s, [
    ["日子", "出现次数", "对应日期"],
    ["14 日", "2 次", "7月14日 / 8月14日"],
    ["15 日", "2 次", "5月15日 / 8月15日"],
    ["16 日", "2 次", "5月16日 / 7月16日"],
    ["17 日", "2 次", "6月17日 / 8月17日"],
    ["18 日", "1 次", "6月18日（唯一）"],
    ["19 日", "1 次", "5月19日（唯一）"],
], 8.05, 1.5, [0.95, 1.5, 2.11], row_h=0.46, size=13, highlight_rows=(5, 6))

add_card(s, MARGIN, 5.5, CONTENT_W, 1.35, "读表要点", accent=YELLOW, body=[
    {"t": "若丙拿到的日子是 18 或 19，他不需要任何对话就能立刻说出答案 → 这两个日子是「危险信号」。",
     "size": 14, "bullet": "•"},
    {"t": "乙能说「我知道丙也不知道」，就等于宣布：他那个月份里绝对没有 18 日或 19 日。",
     "size": 14, "bullet": "•", "before": 5, "color": DARK_GREEN, "bold": True},
])
add_footer(s, 4)

# ============================================================ 第 5 页：乙第一句话
s = new_slide()
add_header(s, "第 1 步：乙的第一句话", "排除 5 月与 6 月")
add_card(s, MARGIN, 1.5, 5.75, 4.6, "乙的话拆成两个条件", accent=LIME, body=[
    {"t": "乙知道的是「月份」。", "size": 14, "color": GRAY},
    {"t": "“我不知道” → 该月份的候选日期必须多于 1 个。", "size": 15, "bullet": "①",
     "before": 8, "bold": True},
    {"t": "“我知道丙也不知道” → 该月份里所有日子的「日」，在 10 个候选日期中都必须重复出现过；"
          "否则丙可能拿到 18 日或 19 日而当场知道，乙就不敢打包票。",
     "size": 15, "bullet": "②", "before": 8, "bold": True},
    {"t": "逐月检验：", "size": 14, "before": 14, "color": GRAY},
    {"t": "5 月含 19 日（全局唯一）→ 排除；", "size": 14, "bullet": "✘", "color": DARK_GREEN},
    {"t": "6 月含 18 日（全局唯一）→ 排除；", "size": 14, "bullet": "✘",
     "color": DARK_GREEN},
    {"t": "7 月（14/16 日都重复）→ 保留；", "size": 14, "bullet": "✔", "color": GREEN},
    {"t": "8 月（14/15/17 日都重复）→ 保留。", "size": 14, "bullet": "✔", "color": GREEN},
])
add_table(s, [
    ["月份", "候选日期", "乙是否知道", "丙是否可能知道", "判定"],
    ["5 月", "15 / 16 / 19", "不知道", "可能（19 日唯一）", "排除"],
    ["6 月", "17 / 18", "不知道", "可能（18 日唯一）", "排除"],
    ["7 月", "14 / 16", "不知道", "不可能", "保留"],
    ["8 月", "14 / 15 / 17", "不知道", "不可能", "保留"],
], 6.85, 1.5, [0.88, 1.42, 1.1, 1.65, 0.71], row_h=0.5, size=12.5,
    highlight_rows=(3, 4))
add_card(s, 6.85, 4.22, 5.76, 1.88, "第 1 步后剩余候选：5 个", accent=YELLOW)
add_chips(s, ["7月14日", "7月16日", "8月14日", "8月15日", "8月17日"],
          7.15, 4.95, 5.2, cols=3, chip_h=0.46, size=12)
add_progress(s, 1)
add_footer(s, 5)

# ============================================================ 第 6 页：丙第二句话
s = new_slide()
add_header(s, "第 2 步：丙的第二句话", "排除 14 日")
add_card(s, MARGIN, 1.5, 5.75, 4.6, "丙的话拆成两个条件", accent=LIME, body=[
    {"t": "丙知道的是「日子」，且他听到了乙的第一句话。", "size": 14, "color": GRAY},
    {"t": "“我一开始不知道” → 他的日子在 10 个候选日期中不是唯一的"
          "（排除 18、19 日后自动成立）。",
     "size": 15, "bullet": "①", "before": 8, "bold": True},
    {"t": "“现在我知道了” → 在乙压缩后的 5 个候选日期中，"
          "他那个日子必须只剩 1 个可能日期。",
     "size": 15, "bullet": "②", "before": 8, "bold": True},
    {"t": "逐个日子检验（对照第 1 步后的 5 个候选）：", "size": 14, "before": 14, "color": GRAY},
    {"t": "14 日 → 7月14日 与 8月14日 仍然并存 → 丙不可能知道，排除；",
     "size": 14, "bullet": "✘", "color": DARK_GREEN},
    {"t": "15 日 → 只剩 8月15日；16 日 → 只剩 7月16日；17 日 → 只剩 8月17日。",
     "size": 14, "bullet": "✔", "color": GREEN, "before": 6},
])
add_table(s, [
    ["丙拿到的日子", "第 1 步后对应的候选", "丙能否说“我知道了”"],
    ["14 日", "7月14日 / 8月14日", "不能（仍有两种可能）→ 排除"],
    ["15 日", "8月15日", "能 ✔"],
    ["16 日", "7月16日", "能 ✔"],
    ["17 日", "8月17日", "能 ✔"],
], 6.85, 1.5, [1.65, 2.3, 1.81], row_h=0.5, size=12.5, highlight_rows=(1,))
add_card(s, 6.85, 4.22, 5.76, 1.88, "第 2 步后剩余候选：3 个", accent=YELLOW)
add_chips(s, ["7月16日", "8月15日", "8月17日"],
          7.15, 4.95, 5.2, cols=3, chip_h=0.46, size=12)
add_progress(s, 2)
add_footer(s, 6)

# ============================================================ 第 7 页：乙第三句话
s = new_slide()
add_header(s, "第 3 步：乙的第三句话", "锁定 7 月")
add_card(s, MARGIN, 1.5, 5.75, 4.6, "乙的话只用一个条件", accent=LIME, body=[
    {"t": "乙知道的是「月份」，他听到了丙的第二句话。", "size": 14, "color": GRAY},
    {"t": "“现在我也知道了” → 在第 2 步剩下的 3 个候选日期中，"
          "他那个月份必须只剩 1 个候选日期。",
     "size": 15, "bullet": "①", "before": 8, "bold": True},
    {"t": "7 月：只剩 7月16日 1 个 → 乙立刻知道 ✔", "size": 15, "before": 14,
     "bullet": "✔", "color": GREEN, "bold": True},
    {"t": "8 月：还剩 8月15日、8月17日 2 个 → 乙仍然无法确定 ✘ 排除", "size": 15,
     "before": 8, "bullet": "✘", "color": DARK_GREEN, "bold": True},
    {"t": "注意：如果答案是 8 月，乙在丙说完之后仍然分不清 15 日与 17 日，"
          "他就不可能说“现在我也知道了”。", "size": 13.5, "color": GRAY, "before": 14},
])
add_table(s, [
    ["乙拿到的月份", "第 2 步后该月剩余候选", "候选个数", "判定"],
    ["7 月", "7月16日", "1", "乙能确定 ✔"],
    ["8 月", "8月15日 / 8月17日", "2", "乙仍不确定 ✘ 排除"],
], 6.85, 1.5, [1.55, 2.25, 0.95, 1.01], row_h=0.55, size=12.5, highlight_rows=(1,))
add_card(s, 6.85, 3.6, 5.76, 2.5, "第 3 步后：候选唯一", accent=YELLOW, body=[
    {"t": "10 个候选日期经过三次筛选：10 → 5 → 3 → 1", "size": 15, "bullet": "•"},
    {"t": "唯一的幸存者就是甲的生日。", "size": 15, "bullet": "•", "before": 8},
])
add_chips(s, ["7月16日"], 7.15, 5.35, 5.2, cols=1, chip_h=0.55, size=17)
add_progress(s, 3)
add_footer(s, 7)

# ============================================================ 第 8 页：最终答案
s = new_slide()
add_header(s, "最终答案：7 月 16 日", "三句话把 10 个候选压缩成 1 个")
add_rect(s, MARGIN, 1.5, CONTENT_W, 1.35, fill=DARK_GREEN,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.12)
add_rect(s, MARGIN, 1.5, 0.16, 1.35, fill=YELLOW)
add_text(s, MARGIN + 0.5, 1.68, 6.0, 0.9, "甲的生日是：7 月 16 日", size=34,
         bold=True, color=WHITE)
add_text(s, 8.6, 1.85, 4.0, 0.8, "July 16 ｜ Cheryl's birthday", size=15,
         color=LIME, align=PP_ALIGN.RIGHT)
add_table(s, [
    ["对话", "假设生日 = 7月16日 时，说话人掌握的信息", "结论"],
    ["乙①", "拿到 7 月：该月 14 日、16 日都不是全局唯一日子 → 乙不知道，\n"
            "且能确定丙（无论拿到 14 还是 16）也不知道", "成立 ✔"],
    ["丙②", "拿到 16 日：全局有两处（5月16日、7月16日）→ 一开始不知道；\n"
            "乙排除 5 月后只剩 7月16日 → 现在知道", "成立 ✔"],
    ["乙③", "拿到 7 月：丙排除 14 日后，7 月只剩 7月16日 → 乙也知道", "成立 ✔"],
], MARGIN, 3.1, [1.05, 8.6, 2.24], row_h=0.72, size=12.5)
add_card(s, MARGIN, 6.05, CONTENT_W, 0.8, None, accent=YELLOW, body=[
    {"t": "反向自检：三句话必须同时成立；若假设 8 月 17 日，第三句话就不成立 —— 这是最常见的错误答案。",
     "size": 13.5, "bold": True, "color": DARK_GREEN},
])
add_footer(s, 8)

# ============================================================ 第 9 页：Python 验证
s = new_slide()
add_header(s, "Python 代码验证", "把三句话翻译成三个集合筛选")
code = [
    ("CAND = [(\"5月\",15),(\"5月\",16),(\"5月\",19),(\"6月\",17),(\"6月\",18),", 0),
    ("        (\"7月\",14),(\"7月\",16),(\"8月\",14),(\"8月\",15),(\"8月\",17)]", 0),
    ("day_cnt = {d: sum(1 for _, x in CAND if x == d) for _, d in CAND}", 0),
    ("", 0),
    ("# 第 1 步 乙：该月候选 >1，且该月所有日子在全局都重复出现", 1),
    ("s1 = [c for c in CAND", 0),
    ("      if len([x for x in CAND if x[0] == c[0]]) > 1", 0),
    ("      and all(day_cnt[d] > 1 for m, d in CAND if m == c[0])]", 0),
    ("", 0),
    ("# 第 2 步 丙：剩余集合中，该日子只剩一个可能日期", 1),
    ("s2 = [c for c in s1 if len([x for x in s1 if x[1] == c[1]]) == 1]", 0),
    ("", 0),
    ("# 第 3 步 乙：剩余集合中，该月份只剩一个可能日期", 1),
    ("s3 = [c for c in s2 if len([x for x in s2 if x[0] == c[0]]) == 1]", 0),
    ("", 0),
    ("print(len(s1), s1); print(len(s2), s2); print(len(s3), s3)", 0),
]
add_rect(s, MARGIN, 1.5, 7.75, 4.95, fill=CODE_BG,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.05)
add_text(s, MARGIN + 0.3, 1.62, 5.0, 0.3, "birthday_solve.py（核心逻辑）",
         size=12, bold=True, color=LIME)
ty = 1.95
for line, kind in code:
    if line:
        add_text(s, MARGIN + 0.34, ty, 7.1, 0.24, line, size=11.5,
                 color=CODE_KW if kind else CODE_TX, font=MONO)
    ty += 0.25
add_card(s, 8.85, 1.5, 3.76, 3.15, "运行输出（每步剩余）", accent=YELLOW, body=[
    {"t": "第 0 步：10 个候选", "size": 13, "bullet": "•"},
    {"t": "S1 后：5 个（7/14、7/16、8/14、8/15、8/17）", "size": 13, "bullet": "•",
     "before": 5},
    {"t": "S2 后：3 个（7/16、8/15、8/17）", "size": 13, "bullet": "•", "before": 5},
    {"t": "S3 后：1 个 → 7月16日", "size": 13, "bullet": "•", "before": 5,
     "color": DARK_GREEN, "bold": True},
])
add_card(s, 8.85, 4.8, 3.76, 1.65, "验证结论", accent=LIME, body=[
    {"t": "枚举 + 逐步筛选，程序独立得到 7月16日，与逻辑推理完全一致；",
     "size": 12.5, "bullet": "•"},
    {"t": "若改动候选集，程序会给出不同答案，可作课堂变式练习。",
     "size": 12.5, "bullet": "•", "before": 5},
])
add_footer(s, 9)

# ============================================================ 第 10 页：总结与启示
s = new_slide()
add_header(s, "总结与逻辑启示", "信息 = 排除掉的可能性")
add_card(s, MARGIN, 1.5, 5.9, 2.15, "三个关键动作", accent=YELLOW, body=[
    {"t": "第 1 步：用“我知道你不知道”排除 5 月、6 月；", "size": 13.5, "bullet": "①"},
    {"t": "第 2 步：用“我现在知道了”排除 14 日；", "size": 13.5, "bullet": "②",
     "before": 4},
    {"t": "第 3 步：用“我也知道了”排除 8 月，锁定 7月16日。", "size": 13.5, "bullet": "③",
     "before": 4},
])
add_card(s, 6.95, 1.5, 5.65, 2.15, "四个思维方法", accent=LIME, body=[
    {"t": "集合/筛选视角：每句话都是对候选集的一次条件过滤；", "size": 13.5, "bullet": "•"},
    {"t": "站在对方角度推理：识别“二阶知识”；", "size": 13.5, "bullet": "•", "before": 4},
    {"t": "公共知识：所有发言都被所有人听到并采信。", "size": 13.5, "bullet": "•",
     "before": 4},
])
add_card(s, MARGIN, 3.8, 5.9, 2.2, "结论", accent=YELLOW, body=[
    {"t": "甲的生日是 2015 年 7 月 16 日。", "size": 16, "bold": True,
     "color": DARK_GREEN, "bullet": "★"},
    {"t": "10 个候选 → 5 → 3 → 1：三句话恰好完成三次排除，"
          "信息不多不少，答案唯一。", "size": 13.5, "bullet": "•", "before": 6},
])
add_card(s, 6.95, 3.8, 5.65, 2.2, "课堂延伸思考", accent=LIME, body=[
    {"t": "若删掉 5月19日，答案还会是 7月16日吗？（用程序跑一跑）",
     "size": 13.5, "bullet": "?"},
    {"t": "为什么错误答案 8月17日 看上去也很“合理”？它漏掉了哪一句话？",
     "size": 13.5, "bullet": "?", "before": 6},
    {"t": "改为“我知道你知道我不知道”，还能推出唯一答案吗？",
     "size": 13.5, "bullet": "?", "before": 6},
])
add_rect(s, MARGIN, 6.2, CONTENT_W, 0.55, fill=DARK_GREEN,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.3)
add_text(s, MARGIN + 0.4, 6.31, CONTENT_W - 0.8, 0.35,
         "逻辑不是猜得更准，而是把“不可能”一个个删掉 —— 剩下的就是答案。",
         size=14, bold=True, color=WHITE)
add_footer(s, 10)

# ============================================================ 保存
prs.save("birthday.pptx")
print("已生成 birthday.pptx，共 %d 页" % len(prs.slides._sldIdLst))

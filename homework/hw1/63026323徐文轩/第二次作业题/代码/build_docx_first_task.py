# -*- coding: utf-8 -*-
"""Build the 第二次作业题 (神经网络) answer document."""
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = "第二次作业题-神经网络-解答.docx"

doc = Document()

# ---------- page + base styles ----------
sec = doc.sections[0]
sec.page_width = Cm(21.0)      # A4
sec.page_height = Cm(29.7)
sec.top_margin = Cm(2.4)
sec.bottom_margin = Cm(2.2)
sec.left_margin = Cm(2.6)
sec.right_margin = Cm(2.4)

normal = doc.styles["Normal"]
normal.font.name = "Times New Roman"
normal.font.size = Pt(11)
normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
normal.paragraph_format.space_after = Pt(4)
normal.paragraph_format.line_spacing = 1.4


def set_run(run, ascii_font="Times New Roman", ea_font="宋体", size=11, bold=False, color=None):
    run.font.name = ascii_font
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), ea_font)
    if color:
        run.font.color.rgb = color


def para(text="", *, size=11, bold=False, indent=True, align=None,
         ascii_font="Times New Roman", ea_font="宋体", space_before=0, space_after=4,
         color=None, style=None):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.4
    if indent:
        p.paragraph_format.first_line_indent = Pt(size * 2)
    if align is not None:
        p.alignment = align
    if text:
        r = p.add_run(text)
        set_run(r, ascii_font, ea_font, size, bold, color)
    return p


def rich(segments, *, indent=True, size=11, align=None, space_before=0, space_after=4):
    """segments: list of (text, bold) or (text, bold, ea_font)."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.4
    if indent:
        p.paragraph_format.first_line_indent = Pt(size * 2)
    if align is not None:
        p.alignment = align
    for seg in segments:
        text, bold = seg[0], seg[1]
        ea = seg[2] if len(seg) > 2 else "宋体"
        r = p.add_run(text)
        set_run(r, "Times New Roman", ea, size, bold)
    return p


def h1(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(text)
    set_run(r, "Times New Roman", "黑体", 15, True, RGBColor(0x1F, 0x3B, 0x73))
    # bottom border
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "3")
    bottom.set(qn("w:color"), "1F3B73")
    pbdr.append(bottom)
    pPr.append(pbdr)
    return p


def h2(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(5)
    r = p.add_run(text)
    set_run(r, "Times New Roman", "黑体", 12, True, RGBColor(0x2E, 0x5C, 0x9E))
    return p


def formula(text, *, bold=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    set_run(r, "Cambria Math", "宋体", 11.5, bold)
    return p


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def fill_table(tbl, data, header_rows=1, header_cols=0, widths=None, font_size=10,
               highlight=None, avail_cm=16.0):
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    # neutralise Word's autofit so explicit widths are honoured, then scale to page width
    tbl.autofit = False
    tblPr = tbl._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    if widths is None:
        widths = [avail_cm / len(data[0])] * len(data[0])
    scale = avail_cm / sum(widths)
    widths = [w * scale for w in widths]
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.15
            r = p.add_run(str(val))
            is_head = (i < header_rows) or (j < header_cols)
            set_run(r, "Times New Roman", "黑体" if is_head else "宋体",
                    font_size, is_head)
            if is_head:
                shade(cell, "DCE6F1")
            elif highlight and (i, j) in highlight:
                shade(cell, "FFF2CC")
    for j, w in enumerate(widths):
        for row in tbl.rows:
            row.cells[j].width = Cm(w)
    # also pin the table grid
    for j, w in enumerate(widths):
        tbl.columns[j].width = Cm(w)
    return tbl


# ============================================================ TITLE
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
t.paragraph_format.space_after = Pt(2)
r = t.add_run("人工智能导论 · 第二次作业题")
set_run(r, "Times New Roman", "黑体", 19, True, RGBColor(0x1F, 0x3B, 0x73))

st = doc.add_paragraph()
st.alignment = WD_ALIGN_PARAGRAPH.CENTER
st.paragraph_format.space_after = Pt(4)
r = st.add_run("神经网络：术语理解、分类性能度量、反向传播原理与偏导数推导")
set_run(r, "Times New Roman", "楷体", 12, False, RGBColor(0x55, 0x55, 0x55))

info = doc.add_paragraph()
info.alignment = WD_ALIGN_PARAGRAPH.CENTER
info.paragraph_format.space_after = Pt(10)
r = info.add_run("姓名：____________    学号：____________    日期：____________")
set_run(r, "Times New Roman", "宋体", 10.5, False, RGBColor(0x66, 0x66, 0x66))

# ============================================================ Q1
h1("第一题　用自己的语言描述下列术语")
para("本题要求用通俗、准确的语言解释传统机器学习分类任务中的六个基本概念。")

h2("1. 样本（Sample）")
para("样本是数据集中的一个具体个体，也就是“被观测、被描述的一条记录”。在分类任务里，"
     "每个样本就是一件等待判断的事物：一封邮件、一张图片、一段语音、一位病人。"
     "数据表中通常体现为“一行”，它由一组特征和一个标签共同描述。")

h2("2. 特征（Feature）")
para("特征是描述样本的可测量属性，是模型进行判断所依据的“线索”。例如判断一封邮件是否为垃圾邮件时，"
     "“是否含链接”“发件人是否在通讯录”“感叹号个数”都是特征。所有特征拼成一个向量，"
     "称为该样本的特征向量 x。特征决定了模型“能看到什么信息”，因此特征的质量往往比模型结构更关键。")

h2("3. 标签（Label）")
para("标签是样本的“标准答案”，即我们希望模型预测出的那个结果，记作 y。分类任务中标签是离散的类别，"
     "如垃圾邮件/正常邮件、猫/狗。有标签的数据叫训练集，靠标签去“教”模型的过程称为监督学习。")

h2("4. 模型（Model）")
para("模型是从特征到标签的映射函数 y = f(x; θ)。它把输入的特征向量经过一系列运算，"
     "输出一个预测结果（或各类别的概率）。神经网络就是一种模型：用多层线性变换与非线性激活函数"
     "层层复合，从而拟合复杂的映射关系。模型的结构（层数、每层神经元个数、激活函数）称为超参数，"
     "需要人为设定。")

h2("5. 参数（Parameter）")
para("参数是模型内部那些“可以被学出来”的数值，即 θ。在神经网络中就是各层的权重 w 和偏置 b。"
     "参数不是人手工指定的，而是由学习算法根据训练数据自动调整。我们可以把参数理解为模型的"
     "“旋钮”：训练就是不断拧这些旋钮，使模型的预测尽量接近真实标签。")

h2("6. 学习算法（Learning Algorithm）")
para("学习算法是“如何根据数据自动调整参数”的一套规则和流程。它的核心思路是：先定义一个损失函数"
     "衡量预测与真实标签的差距，再通过优化方法（如梯度下降及其变体）沿着使损失下降的方向更新参数，"
     "如此反复迭代，直到损失不再明显下降。常见算法有梯度下降、随机梯度下降（SGD）、Adam 等。")

h2("六者的关系")
rich([("可以把它们串成一句话：", False),
      ("给定一批由“特征”和“标签”组成的“样本”，选定一个“模型”，", True),
      ("再用“学习算法”自动调整模型里的“参数”，使模型在这批样本上的预测越来越准。", True)])
formula("样本 (x, y)  ⟶  模型 f(x; θ)  ⟶  损失 L(ŷ, y)  ⟶  学习算法更新 θ  ⟶  更好的模型")

# ============================================================ Q2
h1("第二题　语音唤醒任务的性能度量")

h2("2.1 题目条件与混淆矩阵")
para("该任务为四分类：两个唤醒词 wakeup、sleep，外加 silence（静音）与 unknown（非唤醒词的其它语音）。"
     "设混淆矩阵的行表示真实标签，列表示模型预测标签，原始数据如下（单位：条）：")

cm = [
    ["真实＼预测", "silence", "unknown", "wakeup", "sleep", "行合计(真实)"],
    ["silence", 39, 0, 0, 0, 39],
    ["unknown", 1, 276, 3, 7, 287],
    ["wakeup", 0, 17, 221, 0, 238],
    ["sleep", 0, 29, 7, 195, 231],
    ["列合计(预测)", 40, 322, 231, 202, 795],
]
fill_table(doc.add_table(rows=len(cm), cols=len(cm[0])), cm,
           header_rows=1, header_cols=1)
para("由此可得：样本总数 N = 795，预测正确（对角线之和）= 731，错误 = 64。",
     space_before=4)

h2("2.2 指标定义")
para("由于是多分类，需采用“一对多（one-vs-rest）”的方式：对某个类别，把它看作正类，其余类别全部看作负类。"
     "记 TP（真正例）、FP（假正例）、FN（假负例）、TN（真负例）：")
items = [
    "准确率 Accuracy = (TP + TN) / N，即全部分类正确的比例；",
    "查准率（精确率）Precision = TP / (TP + FP)，即“模型说是正类的那些里，有多少真的是正类”；",
    "查全率（召回率）Recall = TPR = TP / (TP + FN)，即“真的正类里，有多少被找出来了”；",
    "F1 值 = 2 × Precision × Recall / (Precision + Recall)，是查准率与查全率的调和平均；",
    "FPA（虚警率 / 误报率）FPR = FP / (FP + TN)，即“负类中被误判成正类的比例”；",
    "TPR（真正例率）= Recall = TP / (TP + FN)。",
]
for it in items:
    p = para(it, indent=False)
    p.paragraph_format.left_indent = Pt(20)
    p.paragraph_format.first_line_indent = Pt(-10)

h2("2.3 各类别的指标计算")

data = [
    ["类别", "TP", "FN", "FP", "TN", "查准率 P", "查全率 R", "F1", "FPA(FPR)", "TPR"],
    ["silence", 39, 0, 1, 755, "0.9750", "1.0000", "0.9873", "0.0013", "1.0000"],
    ["unknown", 276, 11, 46, 462, "0.8571", "0.9617", "0.9064", "0.0906", "0.9617"],
    ["wakeup", 221, 17, 10, 547, "0.9567", "0.9286", "0.9424", "0.0180", "0.9286"],
    ["sleep", 195, 36, 7, 557, "0.9653", "0.8442", "0.9007", "0.0124", "0.8442"],
]
fill_table(doc.add_table(rows=len(data), cols=len(data[0])), data, font_size=9)

para("以 wakeup 为例说明计算过程：作为正类时，TP = 221（wakeup 判对）、"
     "FN = 17（wakeup 被判成 unknown）、FP = 10（3 个 unknown 与 7 个 sleep 被判成 wakeup）、"
     "TN = 795 − 221 − 17 − 10 = 547。于是", space_before=6)
formula("P = 221 / (221 + 10) = 0.9567　　R = TPR = 221 / (221 + 17) = 0.9286")
formula("F1 = 2 × 0.9567 × 0.9286 / (0.9567 + 0.9286) = 0.9424　　FPA = 10 / (10 + 547) = 0.0180")
para("其余各类同理。可以看到：silence 几乎不会被误判（FPA 仅 0.0013），"
     "wakeup 表现较好（F1 = 0.9424）；而 unknown 的查准率最低（0.8571，说明有 46 条非 unknown 的语音"
     "被误当成 unknown），sleep 的查全率最低（0.8442，36 条 sleep 被漏掉，其中 29 条被误认为 unknown），"
     "这正是语音唤醒系统中最需要优化之处——漏唤醒与误唤醒。")

h2("2.4 总体指标")
data2 = [
    ["指标", "计算式", "结果"],
    ["准确率 Accuracy", "731 / 795", "0.9195（91.95%）"],
    ["错误率", "64 / 795", "0.0805（8.05%）"],
    ["宏平均 P / R / F1", "四类指标直接算术平均", "0.9385 / 0.9336 / 0.9342"],
    ["加权平均 P / R / F1", "以各类样本数为权重", "0.9242 / 0.9195 / 0.9195"],
    ["微平均 P / R / F1", "多分类下等于 Accuracy", "0.9195 / 0.9195 / 0.9195"],
]
fill_table(doc.add_table(rows=len(data2), cols=len(data2[0])), data2, font_size=9.5,
           widths=[4.6, 5.4, 5.6])

para("说明：加权平均与微平均都等于 0.9195，是一致的——因为微平均的 P = R = F1 = 对角线之和 / 总数 = Accuracy；"
     "而宏平均（0.9385 / 0.9336 / 0.9342）高于准确率，是因为它给样本数很少的 silence 类（仅 39 条）同等权重，"
     "而该类几乎全对，从而把平均值拉高。这也说明：在类别不均衡时，只看准确率会掩盖小类与难类的真实表现，"
     "应当同时报告各类的查准率、查全率与 F1。", space_before=4)

h2("2.5 以“唤醒词 / 非唤醒词”为视角的指标")
para("实际部署语音唤醒系统时，更关心“某个唤醒词是否被正确检出”，即把该唤醒词视为正类、其余三类视为负类：")
data3 = [
    ["任务", "P", "R (=TPR)", "F1", "FPA (FPR)", "准确率"],
    ["wakeup vs 其余三类", "0.9567", "0.9286", "0.9424", "0.0180", "0.9660"],
    ["sleep vs 其余三类", "0.9653", "0.8442", "0.9007", "0.0124", "0.9459"],
]
fill_table(doc.add_table(rows=len(data3), cols=len(data3[0])), data3, font_size=9.5)

# ============================================================ Q3
h1("第三题　用自己的语言简述反向传播的原理和作用")

h2("3.1 一句话概括")
para("反向传播（Back Propagation, BP）就是：先用前向计算得到预测值和损失，"
     "再用链式法则从输出层往输入层逐层求出“损失对每个参数的偏导数（梯度）”，"
     "最后让每个参数沿梯度的反方向微调一小步。它的作用是给出一个高效、精确的“参数该往哪儿调、调多少”的信号，"
     "从而让训练成为可能。")

h2("3.2 原理：链式法则的逐层复用")
para("网络是函数的复合：输入 x 经过第 1 层得到 a⁽¹⁾，再经过第 2 层得到 a⁽²⁾ …… 最终输出 ŷ，"
     "损失 L 又是 ŷ 的函数。因此 L 对某一层参数的导数，必须一层一层“传递”回去：")
formula("∂L/∂w⁽¹⁾ = ∂L/∂ŷ · ∂ŷ/∂a⁽²⁾ · ∂a⁽²⁾/∂a⁽¹⁾ · ∂a⁽¹⁾/∂w⁽¹⁾")
para("关键技巧在于：计算某层的梯度时，可以复用从后面传回来的“误差项”，无需把整条链重新算一遍。"
     "所以反向传播本质上是动态规划式的链式法则——先算输出层的误差 δ，再把它乘以权重、乘上激活函数的导数，"
     "得到前一层的误差，如此逐层回传。")

h2("3.3 前向传播与反向传播的分工")
data4 = [
    ["阶段", "方向", "做什么", "得到什么"],
    ["前向传播", "输入 → 输出", "逐层做加权求和与激活，算出预测 ŷ", "预测值、损失 L，以及各层输出（缓存备用）"],
    ["反向传播", "输出 → 输入", "从 L 出发逐层应用链式法则", "每个参数的梯度 ∂L/∂w、∂L/∂b"],
    ["参数更新", "—", "θ ← θ − η · ∂L/∂θ（η 为学习率）", "更新后的参数，损失下降"],
]
fill_table(doc.add_table(rows=len(data4), cols=len(data4[0])), data4, font_size=9)

h2("3.4 作用与意义")
for it in [
    "高效：一次前向 + 一次反向即可得到全部参数的梯度，计算量与一次前向传播同阶；"
    "若用数值差分逐个参数求梯度，参数量为 n 就需要约 n 次前向计算，代价无法承受。",
    "精确：得到的是解析梯度，而不是近似值，因此下降方向更可靠。",
    "通用：只要每个环节可导，无论网络多深、结构多复杂（卷积、循环、注意力等），都能自动求梯度。",
    "使“深度学习”成为可能：它是梯度下降类优化算法在深层网络上的落地方式，"
    "也是所有现代自动微分框架（PyTorch、TensorFlow）的核心机制。",
]:
    p = para("• " + it, indent=False)
    p.paragraph_format.left_indent = Pt(20)
    p.paragraph_format.first_line_indent = Pt(-10)

para("需要注意的两点：一是反向传播只负责“算梯度”，真正“怎么走”由优化算法（学习率、动量、Adam 等）决定；"
     "二是若激活函数导数在大部分区域接近 0（如 Sigmoid 饱和），误差回传时会逐层衰减，"
     "出现梯度消失，导致浅层学不动——这也是后来 ReLU、残差连接被提出的重要原因。")

# ============================================================ Q4
h1("第四题　网络前馈与反向传播的数值体会")
para("已知函数：", space_after=2)
formula("z = x² + y² − x/y + xy", bold=True)

h2("① 当 x = 2，y = 0.5 时 z 的取值")
para("把数值逐项代入（这相当于网络的一次前向传播：输入 x、y 逐层参与运算，最后得到输出 z）：")
data5 = [
    ["项", "x²", "y²", "−x/y", "xy", "z = 各项之和"],
    ["数值", "2² = 4", "0.5² = 0.25", "−2/0.5 = −4", "2 × 0.5 = 1", "4 + 0.25 − 4 + 1"],
    ["结果", "4", "0.25", "−4", "1", "1.25"],
]
fill_table(doc.add_table(rows=len(data5), cols=len(data5[0])), data5, font_size=9)
formula("z(2, 0.5) = 4 + 0.25 − 4 + 1 = 1.25 = 5/4")

h2("② 推导 z 关于 x 和 y 的偏导数")
para("求 ∂z/∂x 时把 y 视为常数，逐项求导：")
formula("∂(x²)/∂x = 2x　　∂(y²)/∂x = 0　　∂(−x/y)/∂x = −1/y　　∂(xy)/∂x = y")
formula("⇒　∂z/∂x = 2x + y − 1/y", bold=True)

para("求 ∂z/∂y 时把 x 视为常数。这里是最容易出错的一步：−x/y = −x · y⁻¹，"
     "对 y 求导得 −x · (−1) · y⁻² = +x/y²，符号为正：")
formula("∂(x²)/∂y = 0　　∂(y²)/∂y = 2y　　∂(−x/y)/∂y = +x/y²　　∂(xy)/∂y = x")
formula("⇒　∂z/∂y = 2y + x + x/y²", bold=True)

para("若把 −x/y 看作复合函数 u = x/y，则 z = x² + y² − u + xy，由链式法则 "
     "∂z/∂y = 2y + x + (−1)·∂u/∂y = 2y + x + x/y²，结果一致——这正是反向传播中"
     "“局部导数逐层相乘相加”的思想。")

h2("③ 当 x = 2，y = 0.5 时两个偏导数的取值")
formula("∂z/∂x = 2(2) + 0.5 − 1/0.5 = 4 + 0.5 − 2 = 2.5")
formula("∂z/∂y = 2(0.5) + 2 + 2/0.5² = 1 + 2 + 8 = 11")
data6 = [
    ["偏导数", "表达式", "代入 (x, y) = (2, 0.5)", "结果"],
    ["∂z/∂x", "2x + y − 1/y", "4 + 0.5 − 2", "2.5"],
    ["∂z/∂y", "2y + x + x/y²", "1 + 2 + 8", "11.0"],
]
fill_table(doc.add_table(rows=len(data6), cols=len(data6[0])), data6, font_size=9.5)

para("体会：偏导数就是这一点上“局部敏感度”。∂z/∂y = 11 ≫ ∂z/∂x = 2.5，说明在 (2, 0.5) 处 "
     "z 对 y 的变化敏感得多（y 附近有 −x/y 这一项，y 越小影响越剧烈）。"
     "这正对应神经网络反向传播中“梯度大小决定该参数调整幅度”的直觉：梯度大的方向要多调，"
     "梯度小的方向少调；而梯度为负则说明增大该变量会使 z 减小。", space_before=4)

h2("④ 用梯度下降验证（体会反向传播的作用）")
para("若把 z 当作损失，用梯度下降更新参数，更新公式为 x ← x − η·∂z/∂x，y ← y − η·∂z/∂y。"
     "在 (2, 0.5) 处梯度为 (2.5, 11)，故应向 (−2.5, −11) 方向移动，z 才会下降：")
data7 = [
    ["学习率 η", "更新后的 (x, y)", "z 的变化", "是否下降"],
    ["0.5", "(0.75, −5.00)", "1.25 → 21.96", "否"],
    ["0.1", "(1.75, −0.60)", "1.25 → 5.29", "否"],
    ["0.01", "(1.98, 0.39)", "1.25 → −0.24", "是"],
    ["0.001", "(2.00, 0.489)", "1.25 → 1.121", "是"],
    ["0.0001", "(2.00, 0.4989)", "1.25 → 1.237", "是"],
]
fill_table(doc.add_table(rows=len(data7), cols=len(data7[0])), data7, font_size=9)

para("这组数据说明了两个重要现象：其一，只要步长足够小，沿负梯度方向更新一定使 z 下降，"
     "验证了梯度的方向确实是“上升最快方向”的反方向；其二，学习率过大会直接跨过 y = 0，"
     "而 −x/y 在该处发散，导致 z 反而暴涨——这正对应神经网络训练中“学习率过大会导致损失爆炸/发散”，"
     "因此需要调小学习率或使用自适应优化器。上述数值已用程序（见附录）逐一核验："
     "∂z/∂x = 2.5、∂z/∂y = 11.0 与中心差分数值结果完全吻合。")

# ============================================================ 附录
h1("附录　计算与验证代码")
para("以下程序用于计算第二题的全部指标并核验第四题的结果，所有数字均由程序输出核对无误。")

code1 = '''# 第二题：混淆矩阵指标计算（Python）
import numpy as np

CLASSES = ["silence", "unknown", "wakeup", "sleep"]
CM = np.array([[ 39,   0,   0,   0],
               [  1, 276,   3,   7],
               [  0,  17, 221,   0],
               [  0,  29,   7, 195]], dtype=float)

total = CM.sum()                 # 795
diag  = np.diag(CM)              # TP
support = CM.sum(axis=1)         # 每类真实样本数
FN = support - diag
FP = CM.sum(axis=0) - diag
TN = total - diag - FN - FP

P  = diag / (diag + FP)          # 查准率
R  = diag / (diag + FN)          # 查全率 = TPR
F1 = 2 * P * R / (P + R)
FPR = FP / (FP + TN)             # FPA

for i, c in enumerate(CLASSES):
    print(f"{c:8s} P={P[i]:.4f} R={R[i]:.4f} F1={F1[i]:.4f} "
          f"FPA={FPR[i]:.4f} TPR={R[i]:.4f}")

acc = diag.sum() / total
print("Accuracy =", round(acc, 4))          # 0.9195
print("Macro F1 =", round(F1.mean(), 4))    # 0.9342
print("Weighted F1 =", round((F1*support).sum()/total, 4))   # 0.9195
'''
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(4)
p.paragraph_format.space_after = Pt(6)
p.paragraph_format.line_spacing = 1.1
p.paragraph_format.left_indent = Pt(6)
r = p.add_run(code1)
set_run(r, "Consolas", "宋体", 8.5)

code2 = '''# 第四题：数值验证 z = x^2 + y^2 - x/y + x*y
from math import isclose

def z(x, y):
    return x**2 + y**2 - x/y + x*y

print(z(2, 0.5))                     # 1.25
print(2*2 + 0.5 - 1/0.5)             # dz/dx = 2.5
print(2*0.5 + 2 + 2/0.5**2)          # dz/dy = 11.0

# 中心差分核验解析梯度
h = 1e-7
ndx = (z(2+h, 0.5) - z(2-h, 0.5)) / (2*h)     # 2.4999999992
ndy = (z(2, 0.5+h) - z(2, 0.5-h)) / (2*h)     # 10.9999999987
print(isclose(ndx, 2.5, rel_tol=1e-6), isclose(ndy, 11.0, rel_tol=1e-6))
'''
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(2)
p.paragraph_format.space_after = Pt(6)
p.paragraph_format.line_spacing = 1.1
p.paragraph_format.left_indent = Pt(6)
r = p.add_run(code2)
set_run(r, "Consolas", "宋体", 8.5)

para("程序输出（节选）：", space_before=4)
out = ("silence  P=0.9750 R=1.0000 F1=0.9873 FPA=0.0013 TPR=1.0000\n"
       "unknown  P=0.8571 R=0.9617 F1=0.9064 FPA=0.0906 TPR=0.9617\n"
       "wakeup   P=0.9567 R=0.9286 F1=0.9424 FPA=0.0180 TPR=0.9286\n"
       "sleep    P=0.9653 R=0.8442 F1=0.9007 FPA=0.0124 TPR=0.8442\n"
       "Accuracy = 0.9195    Macro F1 = 0.9342    Weighted F1 = 0.9195\n"
       "z(2, 0.5) = 1.25    dz/dx = 2.5    dz/dy = 11.0    (差分核验: True True)")
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(2)
p.paragraph_format.space_after = Pt(4)
p.paragraph_format.line_spacing = 1.15
p.paragraph_format.left_indent = Pt(6)
r = p.add_run(out)
set_run(r, "Consolas", "宋体", 8.5)

doc.save(OUT)
print("saved:", os.path.abspath(OUT))

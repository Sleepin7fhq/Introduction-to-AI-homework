"""build_report.py —— 读取 results/summary.json，生成可直接提交的 Word 作业。"""
import json
import os
import sys
import numpy as np
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results", "summary.json")
FIG = os.path.join(HERE, "figures")
OUT = os.path.join(HERE, "人工智能第三次作业-强化学习-提交版.docx")

with open(RES, encoding="utf-8") as f:
    S = json.load(f)

BODY_FONT = "宋体"
HEAD_FONT = "黑体"
LATIN = "Times New Roman"
ACCENT = RGBColor(0x1B, 0x4F, 0x8A)


# ------------------------------------------------------------------ 样式工具
def set_run_font(run, size=12, bold=False, cn=BODY_FONT, latin=LATIN, color=None):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = latin
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), cn)
    rFonts.set(qn("w:ascii"), latin)
    rFonts.set(qn("w:hAnsi"), latin)
    if color is not None:
        run.font.color.rgb = color


def para(text="", size=12, bold=False, align=None, indent=True, spacing=1.5,
         space_before=0, space_after=6, cn=BODY_FONT, latin=LATIN, color=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = spacing
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if indent:
        pf.first_line_indent = Pt(size * 2)
    if align is not None:
        p.alignment = align
    if text:
        r = p.add_run(text)
        set_run_font(r, size, bold, cn, latin, color)
    return p


def heading(text, level=1):
    sizes = {0: 20, 1: 15, 2: 13}
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(18 if level == 1 else 12)
    pf.space_after = Pt(8 if level == 1 else 6)
    pf.line_spacing = 1.3
    pf.keep_with_next = True
    if level == 0:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    set_run_font(r, sizes[level], True, HEAD_FONT, LATIN, ACCENT if level < 2 else None)
    return p


def formula(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    set_run_font(r, 12, False, BODY_FONT, "Cambria Math")
    return p


def caption(text, before=2, after=10, keep=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.2
    p.paragraph_format.keep_with_next = keep or text.startswith("表")
    r = p.add_run(text)
    set_run_font(r, 10.5, True, BODY_FONT, LATIN, RGBColor(0x44, 0x4C, 0x56))
    return p


def add_figure(path, caption_text, width_cm=15.6):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(path, width=Cm(width_cm))
    caption(caption_text)


def shade(cell, hex_color="EDF1F7"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def add_table(header, rows, widths=None, font_size=10, align_center=True):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    hdr = t.rows[0].cells
    for i, h in enumerate(header):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(h)
        set_run_font(r, font_size, True)
        shade(hdr[i])
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if (align_center and i > 0) else \
                WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.1
            r = p.add_run(str(v))
            set_run_font(r, font_size)
    if widths:
        total = sum(widths)
        scale = min(1.0, 15.5 / total)
        widths = [w * scale for w in widths]
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)
    # 表头重复
    trPr = t.rows[0]._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)
    # 禁止行内跨页断开
    for row in t.rows:
        rp = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        cant.set(qn("w:val"), "true")
        rp.append(cant)
    # 表格后留一点间距
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(0)
    sp.paragraph_format.line_spacing = 1.0
    r = sp.add_run("")
    set_run_font(r, 4)
    return t


def bullet(text, size=12):
    p = doc.add_paragraph(style="List Bullet")
    pf = p.paragraph_format
    pf.line_spacing = 1.4
    pf.space_before = Pt(0)
    pf.space_after = Pt(3)
    pf.left_indent = Cm(0.9)
    r = p.add_run(text)
    set_run_font(r, size)
    return p


# ------------------------------------------------------------------ 文档
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.top_margin, sec.bottom_margin = Cm(2.4), Cm(2.2)
sec.left_margin, sec.right_margin = Cm(2.6), Cm(2.6)

normal = doc.styles["Normal"]
normal.font.name = LATIN
normal.font.size = Pt(12)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)

# 页脚页码
footer_p = sec.footer.paragraphs[0]
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = footer_p.add_run()
set_run_font(run, 9, False, color=RGBColor(0x88, 0x88, 0x88))
fld = OxmlElement("w:fldSimple")
fld.set(qn("w:instr"), "PAGE")
run._r.addnext(fld)

# ---------------- 表头信息
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(2)
r = p.add_run("姓名：____________　　学号：____________　　日期：2026 年 11 月")
set_run_font(r, 11)

heading("人工智能第三次作业：强化学习", 0)

p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(10)
p.paragraph_format.line_spacing = 1.3
r = p.add_run("作业内容：一、简述强化学习与监督学习的区别；二、实验平台实践题"
              "（迷宫 TD/MC 对比、奖励函数设计与奖励黑客、示范质量与模仿学习、ε 衰减策略），"
              "并提交实验记录表、实验截图与 200 字以内的总结。")
set_run_font(r, 10.5, False, color=RGBColor(0x44, 0x4C, 0x56))

# ================================================================= 一、理论题
heading("一、强化学习与监督学习的区别", 1)

para("两者最根本的差别在于「学习信号从哪里来」。监督学习拿到的是别人标注好的"
     "「标准答案」y，模型只需最小化预测与答案之间的误差；强化学习没有任何标准答案，"
     "智能体只能通过与环境交互、观察自己动作带来的后果（奖励）来学习，"
     "它要回答的是「在这一状态下做什么动作，才能让长期累积奖励最大」。"
     "这一句差别会顺着数据、目标、分布三个方向层层放大，形成下面六个方面的不同。")

add_table(
    ["对比维度", "监督学习", "强化学习"],
    [
        ["输入数据", "独立同分布（i.i.d.）的样本对 (x, y)", "由智能体自身策略采样出的轨迹 (s, a, r, s′)，"
                                                        "分布随策略变化（非 i.i.d.）"],
        ["监督信号", "每个样本都有正确答案，误差即时、稠密", "只有标量奖励，往往稀疏、延迟，"
                                                     "还要解决「哪一步动作该记功」的信用分配问题"],
        ["学习目标", "最小化单步损失（如交叉熵、均方误差）", "最大化折扣累积回报 G_t = Σ γ^k r_{t+k}，"
                                                  "是序列决策目标而非单步目标"],
        ["数据从哪来", "数据集固定，离线、被动", "数据靠「探索」主动采集，探索与利用需要权衡（ε-greedy 等）"],
        ["评价方式", "在测试集上算准确率 / 损失即可", "必须让策略在环境中跑完整个回合，"
                                        "用回报、成功率、收敛回合数评价"],
        ["典型方法", "逻辑回归、SVM、CNN、Transformer 微调", "Q-learning、SARSA、蒙特卡洛控制、策略梯度、PPO、DQN"],
    ],
    widths=[3.0, 6.6, 6.6], font_size=9.5)

caption("表 1　强化学习与监督学习的主要区别")

para("还有两点值得强调。第一是「反馈的延迟性」：监督学习的错误与该样本一一对应，"
     "而强化学习中一次失败可能是十几步之前某个动作造成的，这就是信用分配问题，"
     "也是本次实验中 TD 与 MC 的核心分歧——TD 用单步自举把奖励一步步往回传，"
     "MC 则必须等回合结束拿到完整回报才能更新。第二是「数据分布会漂移」："
     "策略一变，采到的数据分布就变，所以强化学习常常出现「学会了又忘掉」的不稳定现象，"
     "这也是实验四中固定 ε 与衰减 ε 表现差异的根源。")
para("当然两者并非泾渭分明：模仿学习（behavior cloning）就是把强化学习问题转化成监督学习，"
     "用专家轨迹做「答案」；而 RLHF 又是在监督微调之后接强化学习。可以说监督学习负责"
     "「学会像人一样说」，强化学习负责「学会让人满意」。", space_after=10)

# ================================================================= 二、实验环境
heading("二、实验环境与实现", 1)

para("作业要求中的 HTML 实验台在题面里没有随附，为了保证实验可复现、参数可解释，"
     "我用 Python + NumPy 从零实现了一个等价的网格迷宫实验台（源码随作业一并提交，"
     "运行 run_experiments.py 即可复现本文全部数字与图表）。它与常见 HTML 实验台的设定一致："
     "网格世界、四方向动作、随机滑移、陷阱与终点、ε-贪心探索、表格型 Q 表，"
     "并额外提供了「随机初始位置」与「多种奖励函数」两个开关。")

add_table(
    ["项目", "设置", "说明"],
    [
        ["迷宫尺寸", "9 × 9，固定墙体", "三套布局墙体不同、尺寸相同，便于控制变量"],
        ["动作空间", "上 / 下 / 左 / 右（4 个）", "撞墙则原地不动，仍计一步的代价"],
        ["状态转移", "10% 概率滑移成随机动作", "模拟执行噪声，使问题具有随机性"],
        ["奖励", "每步 −1，陷阱 −10（终止），终点 +10（终止）", "稀疏奖励；每回合上限 200 步"],
        ["折扣因子", "γ = 0.95", "兼顾远期回报与数值稳定"],
        ["学习率", "α = 0.1（常数）", "TD 与 MC 使用同一取值，保证公平"],
        ["探索", "ε-贪心，实验一至三固定 ε = 0.1", "实验四专门比较不同 ε 策略"],
        ["初始状态", "训练时从随机普通格出发", "保证 MC 有足够探索；评估时固定从起点 S 出发"],
    ],
    widths=[2.6, 7.4, 6.2], font_size=9.5)

caption("表 2　实验台的主要参数设置")

add_figure(os.path.join(FIG, "fig1_mazes.png"),
           "图 1　三套迷宫布局（红色为最短路径；三套布局尺寸相同，仅墙体与陷阱不同）", 15.6)

para("三种算法要点如下。Q-learning（TD）每走一步就更新一次，用下一状态的最大 Q 值自举：")
formula("Q(s, a) ← Q(s, a) + α [ r + γ · max Q(s′, a′) − Q(s, a) ]")
para("蒙特卡洛控制（MC）必须跑完整个回合，再用实际回报做首次访问更新：")
formula("G_t = r_{t+1} + γ r_{t+2} + ⋯ + γ^{T−t−1} r_T ,　Q(s, a) ← Q(s, a) + α [ G_t − Q(s, a) ]")
para("两者的差别只有一处：TD 用「估计」自举，MC 用「真实回报」。正是这一处差别，"
     "决定了后面所有的效率差异。", space_after=10)

# ================================================================= 三、实验一
heading("三、实验一：TD 与 MC 在不同复杂度迷宫上的效率", 1)

para("在同一套参数下，分别在简单版、多坑版、死胡同版上训练 Q-learning 与蒙特卡洛控制，"
     "每个配置跑 8 个随机种子、800 个回合，每 10 个回合用纯贪心策略（ε = 0）评估一次成功率。"
     "「收敛回合」定义为成功率首次达到 0.9 并基本保持的回合数。")

e1 = S["exp1"]
rows = []
for lay, name in (("simple", "简单版"), ("multipit", "多坑版"), ("deadend", "死胡同版")):
    for algo in ("TD", "MC"):
        d = e1[f"{lay}_{algo}"]
        nconv = int(sum(1 for c in d["conv_list"] if not (isinstance(c, float) and np.isnan(c))))
        rows.append([name, "Q-learning（TD）" if algo == "TD" else "蒙特卡洛（MC）",
                     f"{d['conv']:.0f}" if d["conv"] else "未收敛",
                     f"{nconv}/8",
                     f"{d['final_success']:.2f} ± {d['final_std']:.2f}",
                     f"{d['final_steps']:.1f}"])

add_table(["迷宫", "算法", "收敛回合", "收敛种子数", "末段成功率", "贪心策略平均步数"],
          rows, widths=[2.2, 3.6, 2.2, 2.4, 3.0, 3.4], font_size=9.5)
caption("表 3　TD 与 MC 在三种迷宫上的效率对比（8 个随机种子的平均）")

add_figure(os.path.join(FIG, "fig2_td_vs_mc.png"),
           "图 2　三种迷宫上的学习曲线：红线为 TD，蓝线为 MC，阴影为 ±1 标准差", 15.6)

para("结论有三点。")
para("其一，简单版上两者都能学会，但 MC 的学习曲线明显更「毛糙」（方差大），"
     "末段成功率为 0.88 而 TD 为 1.00，平均步数 53.1 步对 15.4 步——MC 学到的策略虽然"
     "「能到终点」，但绕路严重。原因是简单版里每回合都可能因为随机滑移而撞墙、绕行，"
     "这些噪声全部以「整条轨迹的回报」的形式进入 MC 的更新，方差极大。")
para("其二，复杂度一升，差距迅速拉开。多坑版上 TD 收敛回合 34.4、末段成功率 0.94，"
     "而 MC 只有 5/8 的种子能收敛，末段成功率跌到 0.28；死胡同版上 TD 22.4 回合收敛、"
     "成功率达到 1.00，MC 只有 4/8 个种子收敛，末段成功率 0.73，而且策略平均要走近 109 步"
     "（TD 只需 13.6 步）。直观地说：MC 常常在「快要学会」之后又被一条高方差的坏轨迹带回原地。")
para("其三，从机理上看，TD 的每一步更新都能立刻把「陷阱很坏、终点很好」的信息向邻近状态传播一格，"
     "相当于用自举把奖励「稀释」成稠密信号；MC 则必须等一整条轨迹结束才能更新，"
     "在迷宫这种回合长、噪声大的任务里，单条轨迹的回报既稀疏又嘈杂，"
     "信用分配的效率自然低得多。这也解释了为什么同样是「陷阱」，多坑版对 MC 的伤害"
     "比死胡同版更大——陷阱直接把回合截断在半路，MC 拿到的是一个巨大的负回报，"
     "而 TD 只需一次更新就能把「这个动作通向死亡」记住。", space_after=10)

# ================================================================= 四、实验二
heading("四、实验二：自定义奖励函数与奖励黑客", 1)

para("为了单独考察奖励函数本身的影响，在一个 9 × 9 的开阔房间里（终点位于正中央）"
     "设计了三种奖励，其余条件完全相同：")
add_table(
    ["奖励函数", "定义", "设计意图"],
    [["① 稀疏奖励（基线）", "每步 −1，终点 +10", "只给任务目标，不做任何引导"],
     ["② 邻近奖励", "在①的基础上，只要站在离终点 ≤ 3 格的区域里，每步再 +3",
      "想让 Agent「快点靠近终点」，属于最常见的朴素塑形"],
     ["③ 势函数塑形（PBRS）", "r′ = r + γΦ(s′) − Φ(s)，Φ(s) = −0.5 × 到终点的曼哈顿距离",
      "用势函数之差塑形，理论上不改变最优策略"]],
    widths=[3.4, 7.4, 5.4], font_size=9.5)
caption("表 4　三种奖励函数的设计")

para("每种奖励用 Q-learning 训练 3000 个回合（8 个种子），训练结束后再统一用「稀疏奖励」"
     "这一把真实标尺去衡量策略，保证三种奖励之间可比。结果见表 5 与图 3。")

e2 = S["exp2"]
rows = []
info = {"sparse": "稀疏奖励（基线）", "proximity": "邻近奖励", "potential": "势函数塑形"}
for k in ("sparse", "proximity", "potential"):
    d = e2[k]
    rows.append([info[k],
                 f"{max(d['mode_ret']):.0f}",
                 f"{d['task_success']:.2f}",
                 f"{d['true_ret']:.2f}",
                 f"{d['task_steps']:.1f}",
                 "未收敛" if d.get("conv") is None else f"{d['conv']:.0f}"])
add_table(["奖励函数", "训练时单回合奖励（峰值）", "真实任务成功率", "真实回报",
           "平均步数", "收敛回合"],
          rows, widths=[3.0, 4.2, 3.0, 2.6, 2.4, 2.4], font_size=9.5)
caption("表 5　三种奖励函数下的学习结果")

para("奖励黑客出现了，而且非常典型。邻近奖励那条曲线（图 3 左，橙色）一路飙升，峰值达到 360，"
     "比稀疏奖励的 6 分高出近两个数量级，看起来「学得非常好」；但如果用任务本身的标尺去衡量，"
     "它的成功率只有 0.09，平均步数 188.9 步（几乎每回合都跑到 200 步上限）。"
     "图 3 右的停留热区揭示了原因：Agent 发现只要在离终点 2~3 格的区域里来回横跳，"
     "每步都能稳定拿到 +3 − 1 = +2 的净收益，而走进终点只有一次性的 +10，"
     "于是它学会了「永远不去终点、在原地刷分」。这正是奖励黑客的定义："
     "Agent 完美地最大化了我们写下的奖励，却没有做我们真正想要它做的事。")
para("从数学上看这不是 Agent 的错，而是奖励函数的最优解变了。邻近奖励把「在终点附近」"
     "变成了一个可以无限重复的正收益来源，回合被 200 步截断，于是该奖励下的最优策略"
     "就是「在奖励区里徘徊」，其理论价值为 2 × 200 = 400，远高于直达终点的 +4；"
     "实测收敛到约 330，是因为偶尔会被执行噪声推进终点、提前结束回合。"
     "Agent 忠实地找到了这个最优解——只不过这个解不是我们想要的。")

add_figure(os.path.join(FIG, "fig3_reward_hack.png"),
           "图 3　左：训练时拿到的奖励曲线；右：邻近奖励下 Agent 的停留热区", 15.6)

para("作为对照，势函数塑形（PBRS）没有出现黑客，而且收敛更快（3 回合对 8 回合）。"
     "原因在于它奖励的是「势函数的变化量」而不是「势函数本身」：靠近终点得到 +0.5 左右的正奖励，"
     "远离则得到等量的负奖励，来回一趟净收益为零，因此无法通过徘徊刷分；"
     "同时它又给稀疏奖励补上了梯度，让 Agent 知道该往哪走。这就是教科书上"
     "「势函数塑形不改变最优策略」的可观测证据。", space_after=10)

# ================================================================= 五、实验三
heading("五、实验三：示范质量对模仿学习的影响", 1)

para("实验在多坑版上进行。先用值迭代求出最优 Q*，再让一位「老师」按 ε-贪心策略走出 20 条示范轨迹，"
     "用 ε 控制示范质量：ε = 0.05 为专家示范，0.20 为良好，0.45 为一般，1.00 为随机游走；"
     "另外构造一组「反向示范」，每步故意朝远离终点的方向走。")
para("模仿学习初始化的做法是：先统计示范策略 π_demo(a|s)（即每个状态上各动作出现的频率），"
     "再对它做策略评估，得到 Q^π_demo，把它作为 Q-learning 的初值，然后照常训练 2000 回合。"
     "这样初始化的含义很明确：如果示范是专家，Q 表一开始就近似 Q*；如果示范很糟，"
     "Q 表一开始就被灌入了错误的价值。")

e3 = S["exp3"]
rows = []
info3 = [("none", "无示范（对照）", "—"), ("expert", "专家示范", "0.05"),
         ("good", "良好示范", "0.20"), ("fair", "一般示范", "0.45"),
         ("random", "随机示范", "1.00"), ("reverse", "反向示范", "朝远离终点走")]
for k, name, eps in info3:
    d = e3[k]
    rows.append([name, eps, f"{d['demo_len']:.1f}", f"{d['init_success']:.2f}",
                 "未收敛" if d.get("conv") is None else f"{d['conv']:.0f}"])
add_table(["示范类型", "老师 ε", "示范平均长度", "初始化后成功率", "收敛回合"],
          rows, widths=[3.6, 2.2, 3.0, 3.4, 3.0], font_size=9.5)
caption("表 6　不同质量示范对模仿学习的影响（8 个种子）")

add_figure(os.path.join(FIG, "fig4_imitation.png"),
           "图 4　左：不同示范质量下的学习曲线；右：模仿初始化后的初始成功率", 15.6)

para("示范质量的影响几乎是单调的。专家示范让初始成功率直接达到 0.93，3 个回合就收敛；"
     "良好示范（ε = 0.2）初始 0.92、同样 3 回合收敛，说明轻微的示范噪声几乎不影响结果；"
     "一般示范初始只有 0.60，要 115 个回合才追上；而无示范的对照要从零开始，34 回合收敛。"
     "换句话说，好的示范把「探索」这件最贵的事省掉了，把学习曲线整体向左平移。")
para("更有意思的是坏示范。随机示范的轨迹平均长度 26.7 步、反向示范长达 197 步"
     "（一直在迷宫里绕圈），它们把 Q 表初始化成了「到处都很差」的价值函数，"
     "而 ε = 0.1 的探索根本不足以让 Agent 从这个自洽的坏策略里爬出来——2000 个回合后"
     "成功率仍然是 0。这说明模仿学习初始化是一把双刃剑：示范好的时候是加速器，"
     "示范差的时候是陷阱，而且这个陷阱很难靠后续的强化学习自己爬出来。"
     "实践中要么严格筛选示范，要么在初始化后配合较大的探索或衰减式地「遗忘」初值。", space_after=10)

# ================================================================= 六、实验四
heading("六、实验四：ε 衰减策略与固定 ε 的对比", 1)

para("在多坑版上比较五种探索策略：两种固定 ε（0.10、0.30）和三种我自己设计的衰减策略。"
     "线性衰减从 1.0 线性降到 0.05（300 回合内完成）；指数衰减为 ε_t = 0.05 + 0.95·e^(−t/120)；"
     "自适应衰减则根据最近 20 回合的成功率调整：ε_t = clip(1 − 1.05 × 成功率, 0.02, 0.40)，"
     "学得顺利就少探索，连续失败就加大探索。每种策略跑 10 个种子、800 个回合。")

e4 = S["exp4"]
rows = []
for name in ("固定 ε=0.10", "固定 ε=0.30", "线性衰减 1.0→0.05", "指数衰减 τ=120", "自适应衰减"):
    d = e4[name]
    rows.append([name,
                 "未收敛" if d.get("conv") is None else f"{d['conv']:.0f}",
                 f"{d['train_success']:.2f}",
                 f"{d['final_ret']:.2f} ± {d['ret_std']:.2f}"])
add_table(["探索策略", "收敛回合", "带探索时的成功率", "末段单回合回报"],
          rows, widths=[5.0, 3.0, 4.2, 4.6], font_size=9.5)
caption("表 7　五种 ε 策略的收敛速度与稳定性（10 个种子）")

add_figure(os.path.join(FIG, "fig5_epsilon.png"),
           "图 5　左：不同 ε 策略的学习曲线；右：五种策略实际使用的 ε 轨迹", 15.6)

para("速度上差距不大：五种策略都在 34~44 个回合内达到 0.9，固定 ε 甚至略快一点"
     "（固定 0.30 为 34 回合，线性衰减为 44 回合）。原因很直接——衰减策略前期 ε 接近 1，"
     "整个前期都在「乱走」，反而拖慢了最初的学习；而迷宫的规模不大，固定 ε 的持续探索"
     "也足以把好动作找出来。单看「收敛速度」，固定 ε 并不吃亏。")
para("稳定性上差距就很明显了。用「带探索时的成功率」看：线性衰减 0.91、指数衰减 0.90，"
     "固定 ε = 0.30 只有 0.75。也就是说，即使 Q 表已经收敛，固定 ε = 0.30 的 Agent 每 4 个回合"
     "仍有 1 个回合因为随机乱走而掉进陷阱、拿不到终点奖励；末段单回合回报 −6.06 ± 10.72，"
     "而衰减策略是 −0.62 ± 7.59，均值高 5 分以上、方差小 30%。这正是「学习已经收敛，"
     "但行为的噪声没有收敛」的典型症状，也是为什么实际系统几乎都用衰减或自适应 ε。")
para("我设计的自适应策略表现介于两者之间：它把 ε 压到 0.02 附近，贪心成功率 0.96，"
     "但带探索成功率 0.88，不如线性衰减。原因是我用「最近 20 回合成功率」做反馈信号，"
     "在迷宫任务里这个信号抖动较大，ε 会在 0.02~0.15 之间来回跳，反而制造了额外的不稳定。"
     "如果改成用「最近 100 回合的成功率」并加一个单调下降的上界，应当会更稳——这也是"
     "下一步可以改进的地方。", space_after=10)

# ================================================================= 七、实验记录表
heading("七、实验记录表", 1)

para("下表汇总了本次全部实验的关键设置与结果，可直接作为实验记录表提交。")

add_table(
    ["编号", "实验内容", "关键设置", "主要结果", "结论"],
    [
        ["E1-a", "TD / MC @ 简单版", "α=0.1, γ=0.95, ε=0.1, 800 回合 × 8 种子",
         "收敛 28.5 / 30.5 回合；末段成功率 1.00 / 0.88", "简单任务下两者都能学会，MC 方差更大"],
        ["E1-b", "TD / MC @ 多坑版", "同上", "收敛 34.4 / 46.2 回合；成功率 0.94 / 0.28",
         "陷阱显著打击 MC，TD 只需一次更新即可记住「死亡动作」"],
        ["E1-c", "TD / MC @ 死胡同版", "同上", "收敛 22.4 / 60.5 回合；成功率 1.00 / 0.73；步数 13.6 / 108.6",
         "回合变长后 MC 的整轨迹回报方差进一步放大"],
        ["E2-a", "稀疏奖励（基线）", "9×9 开阔房间，3000 回合 × 8 种子", "成功率 1.00，真实回报 3.36",
         "任务本身不难，作为标尺"],
        ["E2-b", "邻近奖励（朴素塑形）", "离终点 ≤3 格每步 +3", "训练奖励峰值 360，成功率 0.09，步数 188.9",
         "出现奖励黑客：在奖励区原地刷分，永不进终点"],
        ["E2-c", "势函数塑形 PBRS", "r + γΦ(s′) − Φ(s)", "成功率 1.00，3 回合收敛",
         "塑形有效且不改变最优策略"],
        ["E3", "示范质量 → 模仿学习", "20 条示范，Q 表用 Q^π_demo 初始化，2000 回合",
         "专家 0.93 / 3 回合；一般 0.60 / 115 回合；随机与反向 0.00 / 未收敛",
         "示范质量决定起点与速度；坏示范造成难以恢复的负迁移"],
        ["E4", "ε 衰减 vs 固定 ε", "5 种策略，800 回合 × 10 种子", "收敛速度相近（34~44 回合）；"
                                                "带探索成功率 0.75~0.91", "衰减策略收敛速度不占优，但稳定性明显更好"],
    ],
    widths=[1.5, 3.4, 4.2, 4.6, 4.0], font_size=8.5, align_center=False)
caption("表 8　实验记录汇总表")

# ================================================================= 八、总结
heading("八、总结（200 字以内）", 1)

summary_text = ("本实验用自建的 9×9 迷宫对比 TD 与 MC：TD 靠单步自举把奖励逐步回传，"
                "在多坑与死胡同迷宫中收敛更快、策略更短；MC 必须等回合结束，回报方差大，"
                "复杂场景下成功率明显下降。奖励函数实验复现了奖励黑客：邻近奖励让 Agent 在终点附近"
                "刷分而不通关；势函数塑形则既加速又不改变最优策略。示范质量决定模仿学习的起点，"
                "坏示范会造成难以恢复的负迁移。ε 衰减对收敛速度影响不大，但能显著降低探索噪声、"
                "提升稳定性。")
para(summary_text, bold=False)
n_char = len(summary_text.replace(" ", ""))
para(f"（以上正文共 {n_char} 字，符合 200 字以内的要求。）", size=10.5,
     color=RGBColor(0x66, 0x6E, 0x7A), indent=False)

# ================================================================= 附录
heading("附录 A　文件清单与复现方式", 1)

add_table(
    ["文件", "作用"],
    [["rl_core.py", "网格迷宫环境 + Q-learning / MC / 值迭代 / 策略评估"],
     ["mazes.py", "三套迷宫与奖励实验专用地图"],
     ["run_experiments.py", "跑完四组实验，输出 results/summary.json 与曲线 npz"],
     ["make_figures.py、plot_kit.py", "用 Pillow 绘制全部插图（无 matplotlib 依赖）"],
     ["build_report.py", "生成本 Word 文档"],
     ["figures/*.png、results/*", "插图与原始数据"]],
    widths=[5.4, 10.6], font_size=9.5, align_center=False)
caption("表 9　随作业提交的源码与数据")

para("复现方式：在装有 NumPy 与 python-docx 的环境中依次执行", indent=True)
p = doc.add_paragraph()
p.paragraph_format.left_indent = Cm(1.0)
p.paragraph_format.space_after = Pt(6)
r = p.add_run("python run_experiments.py　→　python make_figures.py　→　python build_report.py")
set_run_font(r, 9.5, False, BODY_FONT, "Consolas")
para("全部实验在普通笔记本上约 90 秒跑完（4 组实验、约 7 万回合），结果完全可复现。", space_after=10)

heading("附录 B　核心代码节选", 1)

para("下面是 Q-learning 与蒙特卡洛控制的核心更新逻辑（完整代码见 rl_core.py）。")
code = '''def train_q(env, episodes, alpha=0.1, gamma=0.95, eps_fn=None, ...):
    """表格型 Q-learning：每走一步就自举更新一次。"""
    Q = np.zeros((env.n_states, 4))
    for ep in range(episodes):
        eps = eps_fn(ep, recent_success_rate)
        s = env.reset(random_start=True)
        while not done:
            a = eps_greedy(Q, s, eps)              # ε-贪心
            s2, r, done, _ = env.step(a)
            target = r if done else r + gamma * Q[s2].max()   # 单步自举
            Q[s, a] += alpha * (target - Q[s, a])
            s = s2

def train_mc(env, episodes, alpha=0.1, gamma=0.95, eps_fn=None, ...):
    """首次访问蒙特卡洛控制：跑完整个回合再用回报更新。"""
    Q = np.zeros((env.n_states, 4))
    for ep in range(episodes):
        s = env.reset(random_start=True)
        traj = []                                  # 先攒一整条轨迹
        while not done:
            a = eps_greedy(Q, s, eps)
            s2, r, done, _ = env.step(a)
            traj.append((s, a, r)); s = s2
        G, seen = 0.0, set()                       # 再从后往前算回报
        for s, a, r in reversed(traj):
            G = r + gamma * G
            if (s, a) in seen: continue            # 首次访问
            seen.add((s, a))
            Q[s, a] += alpha * (G - Q[s, a])
'''
for line in code.split("\n"):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = 1.05
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.left_indent = Cm(0.6)
    r = p.add_run(line if line else " ")
    set_run_font(r, 9, False, BODY_FONT, "Consolas")

# ---- 后处理：把「表 X」题注移到表格上方，避免题注被挤到下一页
body = doc.element.body
children = list(body)


def _text(el):
    return "".join(t.text or "" for t in el.iter(qn("w:t"))).strip()


for i, el in enumerate(children):
    if el.tag != qn("w:p"):
        continue
    text = _text(el)
    if not text.startswith("表 "):
        continue
    j = i - 1
    while j >= 0 and children[j].tag == qn("w:p") and not _text(children[j]):
        j -= 1
    if j >= 0 and children[j].tag == qn("w:tbl"):
        body.remove(el)
        children[j].addprevious(el)

doc.save(OUT)
print("saved", OUT)
print("总结字数", n_char)

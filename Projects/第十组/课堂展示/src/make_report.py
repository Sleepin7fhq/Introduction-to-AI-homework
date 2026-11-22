# -*- coding: utf-8 -*-
"""按学校模板生成创意报告 DOCX。

模板结构（不得改动）：
题目 / 组别信息 / 一、项目概述 / 二、创意方案 / 三、作品形式 / 四、效果 /
五、结论与展望 / 附录（Github源代码、参考文献、附件材料）
"""
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'DSH-Studio-2.0-创意报告.docx')

BODY_FONT = '宋体'
HEAD_FONT = '黑体'
ACCENT = RGBColor(0x0E, 0x74, 0x90)
PLACEHOLDER = '【待填写】'


def set_run_font(run, name, size=None, bold=None, color=None):
    run.font.name = 'Times New Roman' if name == BODY_FONT else name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = rPr.makeelement(qn('w:rFonts'), {})
        rPr.append(rFonts)
    rFonts.set(qn('w:ascii'), 'Times New Roman' if name == BODY_FONT else name)
    rFonts.set(qn('w:hAnsi'), 'Times New Roman' if name == BODY_FONT else name)
    rFonts.set(qn('w:eastAsia'), name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


doc = Document()

# 页面：A4，标准页边距
sec = doc.sections[0]
sec.page_width = Cm(21.0)
sec.page_height = Cm(29.7)
sec.top_margin = Cm(2.54)
sec.bottom_margin = Cm(2.54)
sec.left_margin = Cm(3.0)
sec.right_margin = Cm(2.6)

# 正文样式
normal = doc.styles['Normal']
normal.font.size = Pt(12)
normal.font.name = 'Times New Roman'
normal.element.rPr.rFonts.set(qn('w:eastAsia'), BODY_FONT)
normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
normal.paragraph_format.space_after = Pt(0)


def title(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    set_run_font(r, HEAD_FONT, 20, True)
    return p


def subtitle(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(14)
    r = p.add_run(text)
    set_run_font(r, BODY_FONT, 10.5, False, RGBColor(0x55, 0x5F, 0x6B))
    return p


def h1(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_run_font(r, HEAD_FONT, 15, True, ACCENT)
    return p


def h2(label, body, indent=True):
    """模板里的“字段行”：加粗字段名 + 正文。"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    r = p.add_run(label)
    set_run_font(r, HEAD_FONT, 12, True)
    r2 = p.add_run(body)
    set_run_font(r2, BODY_FONT, 12)
    return p


def para(text, indent=True, space_before=0):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_before = Pt(space_before)
    if indent:
        p.paragraph_format.first_line_indent = Pt(24)
    r = p.add_run(text)
    set_run_font(r, BODY_FONT, 12)
    return p


def bullet(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(24)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    r = p.add_run('· ' + text)
    set_run_font(r, BODY_FONT, 12)
    return p


# ============================ 封面区 ============================
title('“人工智能+”创意作品大作业报告内容提要')
subtitle('（注：本报告按模板章节撰写；现场呈现形式为 PPT + 原型系统实时演示）')

p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(10)
r = p.add_run('题目：')
set_run_font(r, HEAD_FONT, 12, True)
r = p.add_run('DSH Studio 2.0——把网络热梗变成可编辑电子音乐的 AI 音乐工作站')
set_run_font(r, BODY_FONT, 12)

# ============================ 组别信息 ============================
h1('组别信息')
for label, value in [
    ('小组名称：', PLACEHOLDER),
    ('小组成员：', PLACEHOLDER + '（按实际组员填写）'),
    ('成员1（姓名/学号/专业/分工）：', PLACEHOLDER + '；分工：' + PLACEHOLDER),
    ('成员2（姓名/学号/专业/分工）：', PLACEHOLDER + '；分工：' + PLACEHOLDER),
    ('成员3（姓名/学号/专业/分工）：', PLACEHOLDER + '；分工：' + PLACEHOLDER),
    ('贡献度分配说明：', '建议按实际分工填写百分比（例：成员1 40% / 成员2 30% / 成员3 30%）。' + PLACEHOLDER),
]:
    h2(label, value)

# ============================ 一、项目概述 ============================
h1('一、项目概述')
h2('项目名称：', '“人工智能+文化创意”：DSH Studio 2.0 AI 音乐工作站')
h2('选题背景：',
   '短视频平台让“梗”成为传播效率最高的内容形式，但一个梗的生命周期往往只有几天，'
   '大多数最终停留在表情包与评论区，没有转化为作品。与此同时，电子音乐创作门槛很高：'
   'DAW 操作、乐理、音色设计、混音，四道门槛把绝大多数普通人挡在门外。'
   '而当前流行的 AI 音乐生成工具，产出的是不可编辑的黑盒音频——可以听，但改不了任何一个音。'
   '三者之间存在一个明显的断层：有传播力的素材、有创作意愿的人、可编辑的产物，始终没有连起来。')
h2('目标与意义：',
   '本项目希望把“梗”作为创作入口，用 AI 把一句非结构化的生活描述，转换成结构完整、'
   '可播放、可编辑、可导出 MIDI 的音乐作品；让不懂乐理的人也能完成一次真正的音乐创作。'
   '同时，项目刻意把 AI 的能力边界标注在界面上：哪一段是神经网络生成的音频、哪一段是算法生成的音符，'
   '用户可以一眼看清。对“AI+文化创意”的意义在于：AI 不只是生成内容，更应该生成“可继续加工的结构”。')

# ============================ 二、创意方案 ============================
h1('二、创意方案')
h2('核心创意：',
   'Meme-to-Rave——把网络热梗翻译成电子音乐。系统先对梗做“音乐化解读”（情绪落点决定调式，'
   '语速与焦虑感决定 BPM，荒诞程度决定失真与密度），再确定编制与参数，随后进入受约束作曲，'
   '最后按“前奏—铺陈—Drop—Break—二次 Drop”的段落结构编排。'
   '例如“早八打工人”被解读为 Techno、138 BPM、小调：早八的焦虑是重复的、机械的、冷的，'
   '因此使用 acid 的十六分滚动来模拟闹钟的滴答，Drop 时刻大屏打出“06:59 · 再睡五分钟”。'
   '目前内置 7 套风格预设：司凤 Rave、鬼畜切片、热梗 Techno、Hardstyle、Hyperpop、经典 EDM、'
   '混沌 Rave；每套预设决定 BPM、调式、鼓组、贝斯、主音、人声切片与段落结构。')
h2('解决方案设计：', '')
h2('问题定义：',
   '如何把一句非结构化的中文生活描述，稳定地转换成“能听、能改、能导出”的音乐作品，'
   '并在 8GB 显存的普通笔记本上真实运行，而不是停留在演示动画或占位结果。')
h2('技术选择：',
   '（1）规则化自然语言解析：从描述中抽取流派、调性、BPM、小节数、密度与能量，并输出可解释的推理链；'
   '（2）受约束作曲：在 9 条经过验证的和声进行中做选择，用 voice leading 平滑声部，'
   '以“两小节动机 + 移调/倒影/改节奏变奏”生成旋律，鼓型与贝斯写法随流派切换；'
   '（3）Web Audio 合成与 MIDI 导出：Tone.js 按小节滚动调度，导出标准 MIDI（format 1）；'
   '（3b）采样库与采样器：自建 52 个 one-shot 采样（48kHz/16bit，CC0 自制），'
   '按 7 套 kit 绑定鼓组、贝斯、主音与人声切片，用 AudioBufferSourceNode 触发，'
   '支持变调、力度、声像与复音，采样不可用时自动回退合成音色；'
   '（4）ACE-Step 1.5 神经音频生成：2B Turbo（DiT-only）、INT8 权重量化、CPU offload，'
   '在 RTX 5060 Laptop 8GB 上以约 4.45GB 显存峰值生成 48kHz float32 音频；'
   '（5）双引擎适配层：引擎状态实时探测，不可用则如实标注并自动回退，绝不伪造生成结果。')
h2('方案概要：',
   '用户输入一句描述或一个热梗 → 解析为音乐参数并给出推理理由 → 选择引擎生成'
   '（符号引擎产出可编辑音符，ACE-Step 产出真实音频）→ 在时间轴上查看和弦、段落与逐音符内容 → '
   '播放试听、静音/调音量 → 导出 MIDI 或音频。全流程离线可运行，并提供单文件版本用于现场兜底。')

# ============================ 三、作品形式 ============================
h1('三、作品形式')
h2('作品类型：', '原型系统 + 交互式数字作品（可现场操作、可导出产物）')
h2('呈现方式：',
   '现场以 1920×1080 投影运行 Web 应用，配合 PPT 与 3 分钟讲解；'
   '另提供单文件 HTML 版本（双击即可运行，无需服务器），以及两段提前生成的真实音频作为备用演示素材。')
h2('实施工具：',
   '前端：TypeScript、React 18、Tone.js、Vite/esbuild；'
   '音频生成：ACE-Step 1.5（PyTorch 2.7.1 + CUDA 12.8、INT8 量化、CPU offload）、FastAPI 推理服务；'
   '音色：52 个自制 one-shot 采样（numpy DSP 生成，CC0）、AudioBufferSourceNode 采样器；'
   '验证与材料：自建自动化测试（118 项断言）、Python（python-pptx / python-docx / Pillow）制作展示材料。')

# ============================ 四、效果 ============================
h1('四、效果')
h2('应用场景描述：',
   '（1）课堂与社团活动的开场音乐：输入当天的热点梗，几秒内得到一段可直接播放的电子乐；'
   '（2）短视频配乐：把梗转成 Drop 段落，导出 MIDI 后进入任意 DAW 继续制作；'
   '（3）音乐与编程教学演示：可现场展示“描述→参数→音符”的可解释链路。'
   '实测中，本机生成 13 秒音频约需 10 秒，符号引擎生成 16 小节工程为毫秒级。')
h2('目标人群与影响：',
   '核心用户是不懂乐理但有表达欲的普通人（学生、内容创作者），以及需要快速产出结构草稿的音乐学习者。'
   '对他们而言，作品的价值不是“替你写歌”，而是“把想法变成一份可以继续修改的工程”。')
h2('可能面临的挑战：',
   '显存限制：8GB 显卡需要 INT8 + CPU offload 才能跑 2B 模型；'
   '音频不可编辑：神经网络输出的是波形，无法在时间轴上改音符，项目选择如实标注而不是伪装；'
   '生成时长不稳定：模型对 duration 条件不精确，尾部会出现约 −60dB 的残留噪声，已在服务端做静音裁剪；'
   '现场风险：推理服务可能未启动或崩溃，因此准备了符号引擎回退、预生成音频与单文件版本三层兜底。')

# ============================ 五、结论与展望 ============================
h1('五、结论与展望')
h2('总结：',
   '项目完成了“热梗 → 音乐参数 → 可编辑工程 / 真实音频”的完整闭环，并形成四个可复述的亮点：'
   '热梗娱乐化、双引擎（算法给结构、模型给波形）、不伪装能力边界、失败可回退。'
   '关键指标：ACE-Step 显存峰值 4.45GB、生成 13 秒音频约 10 秒、输出 48kHz float32 立体声；'
   '本地音色已从振荡器合成升级为 52 个自制 one-shot 采样（7 套 kit 按风格切换）；'
   '两段真实音频的非静音占比分别为 93.3% 与 98.0%，峰值 −1.00 dBFS；'
   '项目累计 118 项自动化断言（含真实浏览器端到端与音频真伪验证）全部通过。')
h2('未来计划：',
   '（1）接入大语言模型替代规则解析，支持更复杂的语义与多轮修改；'
   '（2）增加“音频转 MIDI”能力，让神经音频也能进入可编辑链路；'
   '（3）扩充梗库与流派，支持用户自建风格模板；'
   '（4）作品分享与协作：把生成的工程变成可二次创作的链接。')

# ============================ 附录 ============================
h1('附录')
h2('Github源代码：', PLACEHOLDER + '（若不上传，可写“源码随作品交付，未公开仓库”）')
h2('参考文献：', '')
for ref in [
    'ACE-Step 官方仓库与技术报告：ACE-Step 1.5 音乐生成模型（DiT 架构）说明。',
    'Tone.js 官方文档：Web Audio 合成、Transport 调度与音频分析。',
    'MDN Web Docs：Web Audio API、Canvas 与 Media 相关规范。',
    'MIDI 1.0 Specification：Standard MIDI File（SMF）format 1 格式说明。',
    'React 官方文档：组件状态管理与生命周期。',
]:
    bullet(ref)
h2('附件材料：', '')
for att in [
    '课堂展示 PPT（DSH-Studio-2.0-课堂展示.pptx，9 页，含逐页演讲备注）。',
    '3 分钟中文演讲稿（与 PPT 逐页对应，含每页时间标注）。',
    '两段真实生成的音频（acestep-techno-128bpm.wav / acestep-early8-rave-138bpm.wav）。',
    '现场演示操作卡、一键启动脚本，以及 20 秒真实操作视频（1440×810，含真实生成音频，已嵌入 PPT）。',
    '自动化测试记录：118 项断言（核心 44 + 渲染 31 + 端到端 22 + 音频闭环 12 + 回退 9）。',
]:
    bullet(att)

doc.save(OUT)
print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB')

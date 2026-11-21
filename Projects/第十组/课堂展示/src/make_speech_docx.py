# -*- coding: utf-8 -*-
"""把演讲稿 Markdown 转成便于打印的 DOCX（去掉 Markdown 标记，保留分页时间）。"""
import os
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, '演讲稿-3分钟.md')
OUT = os.path.join(ROOT, '演讲稿-3分钟.docx')

ACCENT = RGBColor(0x0E, 0x74, 0x90)


def font(run, name, size, bold=False, color=None):
    run.font.name = name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = rPr.makeelement(qn('w:rFonts'), {})
        rPr.append(rFonts)
    rFonts.set(qn('w:eastAsia'), name)
    rFonts.set(qn('w:ascii'), name)
    rFonts.set(qn('w:hAnsi'), name)
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


doc = Document()
sec = doc.sections[0]
sec.left_margin = sec.right_margin = Pt(54)

t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
font(t.add_run('DSH Studio 2.0 · 3 分钟演讲稿'), '黑体', 18, True)

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub.paragraph_format.space_after = Pt(12)
font(sub.add_run('与 9 页 PPT 逐页对应 · 全文约 170 秒 · 留 5 秒缓冲'), '宋体', 10, False, RGBColor(0x55, 0x5F, 0x6B))

lines = open(SRC, encoding='utf-8').read().split('\n')
i = 0
while i < len(lines):
    line = lines[i].rstrip()
    i += 1
    if not line.strip():
        continue
    if line.startswith('|') or line.startswith('---') or line.startswith('>') or line.startswith('#'):
        continue
    m = re.match(r'^##\s+第\s*(\d+)\s*页\s*·\s*(.*?)\s*`(.*?)`', line)
    if m:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        font(p.add_run('第 %s 页 · %s' % (m.group(1), m.group(2))), '黑体', 13, True, ACCENT)
        r = p.add_run('　%s' % m.group(3))
        font(r, 'Consolas', 10, False, RGBColor(0x66, 0x74, 0x8A))
        continue
    if line.startswith('*（') or line.startswith('（'):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Pt(12)
        font(p.add_run(line.replace('*', '')), '楷体', 10.5, False, RGBColor(0x77, 0x88, 0x99))
        continue
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_after = Pt(2)
    clean = line.replace('**', '')
    font(p.add_run(clean), '宋体', 12)

doc.save(OUT)
print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB')

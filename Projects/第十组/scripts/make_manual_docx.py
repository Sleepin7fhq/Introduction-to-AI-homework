# -*- coding: utf-8 -*-
"""把 使用说明书.md 转成排版好的 DOCX（标题层级、表格、图片、代码块、列表）。"""
import os
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, '使用说明书.md')
OUT = os.path.join(ROOT, '使用说明书.docx')

ACCENT = RGBColor(0x0E, 0x74, 0x90)
GRAY = RGBColor(0x55, 0x5F, 0x6B)
BODY, HEAD = '宋体', '黑体'


def set_font(run, name, size, bold=False, color=None):
    run.font.name = 'Times New Roman' if name == BODY else name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = rPr.makeelement(qn('w:rFonts'), {})
        rPr.append(rFonts)
    rFonts.set(qn('w:eastAsia'), name)
    rFonts.set(qn('w:ascii'), 'Times New Roman' if name == BODY else name)
    rFonts.set(qn('w:hAnsi'), 'Times New Roman' if name == BODY else name)
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def clean_inline(text):
    """去掉 Markdown 行内标记，保留文字。"""
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = text.replace('**', '')
    return text


doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.top_margin = sec.bottom_margin = Cm(2.2)
sec.left_margin, sec.right_margin = Cm(2.4), Cm(2.0)

normal = doc.styles['Normal']
normal.font.size = Pt(10.5)
normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
normal.paragraph_format.space_after = Pt(0)
rPr = normal.element.get_or_add_rPr()
rFonts = rPr.find(qn('w:rFonts'))
if rFonts is None:
    rFonts = rPr.makeelement(qn('w:rFonts'), {})
    rPr.append(rFonts)
rFonts.set(qn('w:eastAsia'), BODY)

lines = open(SRC, encoding='utf-8').read().split('\n')
i = 0
first_h1 = True

while i < len(lines):
    line = lines[i].rstrip()
    i += 1

    if not line.strip():
        continue

    # 代码块
    if line.startswith('```'):
        block = []
        while i < len(lines) and not lines[i].startswith('```'):
            block.append(lines[i])
            i += 1
        i += 1
        for b in block:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.space_after = Pt(1)
            set_font(p.add_run(b), 'Consolas', 9, False, RGBColor(0x1B, 0x3A, 0x48))
        doc.add_paragraph()
        continue

    # 图片
    m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line)
    if m:
        path = os.path.join(ROOT, m.group(2).replace('/', os.sep))
        if os.path.exists(path):
            doc.add_picture(path, width=Cm(15.2))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.paragraph_format.space_after = Pt(8)
            set_font(cap.add_run(m.group(1)), BODY, 9, False, GRAY)
        continue

    # 标题
    m = re.match(r'^(#{1,3})\s+(.*)$', line)
    if m:
        level, text = len(m.group(1)), clean_inline(m.group(2))
        p = doc.add_paragraph()
        if level == 1:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(6)
            set_font(p.add_run(text), HEAD, 20, True)
        elif level == 2:
            p.paragraph_format.space_before = Pt(16)
            p.paragraph_format.space_after = Pt(5)
            p.paragraph_format.keep_with_next = True
            set_font(p.add_run(text), HEAD, 14, True, ACCENT)
        else:
            p.paragraph_format.space_before = Pt(9)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.keep_with_next = True
            set_font(p.add_run(text), HEAD, 11.5, True)
        continue

    # 分割线
    if line.strip() == '---':
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        pPr = p._p.get_or_add_pPr()
        pbdr = pPr.makeelement(qn('w:pBdr'), {})
        bottom = pbdr.makeelement(qn('w:bottom'), {
            qn('w:val'): 'single', qn('w:sz'): '6', qn('w:space'): '1', qn('w:color'): 'D0D8E0'})
        pbdr.append(bottom)
        pPr.append(pbdr)
        continue

    # 表格
    if line.startswith('|'):
        rows = [line]
        while i < len(lines) and lines[i].lstrip().startswith('|'):
            rows.append(lines[i].rstrip())
            i += 1
        cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
        header = cells[0]
        body = [r for r in cells[1:] if not all(re.match(r'^:?-{2,}:?$', c) for c in r)]
        cols = len(header)
        table = doc.add_table(rows=1, cols=cols)
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for j, h in enumerate(header):
            cell = table.rows[0].cells[j]
            cell.text = ''
            set_font(cell.paragraphs[0].add_run(clean_inline(h)), HEAD, 9, True)
        for r in body:
            row = table.add_row()
            for j, c in enumerate(r[:cols]):
                cell = row.cells[j]
                cell.text = ''
                set_font(cell.paragraphs[0].add_run(clean_inline(c)), BODY, 9)
        doc.add_paragraph().paragraph_format.space_after = Pt(4)
        continue

    # 引用
    if line.startswith('>'):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        set_font(p.add_run(clean_inline(line.lstrip('> ').strip())), BODY, 10, False, GRAY)
        continue

    # 有序 / 无序列表
    m = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)$', line)
    if m:
        indent = len(m.group(1))
        marker = m.group(2)
        text = clean_inline(m.group(3))
        bullet = '· ' if marker in ('-', '*') else re.match(r'(\d+)\.', marker).group(1) + '. '
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.55 + indent * 0.4)
        p.paragraph_format.first_line_indent = Cm(-0.35)
        p.paragraph_format.space_after = Pt(1)
        set_font(p.add_run(bullet + text), BODY, 10.5)
        continue

    # 正文
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    set_font(p.add_run(clean_inline(line)), BODY, 10.5)

doc.save(OUT)
print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB')

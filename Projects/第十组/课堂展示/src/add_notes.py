# -*- coding: utf-8 -*-
"""把演讲稿按页写进 PPT 备注，保证 PPT 备注与讲稿完全一致。"""
import os
import re

from pptx import Presentation

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PPTX = os.path.join(ROOT, 'DSH-Studio-2.0-课堂展示.pptx')
SPEECH = os.path.join(ROOT, '演讲稿-3分钟.md')


def parse_speech(path):
    text = open(path, encoding='utf-8').read()
    blocks = re.split(r'\n## ', text)
    pages = {}
    for b in blocks:
        m = re.match(r'第\s*(\d+)\s*页', b)
        if not m:
            continue
        idx = int(m.group(1))
        body = b.split('\n', 1)[1] if '\n' in b else ''
        # 去掉时间标注行与引用符号
        body = re.sub(r'`[^`]*`', '', body)
        lines = [ln.strip() for ln in body.split('\n')]
        kept = []
        for ln in lines:
            if not ln:
                continue
            if ln.startswith('---'):
                break
            kept.append(ln.replace('*（', '（').replace('）*', '）'))
        pages[idx] = '\n'.join(kept).strip()
    return pages


def main():
    pages = parse_speech(SPEECH)
    prs = Presentation(PPTX)
    n = len(prs.slides._sldIdLst)
    for i, slide in enumerate(prs.slides, start=1):
        text = pages.get(i)
        if not text:
            print('  slide %d: 无对应讲稿，跳过' % i)
            continue
        slide.notes_slide.notes_text_frame.text = text
        print('  slide %d: %d 字' % (i, len(text)))
    prs.save(PPTX)
    print('notes synced -> %d slides' % n)


if __name__ == '__main__':
    main()

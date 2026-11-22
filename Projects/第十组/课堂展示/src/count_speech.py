# -*- coding: utf-8 -*-
"""统计演讲稿字数与估算时长。"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPEECH = os.path.join(ROOT, '演讲稿-3分钟.md')

CJK = re.compile(r'[\u4e00-\u9fff]')
LATIN = re.compile(r'[A-Za-z0-9]')


def main():
    text = open(SPEECH, encoding='utf-8').read()
    parts = re.split(r'\n## ', text)
    total_cjk = 0
    total_latin = 0
    rows = []
    for b in parts:
        m = re.match(r'第\s*(\d+)\s*页', b)
        if not m:
            continue
        body = b.split('\n', 1)[1]
        body = body.split('---')[0]
        body = re.sub(r'`[^`]*`', '', body)
        body = re.sub(r'\*（[^）]*）\*', '', body)
        cjk = len(CJK.findall(body))
        latin = len(LATIN.findall(body))
        total_cjk += cjk
        total_latin += latin
        rows.append((int(m.group(1)), cjk, latin))

    for idx, cjk, latin in rows:
        print('  第%d页: 汉字 %3d  字母数字 %2d  约 %4.1f 秒' % (idx, cjk, latin, (cjk + latin) / 4.2))

    total = total_cjk + total_latin
    print('')
    print('合计: 汉字 %d + 字母数字 %d = %d' % (total_cjk, total_latin, total))
    for rate in (4.0, 4.2, 4.5):
        print('  按 %.1f 字/秒 → %.0f 秒（%d 分 %02d 秒）' % (
            rate, total / rate, int(total / rate) // 60, int(total / rate) % 60))
    budget = 175
    print('')
    print('3 分钟内（按 4.2 字/秒，留 5 秒缓冲）建议不超过 %d 字；当前 %d 字，%s %d 字。' % (
        int(budget * 4.2), total, '超出' if total > budget * 4.2 else '还可加', abs(int(budget * 4.2) - total)))


if __name__ == '__main__':
    main()

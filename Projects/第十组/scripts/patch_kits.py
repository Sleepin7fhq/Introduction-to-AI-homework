# -*- coding: utf-8 -*-
"""给 7 个风格补上 kit 字段。"""
import io
import re

P = r'D:\AI\aihw\src\music\styles.ts'
s = io.open(P, encoding='utf-8').read()

order = ['sifeng', 'chop', 'techno', 'hardstyle', 'hyper', 'edm', 'chaos']
counter = {'i': 0}


def repl(m):
    i = counter['i']
    counter['i'] += 1
    kit = order[i] if i < len(order) else 'edm'
    return "subHz: %s,\n      kit: '%s',\n    }," % (m.group(1), kit)


s = re.sub(r"subHz: (\d+),\n    \},", repl, s)
io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('kits added:', counter['i'])

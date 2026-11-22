# -*- coding: utf-8 -*-
"""手工梗库优先：同名/同分时，人工撰写的音乐映射比知识库条目更适合做生成。"""
import io

P = r'D:\AI\aihw\src\producer\meme.ts'
s = io.open(P, encoding='utf-8').read()

old = """    if (t.includes(card.name.toLowerCase())) score += 10;"""
new = """    if (t.includes(card.name.toLowerCase())) score += 10;
    // 人工撰写的条目带有更完整的编制映射，同等命中时优先
    if (!card.id.startsWith('kb-')) score += 1.5;"""
assert old in s
s = s.replace(old, new)
io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('findMemes priority patched')

# -*- coding: utf-8 -*-
"""把 engine.ts 里旧的 createVoice 替换成 voices.ts 的新实现，并升级主链路。"""
import io
import re

P = r'D:\AI\aihw\src\music\engine.ts'
src = io.open(P, encoding='utf-8').read()

start = src.index('export interface Voice {')
end = src.index('export class SongPlayer')
head = src[:start]
tail = src[end:]

new_block = '''import { createVoice } from './voices';
import type { Voice } from './voices';

export { createVoice };
export type { Voice };

'''

src = head + new_block + tail

# 主链路加 EQ：低频 +2dB、空气感 +1.5dB，让成品不那么"薄"
src = src.replace(
    "    this.bus = new Tone.Gain(0.9).connect(this.compressor);",
    "    // 总线 EQ：补低频重量与高频空气感（旧版直接进压缩，听起来单薄）\n"
    "    this.eq = new Tone.EQ3({ low: 2, mid: 0, high: 1.5, lowFrequency: 200, highFrequency: 3200 })\n"
    "      .connect(this.compressor);\n"
    "    this.bus = new Tone.Gain(0.9).connect(this.eq);",
)

src = src.replace(
    "  private limiter: Tone.Limiter;\n  private compressor: Tone.Compressor;",
    "  private limiter: Tone.Limiter;\n  private compressor: Tone.Compressor;\n  private eq: Tone.EQ3;",
)

io.open(P, 'w', encoding='utf-8', newline='\n').write(src)
print('engine.ts rewritten: %.1f KB' % (len(src) / 1024))

# render.ts 使用同样的 EQ
R = r'D:\AI\aihw\src\music\render.ts'
r = io.open(R, encoding='utf-8').read()
r = r.replace(
    "      const bus = new Tone.Gain(0.9).connect(comp);",
    "      const eq = new Tone.EQ3({ low: 2, mid: 0, high: 1.5, lowFrequency: 200, highFrequency: 3200 }).connect(comp);\n"
    "      const bus = new Tone.Gain(0.9).connect(eq);",
)
io.open(R, 'w', encoding='utf-8', newline='\n').write(r)
print('render.ts EQ patched:', 'EQ3' in r)

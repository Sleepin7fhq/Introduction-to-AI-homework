# -*- coding: utf-8 -*-
"""锁定风格时，让 BPM 与调式跟着风格走。"""
import io

P = r'D:\AI\aihw\src\producer\parse.ts'
s = io.open(P, encoding='utf-8').read()

start = s.index('export function applyOverrides(')
end = s.index('/** 给界面用的 key 展示 */')

new = '''export function applyOverrides(
  base: ParsedIntent,
  opts: { styleId: GenreId | 'auto'; bpm: number | 'auto'; bars: number | 'auto'; energy: number },
): ParsedIntent {
  const next: ParsedIntent = { ...base, reasoning: [...base.reasoning] };

  if (opts.styleId !== 'auto') {
    const g = GENRES.find((x) => x.id === opts.styleId);
    if (g) {
      next.genre = g;
      next.genreExplicit = true;
      next.reasoning.unshift('手动锁定风格：' + g.name);
      // 锁定风格时，速度与调式跟着风格走（否则会出现"风格 Hardstyle、速度 128"的怪结果）
      next.mode = g.mode;
      next.brightness = g.brightness;
      if (opts.bpm === 'auto') {
        next.bpm = clamp(Math.round(g.bpm), 60, 190);
        next.bpmExplicit = false;
      }
    }
  }
  if (opts.bpm !== 'auto') {
    next.bpm = clamp(Math.round(opts.bpm), 60, 190);
    next.bpmExplicit = true;
    next.reasoning.unshift('手动锁定速度：' + next.bpm + ' BPM');
  }
  if (opts.bars !== 'auto') {
    next.bars = clamp(Math.round(opts.bars), 2, 64);
    next.barsExplicit = true;
    next.reasoning.unshift('手动锁定长度：' + next.bars + ' 小节');
  }
  next.energy = clamp(opts.energy, 0, 1);
  next.density = clamp(next.genre.density * 0.75 + next.energy * 0.35, 0.2, 1);
  next.durationSec = Math.round((next.bars * 4 * 60) / next.bpm);
  return next;
}

'''

s = s[:start] + new + s[end:]
io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('applyOverrides rewritten; style->bpm/mode wired')

# -*- coding: utf-8 -*-
"""把研究知识库并入 meme.ts（保留原有 16 条，追加 42 条并去重）。"""
import io
import re

P = r'D:\AI\aihw\src\producer\meme.ts'
s = io.open(P, encoding='utf-8').read()

# 1) MemeCard 增加来源字段
s = s.replace(
    "  /** 音色/织体提示 */\n  palette: string;\n}",
    "  /** 音色/织体提示 */\n  palette: string;\n"
    "  /** 以下为知识库溯源信息（可选） */\n"
    "  sources?: string[];\n"
    "  confidence?: 'high' | 'medium' | 'low';\n"
    "  verified?: boolean;\n"
    "  era?: string;\n"
    "  category?: string;\n"
    "  originNote?: string;\n}",
)

# 2) 导入知识库
s = s.replace(
    "import type { GenreId } from '../music/genre';\nimport { GENRES } from '../music/genre';",
    "import type { GenreId } from '../music/genre';\nimport { GENRES } from '../music/genre';\n"
    "import { RESEARCH_MEMES } from './memeKB';\nimport type { ResearchMeme } from './memeKB';",
)

# 3) 原数组改名
s = s.replace('export const MEMES: MemeCard[] = [', 'const CURATED_MEMES: MemeCard[] = [')

# 4) 在 hash() 之前插入适配器与合并
anchor = 'function hash(text: string): number {'
adapter = '''/** 研究知识库条目 → 梗卡（补齐风格画像里缺的参数） */
function cardFromResearch(r: ResearchMeme): MemeCard {
  const g = GENRES.find((x) => x.id === (r.style as GenreId));
  return {
    id: 'kb-' + r.id,
    name: r.name,
    emoji: r.emoji || '🎛️',
    keywords: r.keywords.length > 0 ? r.keywords : [r.name],
    concept: r.musicFit || r.context || r.usage,
    punchline: r.punchline || r.usage || r.name,
    genreId: (g ? g.id : 'meme_techno') as GenreId,
    bpm: r.bpm > 40 ? r.bpm : 128,
    density: g ? g.density : 0.8,
    energy: g ? Math.min(1, g.dynamics + 0.05) : 0.8,
    brightness: g ? g.brightness : 0.5,
    tags: [r.category, g ? g.name : r.style].filter(Boolean),
    dropLine: r.punchline || r.name,
    why: [r.originNote, r.context].filter(Boolean).join(' '),
    palette: r.timbre || 'synth + drums',
    sources: r.sources,
    confidence: r.confidence,
    verified: r.verified,
    era: r.era,
    category: r.category,
    originNote: r.originNote,
  };
}

/** 手工梗库 + 研究知识库；同名以手工条目为准 */
export const MEMES: MemeCard[] = (() => {
  const seen = new Set(CURATED_MEMES.map((m) => m.name));
  const extra: MemeCard[] = [];
  for (const r of RESEARCH_MEMES) {
    const card = cardFromResearch(r);
    if (seen.has(card.name)) continue;
    seen.add(card.name);
    extra.push(card);
  }
  return [...CURATED_MEMES, ...extra];
})();

function hash(text: string): number {'''
assert anchor in s
s = s.replace(anchor, adapter, 1)

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('meme.ts patched; total curated + research merged')

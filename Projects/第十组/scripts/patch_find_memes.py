# -*- coding: utf-8 -*-
"""findMemes 改成两级检索：手工梗库优先，知识库兜底扩展覆盖面。"""
import io

P = r'D:\AI\aihw\src\producer\meme.ts'
s = io.open(P, encoding='utf-8').read()

start = s.index('/** 在梗库里按关键词找，命中越多越靠前 */')
end = s.index('export function fallbackCard')

new = '''/**
 * 两级检索：
 *   1) 先查人工撰写的 16 条（编制映射更完整，生成的音乐更可控）；
 *   2) 没有命中，再查 42 条研究知识库（覆盖面广，用于新梗）。
 * 这样既不会丢掉质量，也不会因为"库里没有"而空手。
 */
export function findMemes(text: string, limit = 3): MemeCard[] {
  const t = text.trim().toLowerCase();
  if (!t) return [];

  const scoreOne = (card: MemeCard) => {
    let score = 0;
    for (const k of card.keywords) {
      const kk = k.toLowerCase();
      if (!t.includes(kk)) continue;
      score += keywordWeight(kk);
      const at = t.indexOf(kk);
      if (at >= 0 && at <= 6) score += 1.2;
    }
    if (t.includes(card.name.toLowerCase())) score += 10;
    return score;
  };

  const rank = (cards: MemeCard[]) =>
    cards
      .map((card) => ({ card, score: scoreOne(card) }))
      .filter((x) => x.score > 0)
      .sort((a, b) => b.score - a.score);

  const curated = rank(CURATED_MEMES);
  const research = rank(MEMES.filter((m) => m.id.startsWith('kb-')));
  const chosen = curated.length > 0 ? curated : research;
  return chosen.slice(0, limit).map((x) => x.card);
}

'''
s = s[:start] + new + s[end:]
io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('findMemes rewritten (two-tier)')

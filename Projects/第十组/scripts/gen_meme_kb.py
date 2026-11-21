# -*- coding: utf-8 -*-
"""把研究得到的 42 条热梗 JSON 转成 TypeScript 知识库模块。"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, '音乐风格升级', '研究', '热梗候选.json')
OUT = os.path.join(ROOT, 'src', 'producer', 'memeKB.ts')

EMOJI = {
    '鬼畜': '🎬',
    '音乐': '🎵',
    '游戏': '🎮',
    '动漫': '📺',
    '影视': '🎞️',
    '抽象': '🌀',
    '校园': '🎒',
    '近期': '🔥',
}


def js(s):
    return json.dumps(s, ensure_ascii=False)


def main():
    data = json.load(io.open(SRC, encoding='utf-8'))
    rows = []
    for e in data:
        rows.append({
            'id': e['id'],
            'name': e['name'],
            'category': e.get('category', ''),
            'era': e.get('era', ''),
            'emoji': EMOJI.get(e.get('category', ''), '🎛️'),
            'keywords': list(dict.fromkeys([e['name']] + [v for v in e.get('variants', []) if len(v) >= 2]))[:6],
            'originNote': e.get('origin_note', ''),
            'context': e.get('context', ''),
            'usage': e.get('usage', ''),
            'punchline': e.get('punchline', ''),
            'musicFit': e.get('music_fit', ''),
            'style': e.get('style', 'meme_techno'),
            'bpm': int(e.get('bpm', 128)),
            'timbre': e.get('timbre', ''),
            'prompt': e.get('prompt', ''),
            'sources': e.get('sources', []),
            'confidence': e.get('confidence', 'low'),
            'verified': bool(e.get('verified', False)),
        })

    lines = []
    lines.append('/**')
    lines.append(' * 热梗知识库（自动生成，勿手改）。')
    lines.append(' * 数据源：音乐风格升级/研究/热梗候选.json')
    lines.append(' * 每条保留 sources / confidence / verified，未核实的条目标记为 low + false。')
    lines.append(' * 生成脚本：scripts/gen_meme_kb.py')
    lines.append(' */')
    lines.append('')
    lines.append('export interface ResearchMeme {')
    lines.append('  id: string;')
    lines.append('  name: string;')
    lines.append('  category: string;')
    lines.append('  era: string;')
    lines.append('  emoji: string;')
    lines.append('  keywords: string[];')
    lines.append('  originNote: string;')
    lines.append('  context: string;')
    lines.append('  usage: string;')
    lines.append('  punchline: string;')
    lines.append('  musicFit: string;')
    lines.append('  style: string;')
    lines.append('  bpm: number;')
    lines.append('  timbre: string;')
    lines.append('  prompt: string;')
    lines.append('  sources: string[];')
    lines.append('  confidence: \'high\' | \'medium\' | \'low\';')
    lines.append('  verified: boolean;')
    lines.append('}')
    lines.append('')
    lines.append('export const RESEARCH_MEMES: ResearchMeme[] = [')
    for r in rows:
        lines.append('  {')
        for k in ('id', 'name', 'category', 'era', 'emoji'):
            lines.append('    %s: %s,' % (k, js(r[k])))
        lines.append('    keywords: [%s],' % ', '.join(js(k) for k in r['keywords']))
        for k in ('originNote', 'context', 'usage', 'punchline', 'musicFit', 'style', 'timbre', 'prompt'):
            lines.append('    %s: %s,' % (k, js(r[k])))
        lines.append('    bpm: %d,' % r['bpm'])
        lines.append('    sources: [%s],' % ', '.join(js(s) for s in r['sources']))
        lines.append('    confidence: %s,' % js(r['confidence']))
        lines.append('    verified: %s,' % ('true' if r['verified'] else 'false'))
        lines.append('  },')
    lines.append('];')
    lines.append('')
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('wrote %s  entries=%d  %.1f KB' % (OUT, len(rows), os.path.getsize(OUT) / 1024))


if __name__ == '__main__':
    main()

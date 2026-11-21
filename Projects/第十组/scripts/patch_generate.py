# -*- coding: utf-8 -*-
"""给生成器接入：风格化鼓组 preset + 人声切片轨。"""
import io

P = r'D:\AI\aihw\src\music\generate.ts'
src = io.open(P, encoding='utf-8').read()

# 1) 鼓组 preset 随风格变化（hardstyle / rave / electronic）
old_drums = "track('t-drums', '鼓组', 'drums', 0.82, drumNotes(genre.drums, bars, rng, [leadFrom - 1]), 'electronic'),"
new_drums = (
    "track('t-drums', '鼓组', 'drums', 0.82, drumNotes(genre.drums, bars, rng, [leadFrom - 1]), drumPresetFor(genre)),"
)
assert old_drums in src
src = src.replace(old_drums, new_drums)

# 2) 人声切片轨：只在新风格且 sound.chop 为真时生成
anchor = "  const lead = generateLead(chords, key, rng, genre.density, leadFrom, bars);\n  if (lead.length > 0) {\n    tracks.push(track('t-lead', '主旋律', 'lead', 0.6, lead, genre.lead));\n  }"
assert anchor in src
addition = anchor + """

  // 人声切片轨：司凤 / 鬼畜 / Hyperpop 的"记忆点"来源。
  // 用共振峰合成发 /a/ /e/ 元音，按 16 或 32 分音符切，形成节奏化的"邦吧邦吧"。
  if (genre.sound?.chop) {
    const chops = generateChops(chords, bars, rng, leadFrom);
    if (chops.length > 0) {
      tracks.push(track('t-chop', '人声切片', 'lead', 0.62, chops, 'a'));
    }
  }"""
src = src.replace(anchor, addition)

# 3) 追加两个工具函数（放在 track() 定义之前）
marker = "function track(\n"
helpers = '''/** 根据风格画像选择鼓组音色取向 */
function drumPresetFor(genre: GenreSpec): string {
  const kick = genre.sound?.kick;
  if (kick === 'hard') return 'hardstyle';
  if (kick === 'rave' || kick === 'click') return 'rave';
  return 'electronic';
}

/**
 * 人声切片：把和弦内音切成密集的短音，制造"邦吧邦吧"的记忆点。
 * 80% 的切点发声、重拍加重、音高在 4 个音里循环——不是随机撒音符。
 */
function generateChops(chords: ChordEvent[], bars: number, rng: () => number, fromBar: number): Note[] {
  const out: Note[] = [];
  const rate = 8; // 每拍 8 刀 = 32 分音符
  const step = 1 / rate;
  for (let bar = fromBar; bar < bars; bar++) {
    const ev = chords[bar];
    if (!ev) continue;
    const tones = chordPitches(ev.chord, 4, 0);
    const pool = [tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[0] + 24];
    for (let i = 0; i < 4 * rate; i++) {
      if (rng() < 0.16) continue;
      const accent = i % 4 === 0;
      out.push({
        pitch: pool[(i + bar) % pool.length],
        start: bar * 4 + i * step,
        dur: Math.max(0.07, step * 0.85),
        vel: accent ? 0.85 : 0.5 + rng() * 0.2,
      });
    }
  }
  return out;
}

function track(
'''
assert marker in src
src = src.replace(marker, helpers, 1)

io.open(P, 'w', encoding='utf-8', newline='\n').write(src)
print('generate.ts patched:', 'generateChops' in src, '|', 'drumPresetFor' in src)

/**
 * 司凤音乐歌词加工器。
 *
 * 复刻自 B 站教程《零基础司凤音乐制作教程》里的歌词提示词规则：
 * 把普通歌词转换成带结构标签 + scat 拟声加花的格式，直接粘进 Suno。
 *
 * 规则是确定性的（段落标签、拟声位置、不增删歌词），所以不需要 LLM。
 */

export const SUNO_STYLE_PROMPT =
  'EDM; gruff smoky male baritone lead with stacked vocal doubles; bright synth-pluck arpeggios and synth brass over sidechained bass, punchy snare and crisp hi-hats; sidechain-pumped mix at a driving 126-132 BPM four-on-the-floor groove; short instrumental intro driven by rhythmic scat syllables and raw shout ad-libs, rising synth sweeps and impact-drop transitions into a big chorus drop; gritty raspy timbre, coarse gravelly edge, raw chest-voice ad-libs, falsetto yelps and rapid-fire scat runs. Short scat intro, three lines maximum. Single male lead only. Preserve the uploaded melody, phrasing and song structure.';

export const SUNO_EXCLUDE =
  'female vocal, female backing vocals, female harmony, duet, girl group, choir, clean pop vocal, bright glossy vocal, funk, soul, jazz, acoustic guitar, live band, rock, orchestral';

/** 拟声素材池：长短、重音、停顿都要有变化 */
const SCAT_LINES = [
  ['Ha! ha! Woo!', 'Pa! pa! — Ha!', 'Ooh— woo! ha!'],
  ['Pa! ha! — woo!', 'Ha! ooh! pa!', 'Woo— oww! ha!'],
  ['Ha! — pa! pa!', 'Oww! woo!', 'Pa! ha! ooh—'],
];

const TAIL_ADLIBS = ['(Woo!)', '(Pa! Pa!)', '(Ah!)', '(Ha!)', '(Ooh!)', '(Oww!)'];

const SECTION_ORDER = [
  'Verse 1',
  'Pre-Chorus 1',
  'Chorus 1',
  'Verse 2',
  'Pre-Chorus 2',
  'Chorus 2',
  'Bridge',
  'Chorus 3',
];

export interface TagResult {
  text: string;
  sections: number;
  adlibs: number;
}

function pick<T>(arr: T[], i: number): T {
  return arr[i % arr.length];
}

/**
 * 按教程规则加工歌词。
 * 不增删原歌词，只加标签、拟声、空行。
 */
export function tagLyrics(raw: string, rng: () => number = Math.random): TagResult {
  const blocks = raw
    .split(/\n\s*\n/)
    .map((b) => b.trim())
    .filter(Boolean);
  if (blocks.length === 0) return { text: '', sections: 0, adlibs: 0 };

  const out: string[] = [];
  let adlibs = 0;

  // 1. 开头用 [Instrumental solo] 代替前奏，下面三行不同的 scat
  out.push('[Instrumental solo]');
  for (const line of SCAT_LINES[0]) out.push(line);
  out.push('');

  blocks.forEach((block, idx) => {
    const label = SECTION_ORDER[Math.min(idx, SECTION_ORDER.length - 1)];

    // [Bridge] 之前加 [Build up]，并按"低沉哼唱 → 短促 Ha!/Pa! → 高音假声"三层推进
    if (label === 'Bridge') {
      out.push('[Build up]');
      out.push('Mmm— hmm— (low hum)');
      out.push('Ha! pa! ha! pa!');
      out.push('Ooh— woo! (falsetto)');
      out.push('');
    }

    out.push(`[${label}]`);

    const lines = block.split('\n').map((l) => l.trim()).filter(Boolean);
    lines.forEach((line, i) => {
      // Verse / Pre-Chorus：每句或隔句句尾插短促加花
      const wantsAdlib = label.startsWith('Verse') || label.startsWith('Pre-Chorus');
      if (wantsAdlib && (i % 2 === 0 || rng() < 0.4)) {
        out.push(`${line} ${pick(TAIL_ADLIBS, Math.floor(rng() * TAIL_ADLIBS.length))}`);
        adlibs += 1;
      } else {
        out.push(line);
      }
    });

    // 连续 Chorus 之后加 [Break]，下面 3-5 行密集拟声，两处不重复
    if (label.startsWith('Chorus')) {
      const next = blocks[idx + 1];
      if (next) {
        out.push('');
        out.push('[Break]');
        const set = SCAT_LINES[(out.filter((l) => l === '[Break]').length) % SCAT_LINES.length];
        for (const line of set) out.push(line);
        out.push('');
        return;
      }
    }

    out.push('');
  });

  // 结尾
  out.push('[Outro]');
  out.push('Ooh— woo— hmm.');
  out.push('(Ha!) (Pa!)');
  out.push('');
  out.push('[End]');

  return { text: out.join('\n').replace(/\n{3,}/g, '\n\n').trim(), sections: blocks.length, adlibs };
}

/** 拆分歌词段落（给 UI 显示段落数用） */
export function countBlocks(raw: string): number {
  return raw
    .split(/\n\s*\n/)
    .map((b) => b.trim())
    .filter(Boolean).length;
}

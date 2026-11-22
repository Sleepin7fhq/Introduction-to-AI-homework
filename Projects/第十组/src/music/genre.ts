import type { Mode } from './types';
import { EXTRA_GENRES } from './styles';
import type { SoundProfile } from './styles';

/**
 * 电子乐流派。
 *
 * 每个流派不是换一组参数就完事，而是换一整套"编制习惯"：
 * 鼓型、贝斯写法、和弦织体、音色预设都要跟着变。
 * house 的反拍贝斯和 trap 的 808 是两种完全不同的演奏逻辑。
 */

export type GenreId =
  | 'house'
  | 'techno'
  | 'dnb'
  | 'trap'
  | 'synthwave'
  | 'electropop'
  | 'rock'
  | 'ambient'
  | 'sifeng'
  // 2.1 新增风格（见 styles.ts）
  | 'sifeng_rave'
  | 'ghost_chop'
  | 'meme_techno'
  | 'hardstyle'
  | 'hyperpop'
  | 'classic_edm'
  | 'chaos_rave';

export type BassStyle =
  | 'sub'
  | 'acid'
  | 'reese'
  | 'e808'
  | 'pluck'
  | 'rave'
  | 'hard'
  | 'hoover';
export type KeysStyle = 'stab' | 'stab_wide' | 'supersaw' | 'pluck';
export type LeadStyle =
  | 'saw'
  | 'square'
  | 'bell'
  | 'soft'
  | 'grit'
  | 'rave'
  | 'hard'
  | 'siren'
  | 'vocal'
  | 'hyper';

export interface DrumKit {
  kick: string;
  snare: string;
  clap: string;
  hat: string;
  open: string;
}

export interface GenreSpec {
  id: GenreId;
  name: string;
  keywords: string[];
  bpm: number;
  mode: Mode;
  brightness: number;
  density: number;
  groove: number;
  tension: number;
  dynamics: number;
  drums: DrumKit;
  bass: BassStyle;
  keys: KeysStyle;
  lead: LeadStyle;
  tags: string[];
  /** 2.1 新增：音色画像（仅新风格有） */
  sound?: SoundProfile;
}

const K = (kick: string, snare: string, clap: string, hat: string, open: string): DrumKit => ({
  kick,
  snare,
  clap,
  hat,
  open,
});

const BASE_GENRES: GenreSpec[] = [
  {
    id: 'house',
    name: 'House',
    keywords: ['house', '浩室', '四踩', 'deep house', 'tech house'],
    bpm: 124,
    mode: 'minor',
    brightness: 0.6,
    density: 0.62,
    groove: 0.84,
    tension: 0.3,
    dynamics: 0.6,
    // 四踩底鼓 + 反拍开镲 + 2/4 拍手
    drums: K('x...x...x...x...', '................', '....x.......x...', 'x.x.x.x.x.x.x.x.', '..x...x...x...x.'),
    bass: 'sub',
    keys: 'stab',
    lead: 'saw',
    tags: ['house', '四踩', '反拍'],
  },
  {
    id: 'techno',
    name: 'Techno',
    keywords: ['techno', '科技舞曲', '地下', '工业', 'acid', 'acid house'],
    bpm: 132,
    mode: 'minor',
    brightness: 0.4,
    density: 0.7,
    groove: 0.82,
    tension: 0.5,
    dynamics: 0.55,
    drums: K('x...x...x...x...', '................', '....x.......x...', 'x.x.x.x.x.x.x.x.', '......x.......x.'),
    bass: 'acid',
    keys: 'stab',
    lead: 'saw',
    tags: ['techno', 'acid', '冷'],
  },
  {
    id: 'dnb',
    name: 'Drum & Bass',
    keywords: ['dnb', 'drum and bass', '鼓打贝斯', 'jungle', 'd&b', 'dnb鼓'],
    bpm: 174,
    mode: 'minor',
    brightness: 0.5,
    density: 0.86,
    groove: 0.9,
    tension: 0.55,
    dynamics: 0.7,
    drums: K('x.......x.x.....', '....x.......x...', '................', 'x.x.x.x.x.x.x.x.', '................'),
    bass: 'reese',
    keys: 'supersaw',
    lead: 'soft',
    tags: ['dnb', 'breakbeat', '高速'],
  },
  {
    id: 'trap',
    name: 'Trap',
    keywords: ['trap', '陷阱', '808', 'hihat', '说唱', 'hiphop', 'hip-hop'],
    bpm: 140,
    mode: 'minor',
    brightness: 0.38,
    density: 0.6,
    groove: 0.72,
    tension: 0.55,
    dynamics: 0.5,
    // 半拍：军鼓只落在第 3 拍，808 拖着走
    drums: K('x.......x.......', '........x.......', '................', 'xxxxxxxxxxxxxxxx', '................'),
    bass: 'e808',
    keys: 'pluck',
    lead: 'bell',
    tags: ['trap', '808', '半拍'],
  },
  {
    id: 'synthwave',
    name: 'Synthwave',
    keywords: ['synthwave', '合成器浪潮', '复古', 'retro', '80年代', '八零年代'],
    bpm: 108,
    mode: 'minor',
    brightness: 0.62,
    density: 0.6,
    groove: 0.66,
    tension: 0.38,
    dynamics: 0.6,
    drums: K('x...x...x...x...', '....x.......x...', '................', 'x.x.x.x.x.x.x.x.', '..............x.'),
    bass: 'pluck',
    keys: 'supersaw',
    lead: 'saw',
    tags: ['synthwave', '复古合成器', '宽'],
  },
  {
    id: 'electropop',
    name: '电子流行',
    keywords: ['流行', 'electropop', '电子流行', 'pop', '舞曲'],
    bpm: 118,
    mode: 'major',
    brightness: 0.78,
    density: 0.6,
    groove: 0.74,
    tension: 0.2,
    dynamics: 0.62,
    drums: K('x...x...x...x...', '................', '....x.......x...', 'x.x.x.x.x.x.x.x.', '..x...x...x...x.'),
    bass: 'pluck',
    keys: 'stab',
    lead: 'square',
    tags: ['电子流行', '明亮', '舞曲'],
  },
  {
    id: 'rock',
    name: '电子摇滚',
    keywords: ['摇滚', 'rock', '失真', '电吉他', 'metal', '工业摇滚'],
    bpm: 142,
    mode: 'minor',
    brightness: 0.55,
    density: 0.8,
    groove: 0.78,
    tension: 0.64,
    dynamics: 0.8,
    drums: K('x...x...x...x.x.', '....x.......x...', '................', 'x.x.x.x.x.x.x.x.', '..............x.'),
    bass: 'pluck',
    keys: 'stab',
    lead: 'saw',
    tags: ['电子摇滚', '失真', '驱动'],
  },
  {
    id: 'ambient',
    name: '氛围电子',
    keywords: ['ambient', '氛围', '环境', '纯音乐', '冥想'],
    bpm: 74,
    mode: 'minor',
    brightness: 0.34,
    density: 0.3,
    groove: 0.3,
    tension: 0.36,
    dynamics: 0.42,
    drums: K('x...............', '................', '................', '........x.......', '................'),
    bass: 'sub',
    keys: 'supersaw',
    lead: 'soft',
    tags: ['ambient', '铺底', '留白'],
  },
  {
    id: 'sifeng',
    name: '司凤版',
    keywords: ['司凤', '死风', '嘶吼', '电音改编', '魔改', '破音', '整活'],
    bpm: 168,
    mode: 'minor',
    brightness: 0.52,
    density: 0.95,
    groove: 0.9,
    tension: 0.72,
    dynamics: 0.9,
    // 密集：四踩 + 16 分踩镲 + 2/4 拍手叠军鼓 + 反拍开镲
    drums: K('x...x...x...x..x', '....x.......x...', '....x.......x...', 'xxxxxxxxxxxxxxxx', '..x...x...x...x.'),
    bass: 'acid',
    keys: 'stab',
    lead: 'grit',
    tags: ['司凤版', '高速电音', '破音'],
  },
];

export const GENRES: GenreSpec[] = [...BASE_GENRES, ...(EXTRA_GENRES as unknown as GenreSpec[])];

/** 明确写了流派词就优先用；否则返回 null 交给情绪推断 */
export function matchGenre(text: string): GenreSpec | null {
  const t = text.toLowerCase();
  let best: GenreSpec | null = null;
  let bestLen = 0;
  for (const g of GENRES) {
    for (const k of g.keywords) {
      if (t.includes(k.toLowerCase()) && k.length > bestLen) {
        best = g;
        bestLen = k.length;
      }
    }
  }
  return best;
}

/** 只给了情绪没给流派时，按情绪的情绪色推测一种电子编制 */
export function genreForMood(moodName: string): GenreSpec {
  const byId: Record<string, GenreId> = {
    深夜霓虹: 'synthwave',
    窗边听雨: 'ambient',
    一个人的房间: 'synthwave',
    清晨的海: 'electropop',
    冲向舞台: 'house',
    赛博清晨: 'techno',
    回不去的夏天: 'electropop',
    在公路上: 'synthwave',
    毕业那天: 'synthwave',
    凌晨的办公室: 'house',
    地铁末班车: 'dnb',
    下雪那天: 'ambient',
    心动的瞬间: 'electropop',
    失控: 'rock',
  };
  const id = byId[moodName] ?? 'electropop';
  return GENRES.find((g) => g.id === id) ?? GENRES[5];
}

/** 上传参考曲目时：用速度、明暗、律动反推最接近的流派 */
export function genreFromStyle(bpm: number, brightness: number, groove: number): GenreSpec {
  const pick = (id: GenreId) => GENRES.find((g) => g.id === id) ?? GENRES[5];
  if (bpm >= 160) return pick('dnb');
  if (bpm >= 136 && groove > 0.65) return pick(bpm > 138 && groove < 0.78 ? 'trap' : 'rock');
  if (bpm >= 118 && brightness > 0.6) return pick('electropop');
  if (bpm >= 120) return pick('house');
  if (brightness < 0.4) return pick('ambient');
  return pick('synthwave');
}

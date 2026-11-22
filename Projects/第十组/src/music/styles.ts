import type { DrumKit, GenreSpec, GenreId } from './genre';
import type { Mode } from './types';

/**
 * 扩展风格库（7 个）。
 *
 * 每个风格不只是"换个 BPM"，而是一整套编制习惯：
 * 鼓组的音色取向、贝斯的分层方式、主音的合成器类型与效果链、
 * 人声切片怎么切、段落怎么走、Drop 怎么设计。
 *
 * sound 字段被音频引擎读取（决定音色分支与效果量），
 * 其余字段（structure/dropBars/chop）被生成器与编曲读取。
 */

export type KickTone = 'punch' | 'hard' | 'deep' | 'click' | 'rave';
export type SnareTone = 'crack' | 'clap' | 'rim';
export type HatTone = 'tight' | 'bright' | 'loose';
export type BassTone = 'sub' | 'acid' | 'reese' | 'e808' | 'rave' | 'hard' | 'hoover' | 'pluck';
export type LeadTone =
  | 'saw'
  | 'grit'
  | 'soft'
  | 'square'
  | 'bell'
  | 'rave'
  | 'hard'
  | 'siren'
  | 'vocal'
  | 'hyper';
export type KeysTone = 'stab' | 'stab_wide' | 'supersaw' | 'pluck' | 'piano';
export type PadTone = 'warm' | 'dark' | 'wide' | 'none';

export interface SoundProfile {
  kick: KickTone;
  snare: SnareTone;
  hat: HatTone;
  /** 总线失真量 0-1（越大越"脏"，Hardstyle/Chaos 高） */
  drive: number;
  /** 混响送出量 0-1 */
  reverb: number;
  /** 延迟送出量 0-1 */
  delay: number;
  /** 是否额外生成"人声切片"轨 */
  chop: boolean;
  /** 切片密度：每拍切几刀（4=16分，8=32分） */
  chopRate: number;
  /** 段落骨架：决定 intro/build 的长度 */
  structure: 'edm' | 'rave' | 'hardstyle' | 'meme';
  /** Drop 持续小节数 */
  dropBars: number;
  /** 低频重心：sub 的截止频率 */
  subHz: number;
  /** 采样套件 id（对应 src/audio/sampler.ts 的 KITS） */
  kit: string;
}

const K = (kick: string, snare: string, clap: string, hat: string, open: string): DrumKit => ({
  kick,
  snare,
  clap,
  hat,
  open,
});

export interface ExtraGenreSpec extends GenreSpec {
  sound: SoundProfile;
}

export const EXTRA_GENRES: ExtraGenreSpec[] = [
  {
    id: 'sifeng_rave' as GenreId,
    name: '司凤 Rave',
    keywords: ['司凤', '司凤版', '雨爱司凤', '小曲', '魔性', '鬼畜电音', '整活'],
    bpm: 172,
    mode: 'minor' as Mode,
    brightness: 0.55,
    density: 0.96,
    groove: 0.9,
    tension: 0.75,
    dynamics: 0.92,
    // 四踩 + 16 分踩镲 + 2/4 拍手；过门靠最后两拍军鼓
    drums: K('x...x...x...x..x', '....x.......x...', '....x.......x...', 'xxxxxxxxxxxxxxxx', '..x...x...x...x.'),
    bass: 'rave' as never,
    keys: 'stab_wide' as never,
    lead: 'siren' as never,
    tags: ['司凤', '夸张人声', '魔性', '升调'],
    sound: {
      kick: 'rave',
      snare: 'crack',
      hat: 'bright',
      drive: 0.62,
      reverb: 0.3,
      delay: 0.26,
      chop: true,
      chopRate: 4,
      structure: 'rave',
      dropBars: 8,
      subHz: 48,
      kit: 'sifeng',
    },
  },
  {
    id: 'ghost_chop' as GenreId,
    name: '鬼畜切片',
    keywords: ['鬼畜', '音mad', '音MAD', '调教', '人声切片', '卡点', '人力', '二创'],
    bpm: 146,
    mode: 'minor' as Mode,
    brightness: 0.5,
    density: 0.88,
    groove: 0.94,
    tension: 0.6,
    dynamics: 0.86,
    // 半拍军鼓 + 反拍底鼓，留空隙给切片
    drums: K('x.....x.x.......', '........x.......', '................', 'x.x.x.x.x.x.x.x.', '......x........'),
    bass: 'e808' as never,
    keys: 'pluck' as never,
    lead: 'vocal' as never,
    tags: ['音MAD', '切片', '卡点', '重复'],
    sound: {
      kick: 'punch',
      snare: 'clap',
      hat: 'tight',
      drive: 0.35,
      reverb: 0.22,
      delay: 0.3,
      chop: true,
      chopRate: 8,
      structure: 'meme',
      dropBars: 4,
      subHz: 52,
      kit: 'chop',
    },
  },
  {
    id: 'meme_techno' as GenreId,
    name: '热梗 Techno',
    keywords: ['热梗', '洗脑', '循环', '梗曲', 'meme techno', '抽象电音'],
    bpm: 132,
    mode: 'minor' as Mode,
    brightness: 0.42,
    density: 0.82,
    groove: 0.86,
    tension: 0.6,
    dynamics: 0.72,
    drums: K('x...x...x...x...', '................', '....x.......x...', 'x.x.x.x.x.x.x.x.', '......x.......x.'),
    bass: 'acid' as never,
    keys: 'stab' as never,
    lead: 'rave' as never,
    tags: ['Techno', '循环', '洗脑', '冷'],
    sound: {
      kick: 'deep',
      snare: 'rim',
      hat: 'tight',
      drive: 0.4,
      reverb: 0.24,
      delay: 0.2,
      chop: false,
      chopRate: 4,
      structure: 'edm',
      dropBars: 8,
      subHz: 46,
      kit: 'techno',
    },
  },
  {
    id: 'hardstyle' as GenreId,
    name: 'Hardstyle',
    keywords: ['hardstyle', '硬核', '硬派', 'reverse bass', 'rawstyle', '强kick'],
    bpm: 152,
    mode: 'minor' as Mode,
    brightness: 0.5,
    density: 0.9,
    groove: 0.88,
    tension: 0.8,
    dynamics: 0.95,
    // 四踩 kick；2/4 拍军鼓强化；反拍开镲
    drums: K('x...x...x...x...', '....x.......x...', '................', '..x...x...x...x.', '..............x.'),
    bass: 'hard' as never,
    keys: 'stab' as never,
    lead: 'hard' as never,
    tags: ['Hardstyle', 'Reverse Bass', '强 Kick'],
    sound: {
      kick: 'hard',
      snare: 'crack',
      hat: 'tight',
      drive: 0.72,
      reverb: 0.2,
      delay: 0.12,
      chop: false,
      chopRate: 4,
      structure: 'hardstyle',
      dropBars: 8,
      subHz: 44,
      kit: 'hardstyle',
    },
  },
  {
    id: 'hyperpop' as GenreId,
    name: 'Hyperpop',
    keywords: ['hyperpop', '超流行', '高能', '碎片化', '气泡音', 'future pop'],
    bpm: 160,
    mode: 'major' as Mode,
    brightness: 0.86,
    density: 0.92,
    groove: 0.76,
    tension: 0.55,
    dynamics: 0.9,
    drums: K('x...x...x...x...', '....x.......x...', '....x.......x...', 'xxxxxxxxxxxxxxxx', '..x...x...x...x.'),
    bass: 'e808' as never,
    keys: 'pluck' as never,
    lead: 'hyper' as never,
    tags: ['Hyperpop', '高亮', '碎片', '失真'],
    sound: {
      kick: 'punch',
      snare: 'clap',
      hat: 'bright',
      drive: 0.5,
      reverb: 0.3,
      delay: 0.34,
      chop: true,
      chopRate: 8,
      structure: 'edm',
      dropBars: 8,
      subHz: 50,
      kit: 'hyper',
    },
  },
  {
    id: 'classic_edm' as GenreId,
    name: '经典 EDM',
    keywords: ['edm', 'festival', '主流电音', '电音流行', 'big room', '音乐节'],
    bpm: 128,
    mode: 'major' as Mode,
    brightness: 0.8,
    density: 0.7,
    groove: 0.8,
    tension: 0.35,
    dynamics: 0.8,
    drums: K('x...x...x...x...', '................', '....x.......x...', 'x.x.x.x.x.x.x.x.', '..x...x...x...x.'),
    bass: 'sub' as never,
    keys: 'supersaw' as never,
    lead: 'saw' as never,
    tags: ['EDM', 'Festival', '宽', '悦耳'],
    sound: {
      kick: 'punch',
      snare: 'clap',
      hat: 'tight',
      drive: 0.28,
      reverb: 0.34,
      delay: 0.28,
      chop: false,
      chopRate: 4,
      structure: 'edm',
      dropBars: 8,
      subHz: 50,
      kit: 'edm',
    },
  },
  {
    id: 'chaos_rave' as GenreId,
    name: '混沌 Rave',
    keywords: ['混沌', '抽象', '发疯', '鬼畜派对', 'chaos', '离谱', '乱'],
    bpm: 178,
    mode: 'minor' as Mode,
    brightness: 0.6,
    density: 0.98,
    groove: 0.82,
    tension: 0.9,
    dynamics: 0.98,
    // 错拍、双踩、密集镲
    drums: K('x..x..x.x..x..x.', '..x...x...x...x.', '....x.......x...', 'xxxxxxxxxxxxxxxx', 'x...x...x...x...'),
    bass: 'rave' as never,
    keys: 'stab_wide' as never,
    lead: 'siren' as never,
    tags: ['混沌', '抽象', '高速', '失真'],
    sound: {
      kick: 'click',
      snare: 'crack',
      hat: 'loose',
      drive: 0.85,
      reverb: 0.26,
      delay: 0.38,
      chop: true,
      chopRate: 8,
      structure: 'rave',
      dropBars: 8,
      subHz: 45,
      kit: 'chaos',
    },
  },
];

/** 给引擎用：按风格 id 取音色画像（老风格返回 null，走原有分支） */
export function soundProfileOf(id: string): SoundProfile | null {
  const hit = EXTRA_GENRES.find((g) => g.id === id);
  return hit ? hit.sound : null;
}

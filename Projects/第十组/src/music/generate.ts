import type { BassStyle, DrumKit, GenreSpec, KeysStyle } from './genre';
import { genreForMood, genreFromStyle, matchGenre } from './genre';
import type { Chord, ChordEvent, Key, Mode, Note, Song, StyleProfile, Track } from './types';
import { SCALES, chordPitches, diatonicChords, voiceChord } from './theory';

/**
 * 本地符号生成引擎。
 *
 * 设计原则：生成 = 在「音乐上安全」的模板空间里做受约束的选择。
 * 不用随机音符堆砌，而是让和弦进行、律动、音区、旋律走向都在乐理约束内，
 * 这样任何时候生成出来的东西都不会难听——现场演示的底线。
 */

export interface MoodSpec {
  name: string;
  mode: Mode;
  tempo: number;
  brightness: number;
  density: number;
  groove: number;
  tension: number;
  dynamics: number;
  tags: string[];
  /** 命中的关键词 */
  matched?: string[];
}

const MOOD_LIBRARY: Array<{ keywords: string[]; mood: MoodSpec }> = [
  {
    keywords: ['夜', '深夜', '晚上', '月光', '霓虹', '凌晨', '星', '失眠', '下雨', '雨夜'],
    mood: {
      name: '深夜霓虹',
      mode: 'minor',
      tempo: 80,
      brightness: 0.34,
      density: 0.44,
      groove: 0.5,
      tension: 0.34,
      dynamics: 0.6,
      tags: ['lo-fi', '夜晚', '电钢琴'],
    },
  },
  {
    keywords: ['雨', '下雨', '潮湿', '窗', '水', '雾'],
    mood: {
      name: '窗边听雨',
      mode: 'minor',
      tempo: 72,
      brightness: 0.28,
      density: 0.32,
      groove: 0.36,
      tension: 0.3,
      dynamics: 0.42,
      tags: ['ambient', '安静', '雨声感'],
    },
  },
  {
    keywords: ['孤独', '寂寞', '一个人', '思念', '怀念', '告别', '失恋', '想念', '远方', '难过', '失落', '低落', '崩溃', '很差', '不好', 'emo', '丧'],
    mood: {
      name: '一个人的房间',
      mode: 'minor',
      tempo: 68,
      brightness: 0.24,
      density: 0.3,
      groove: 0.3,
      tension: 0.38,
      dynamics: 0.34,
      tags: ['抒情', '稀疏', '小调'],
    },
  },
  {
    keywords: ['开心', '快乐', '明亮', '阳光', '清晨', '春天', '甜', '温暖', '海'],
    mood: {
      name: '清晨的海',
      mode: 'major',
      tempo: 96,
      brightness: 0.72,
      density: 0.56,
      groove: 0.56,
      tension: 0.22,
      dynamics: 0.55,
      tags: ['明亮', '大调', '流行'],
    },
  },
  {
    keywords: ['热烈', '燃烧', '奔跑', '热血', '冲', '炸', '舞台'],
    mood: {
      name: '冲向舞台',
      mode: 'major',
      tempo: 124,
      brightness: 0.7,
      density: 0.82,
      groove: 0.82,
      tension: 0.44,
      dynamics: 0.86,
      tags: ['电子', '驱动', '四踩'],
    },
  },
  {
    keywords: ['未来', '科幻', '赛博', '城市', '机器', '代码', '数字', '宇宙'],
    mood: {
      name: '赛博清晨',
      mode: 'minor',
      tempo: 108,
      brightness: 0.55,
      density: 0.7,
      groove: 0.74,
      tension: 0.52,
      dynamics: 0.68,
      tags: ['synthwave', '合成器', '冷色'],
    },
  },
  {
    keywords: ['童年', '夏天', '旧', '老', '回忆', '放学', '自行车'],
    mood: {
      name: '回不去的夏天',
      mode: 'major',
      tempo: 88,
      brightness: 0.62,
      density: 0.46,
      groove: 0.48,
      tension: 0.34,
      dynamics: 0.52,
      tags: ['怀旧', '木质感', '大调'],
    },
  },
  {
    keywords: ['风', '自由', '远行', '山', '旅行', '路上', '公路'],
    mood: {
      name: '在公路上',
      mode: 'major',
      tempo: 104,
      brightness: 0.66,
      density: 0.56,
      groove: 0.62,
      tension: 0.3,
      dynamics: 0.6,
      tags: ['民谣感', '律动', '大调'],
    },
  },
  {
    keywords: ['毕业', '告别', '同学', '分开', '最后一', '再见'],
    mood: {
      name: '毕业那天',
      mode: 'minor',
      tempo: 76,
      brightness: 0.32,
      density: 0.36,
      groove: 0.34,
      tension: 0.4,
      dynamics: 0.5,
      tags: ['怀旧', '离别', '小调'],
    },
  },
  {
    keywords: ['加班', '工作', '办公室', '咖啡', '赶', 'ddl', 'DDL', '改代码', '熬', '深夜加班', '凌晨', '两点'],
    mood: {
      name: '凌晨的办公室',
      mode: 'minor',
      tempo: 92,
      brightness: 0.4,
      density: 0.5,
      groove: 0.56,
      tension: 0.34,
      dynamics: 0.52,
      tags: ['lo-fi', '疲惫', '城市'],
    },
  },
  {
    keywords: ['地铁', '通勤', '人群', '末班车', '车站', '街头'],
    mood: {
      name: '地铁末班车',
      mode: 'minor',
      tempo: 100,
      brightness: 0.42,
      density: 0.62,
      groove: 0.68,
      tension: 0.42,
      dynamics: 0.58,
      tags: ['都市', '律动', '小调'],
    },
  },
  {
    keywords: ['雪', '冬天', '白色', '冷', '冰'],
    mood: {
      name: '下雪那天',
      mode: 'major',
      tempo: 66,
      brightness: 0.56,
      density: 0.26,
      groove: 0.28,
      tension: 0.3,
      dynamics: 0.4,
      tags: ['安静', '冬天', '大调'],
    },
  },
  {
    keywords: ['喜欢', '心动', '恋爱', '婚礼', '爱你', '告白'],
    mood: {
      name: '心动的瞬间',
      mode: 'major',
      tempo: 100,
      brightness: 0.78,
      density: 0.6,
      groove: 0.62,
      tension: 0.2,
      dynamics: 0.62,
      tags: ['明亮', '甜', '大调'],
    },
  },
  {
    keywords: ['愤怒', '吵架', '失控', '压抑', '砸', '吼'],
    mood: {
      name: '失控',
      mode: 'minor',
      tempo: 132,
      brightness: 0.5,
      density: 0.85,
      groove: 0.86,
      tension: 0.66,
      dynamics: 0.82,
      tags: ['激烈', '压迫', '小调'],
    },
  },
];

const DEFAULT_MOOD = MOOD_LIBRARY[0].mood;

export function interpret(text: string): MoodSpec {
  const t = text.trim();
  let best: MoodSpec = DEFAULT_MOOD;
  let bestScore = 0;
  let bestHits: string[] = [];
  for (const entry of MOOD_LIBRARY) {
    let score = 0;
    const hits: string[] = [];
    for (const k of entry.keywords) {
      if (!t.includes(k)) continue;
      // 关键词越长越具体，权重越高："凌晨两点"应该压过"凌晨"
      score += k.length >= 2 ? Math.min(5, k.length) : 1;
      hits.push(k);
    }
    if (score > bestScore) {
      bestScore = score;
      best = entry.mood;
      // 去掉被更长关键词包含的短词（"深夜"命中时就不再单独显示"夜"）
      bestHits = hits.filter((h) => !hits.some((o) => o !== h && o.includes(h)));
    }
  }
  const mood: MoodSpec = { ...best, tags: [...best.tags], matched: bestHits };
  if (/[！!]|燃|冲|热烈/.test(t)) mood.tempo = Math.min(140, mood.tempo + 8);
  if (/安静|轻|慢|温柔|轻声|睡/.test(t)) mood.tempo = Math.max(58, mood.tempo - 6);
  if (/悲伤|难过|哭|失去|离开/.test(t)) {
    mood.mode = 'minor';
    mood.brightness = Math.min(mood.brightness, 0.26);
    mood.tension = Math.max(mood.tension, 0.42);
  }
  return mood;
}

/* ---------------- 可复现随机 ---------------- */

function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick<T>(arr: readonly T[], rng: () => number): T {
  return arr[Math.floor(rng() * arr.length) % arr.length];
}

/* ---------------- 和弦 ---------------- */

const TONICS_MINOR = [9, 2, 4, 11, 7];
const TONICS_MAJOR = [0, 7, 2, 5, 9];

/** 用级数表示的常见进行（0 = 主和弦） */
const MINOR_PROGRESSIONS: number[][] = [
  [0, 5, 2, 6], // i – VI – III – VII
  [0, 3, 5, 4], // i – iv – VI – V
  [0, 5, 3, 4], // i – VI – iv – V
  [0, 6, 5, 6], // i – VII – VI – VII
  [0, 2, 6, 3], // i – III – VII – iv
];

const MAJOR_PROGRESSIONS: number[][] = [
  [0, 4, 5, 3], // I – V – vi – IV
  [0, 5, 3, 4], // I – vi – IV – V
  [3, 0, 4, 5], // IV – I – V – vi
  [5, 3, 0, 4], // vi – IV – I – V
];

function withSeventh(chord: Chord): Chord {
  if (chord.quality === 'maj') return { ...chord, quality: 'maj7' };
  if (chord.quality === 'min') return { ...chord, quality: 'min7' };
  if (chord.quality === 'dim') return { ...chord, quality: 'm7b5' };
  return chord;
}

function buildChords(key: Key, mode: Mode, tension: number, bars: number, rng: () => number): ChordEvent[] {
  const prog = pick(mode === 'minor' ? MINOR_PROGRESSIONS : MAJOR_PROGRESSIONS, rng);
  const degrees: number[] = [];
  while (degrees.length < bars) degrees.push(...prog);
  const trimmed = degrees.slice(0, bars);
  // 最后一小节收在属和弦，形成回环的牵引
  trimmed[bars - 1] = 4;

  const diat = diatonicChords(key);
  return trimmed.map((deg, i) => {
    let chord: Chord = { ...diat[deg] };
    if (i === bars - 1) {
      chord = { root: diat[4].root, quality: 'dom7' };
    } else if (tension > 0.4) {
      chord = withSeventh(chord);
    }
    return { startBeat: i * 4, beats: 4, chord };
  });
}

/* ---------------- 节奏型 ---------------- */

function drumNotes(kit: DrumKit, bars: number, rng: () => number, fillBars: number[] = []): Note[] {
  const out: Note[] = [];
  for (let bar = 0; bar < bars; bar++) {
    const fill = bar === bars - 1 || fillBars.includes(bar);
    const base = bar * 4;
    const push = (pattern: string, pitch: number, vel: number, accent: number) => {
      const step = 4 / pattern.length;
      for (let i = 0; i < pattern.length; i++) {
        if (pattern[i] !== 'x') continue;
        // 重拍重、弱拍轻，这是鼓点"活"起来的根本
        const metrical = i % 4 === 0 ? 1 : i % 2 === 0 ? accent : accent * 0.66;
        out.push({
          pitch,
          start: base + i * step,
          dur: step * 0.9,
          vel: Math.min(1, vel * metrical * (0.92 + rng() * 0.16)),
        });
      }
    };
    push(fill ? 'x.......x.x.x...' : kit.kick, 36, 0.95, 0.86);
    push(kit.snare, 38, 0.8, 0.9);
    push(kit.clap, 39, 0.72, 0.92);
    push(kit.hat, 42, 0.52, 0.68);
    push(kit.open, 46, 0.4, 0.9);
  }
  return out;
}

/* ---------------- 贝斯 ---------------- */

function genreBass(style: BassStyle, chords: ChordEvent[], rng: () => number): Note[] {
  const out: Note[] = [];
  chords.forEach((ev, bar) => {
    const root = 36 + ev.chord.root;
    const base = bar * 4;
    if (style === 'sub') {
      // house：反拍 8 分低音，短促、只负责低频
      for (const off of [0.5, 1.5, 2.5, 3.5]) {
        out.push({ pitch: root, start: base + off, dur: 0.36, vel: 0.86 });
      }
    } else if (style === 'acid') {
      // techno：16 分滚动，偶尔跳八度
      for (let i = 0; i < 16; i++) {
        out.push({
          pitch: root + (rng() < 0.16 ? 12 : 0),
          start: base + i * 0.25,
          dur: 0.2,
          vel: i % 4 === 0 ? 0.92 : 0.64,
        });
      }
    } else if (style === 'reese') {
      // dnb：长音 reese，两拍一个
      out.push({ pitch: root, start: base, dur: 1.85, vel: 0.8 });
      out.push({ pitch: root, start: base + 2, dur: 1.85, vel: 0.72 });
    } else if (style === 'e808') {
      // trap：低八度长音，后半拍滑上去
      out.push({ pitch: root - 12, start: base, dur: 2.2, vel: 0.92 });
      if (rng() < 0.55) out.push({ pitch: root, start: base + 2.5, dur: 1.3, vel: 0.7 });
    } else {
      // electropop / rock：8 分推进
      for (let i = 0; i < 8; i++) {
        out.push({
          pitch: root,
          start: base + i * 0.5,
          dur: 0.22,
          vel: i % 2 === 0 ? 0.82 : 0.6,
        });
      }
    }
  });
  return out;
}

/* ---------------- 和声织体 ---------------- */

function genreKeys(style: KeysStyle, chords: ChordEvent[], rng: () => number): Note[] {
  const out: Note[] = [];
  let prev: number[] | null = null;
  for (const ev of chords) {
    const voicing = voiceChord(ev.chord, prev);
    prev = voicing;
    const base = ev.startBeat;

    if (style === 'stab') {
      // 反拍和弦刺：一响就收，这是 house 的味道
      for (const off of [0.5, 1.5, 2.5, 3.5]) {
        if (rng() < 0.18) continue;
        for (const p of voicing) out.push({ pitch: p, start: base + off, dur: 0.16, vel: 0.4 });
      }
    } else if (style === 'supersaw') {
      // synthwave：整小节宽和弦
      for (const p of voicing) out.push({ pitch: p, start: base, dur: 3.8, vel: 0.4 });
    } else {
      // pluck / trap：8 分拨弦琶音
      const arp = [
        voicing[0],
        voicing[1],
        voicing[2],
        voicing[1],
        voicing[2],
        voicing[0] + 12,
        voicing[2],
        voicing[1],
      ];
      arp.forEach((p, i) => out.push({ pitch: p, start: base + i * 0.5, dur: 0.2, vel: 0.42 }));
    }
  }
  return out;
}

/* ---------------- 旋律 ---------------- */

/** 旋律节奏模板：带切分、带留白，避免每小节套同一个节奏型 */
const LEAD_RHYTHMS: Array<Array<[number, number]>> = [
  [[0, 1], [1, 0.5], [1.5, 1], [2.5, 1.5]],
  [[0, 0.75], [0.75, 0.75], [2, 1], [3, 0.5]],
  [[0, 1.5], [2, 0.5], [2.5, 0.5], [3, 0.75]],
  [[0, 0.5], [1.5, 1], [2.5, 1.5]],
  [[0, 2], [2.5, 1]],
  [[0, 0.5], [0.5, 0.5], [1, 1], [2.5, 0.5], [3, 0.5]],
  [[0, 1], [1, 1], [2, 0.5], [2.5, 0.5], [3, 1]],
  [[0, 1.25], [1.25, 0.75], [2, 0.5], [2.5, 1.5]],
];

function nearest(pool: number[], target: number): number {
  let best = pool[0];
  let bestD = Infinity;
  for (const p of pool) {
    const d = Math.abs(p - target);
    if (d < bestD) {
      bestD = d;
      best = p;
    }
  }
  return best;
}

interface MotifNote {
  /** 相对动机起点的音级偏移 */
  step: number;
  onset: number;
  dur: number;
}

const MOTIF_TRANSFORMS = ['none', 'sequence', 'inversion', 'rhythm'] as const;
type MotifTransform = (typeof MOTIF_TRANSFORMS)[number];

/** 生成两小节的动机：级进为主，跳进后反向级进，音域收在一个八度内 */
function buildMotif(rng: () => number, density: number): MotifNote[] {
  const pool = density > 0.62 ? LEAD_RHYTHMS : LEAD_RHYTHMS.slice(0, 5);
  const first = pool[Math.floor(rng() * pool.length)];
  const second = pool[Math.floor(rng() * pool.length)];
  const rhythm: Array<[number, number]> = [
    ...first,
    ...second.map(([o, d]) => [o + 4, d] as [number, number]),
  ];

  const notes: MotifNote[] = [];
  let off = 0;
  let lastStep = 0;
  const half = Math.ceil(rhythm.length / 2);

  for (let i = 0; i < rhythm.length; i++) {
    const [onset, dur] = rhythm[i];
    let step: number;
    if (i === 0) {
      step = 1 + Math.floor(rng() * 2);
    } else if (Math.abs(lastStep) >= 3) {
      step = lastStep > 0 ? -1 : 1;
    } else {
      const r = rng();
      if (r < 0.55) step = rng() < 0.5 ? 1 : -1;
      else if (r < 0.75) step = rng() < 0.5 ? 2 : -2;
      else if (r < 0.83) step = 0;
      else step = rng() < 0.5 ? 3 : -3;
    }
    // 动机后半回落，形成一个小拱形
    if (i >= half && step > 0 && rng() < 0.55) step = -step;
    off = Math.max(-6, Math.min(7, off + step));
    lastStep = step;
    notes.push({ step: off, onset, dur });
  }
  return notes;
}

function transformMotif(motif: MotifNote[], kind: MotifTransform): MotifNote[] {
  if (kind === 'sequence') return motif.map((n) => ({ ...n, step: n.step + 1 }));
  if (kind === 'inversion') return motif.map((n) => ({ ...n, step: 1 - n.step }));
  if (kind === 'rhythm') {
    return motif.map((n, i) =>
      i === 1 ? { ...n, onset: n.onset + 0.25, dur: Math.max(0.25, n.dur - 0.25) } : n,
    );
  }
  return motif.slice();
}

/**
 * 旋律 = 动机 + 变奏。
 * 先立一个两小节的动机，下一句用移调 / 倒影 / 改节奏来回应。
 * 这是"听起来像有人写的"和"听起来像随机点"的分界线。
 */
function generateLead(
  chords: ChordEvent[],
  key: Key,
  rng: () => number,
  density: number,
  fromBar: number,
  toBar: number,
): Note[] {
  const scaleSel = SCALES[key.mode];
  const scale: number[] = [];
  for (let p = 60; p <= 86; p++) {
    if (scaleSel.includes((p - key.tonic + 120) % 12)) scale.push(p);
  }
  if (scale.length === 0) return [];

  const motif = buildMotif(rng, density);
  const anchor = Math.max(0, scale.indexOf(nearest(scale, 69)));
  const out: Note[] = [];
  const phrases = Math.max(1, Math.ceil((toBar - fromBar) / 2));

  for (let p = 0; p < phrases; p++) {
    const startBar = fromBar + p * 2;
    let shape = transformMotif(motif, MOTIF_TRANSFORMS[p % MOTIF_TRANSFORMS.length]);

    // 第二句：在移调之外再挪一个音的拍子，避免两句像复制粘贴
    if (p % 2 === 1 && shape.length > 1) {
      const shifted = Math.min(7, shape[1].onset + 0.5);
      const nextOnset = shape[2]?.onset;
      // 挪完后不能和后面的音撞在同一拍上，否则两个音会一起响
      if (nextOnset === undefined || Math.abs(nextOnset - shifted) > 0.01) {
        shape = shape.slice();
        shape[1] = { ...shape[1], onset: shifted };
      }
    }

    const local: Note[] = [];
    shape.forEach((n, i) => {
      const bar = startBar + Math.floor(n.onset / 4);
      if (bar >= toBar) return;
      const beat = n.onset % 4;
      const downbeat = beat === 0;
      const idx = Math.max(0, Math.min(scale.length - 1, anchor + n.step));
      let pitch = scale[idx];

      // 只在小节强拍上吸附和弦音，且距离必须很近——
      // 吸得太狠会把动机的轮廓磨平，听起来就不像"同一个动机"了
      if (downbeat) {
        const tones = chordPitches(chords[bar].chord, 4, 0)
          .flatMap((c) => [c - 12, c, c + 12])
          .filter((c) => c >= 60 && c <= 88);
        const snap = nearest(tones, pitch);
        if (Math.abs(snap - pitch) <= 2) pitch = snap;
      }

      // 最后一句的最后一个音收长一点；其余缩到 78%，让音与音之间有缝
      const isLast = p === phrases - 1 && i === shape.length - 1;
      const dur = isLast ? Math.max(n.dur, 1.5) : Math.max(0.2, n.dur * 0.78);

      local.push({
        pitch: Math.max(60, Math.min(88, pitch)),
        start: bar * 4 + beat,
        dur,
        vel: Math.min(1, (beat === 0 || beat === 2 ? 0.6 : 0.47) + rng() * 0.12),
      });
    });

    // 句内不许叠音：后一个音响起时，前一个必须已经放开
    local.sort((a, b) => a.start - b.start);
    for (let i = local.length - 1; i > 0; i--) {
      if (local[i].start - local[i - 1].start < 0.06) local.splice(i, 1);
    }
    for (let i = 0; i < local.length - 1; i++) {
      const limit = local[i + 1].start - local[i].start - 0.04;
      if (local[i].dur > limit) local[i].dur = Math.max(0.15, limit);
    }
    // 句尾也不能拖进下一句
    if (p < phrases - 1 && local.length > 0) {
      const phraseEnd = (startBar + 2) * 4;
      const tail = local[local.length - 1];
      tail.dur = Math.max(0.15, Math.min(tail.dur, phraseEnd - tail.start - 0.06));
    }

    out.push(...local);
  }
  return out;
}

/* ---------------- 组装 ---------------- */

/** 根据风格画像选择鼓组音色取向 */
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
  id: string,
  name: string,
  kind: Track['kind'],
  gain: number,
  notes: Note[],
  preset?: string,
): Track {
  return {
    id,
    name,
    kind,
    preset,
    gain,
    mute: false,
    locked: false,
    clips: [{ id: `${id}-clip`, startBeat: 0, notes }],
  };
}

export interface Brief {
  mood: MoodSpec;
  genre: GenreSpec;
  tempo: number;
  /** 用户是否明确点名了流派 */
  explicit?: boolean;
}

function composeFromBrief(brief: Brief, bars: number, seedStr: string, tonic?: number): Song {
  const { mood, genre, tempo } = brief;
  const rng = mulberry32(hashString(seedStr));
  const tonics = mood.mode === 'minor' ? TONICS_MINOR : TONICS_MAJOR;
  const key: Key = { tonic: tonic ?? pick(tonics, rng), mode: mood.mode };
  const chords = buildChords(key, mood.mode, Math.max(mood.tension, genre.tension), bars, rng);

  // 电子乐不搞前奏留白：第一小节就要有律动。只在副歌前放一个过门。
  const q = Math.max(1, Math.floor(bars / 4));
  const leadFrom = q * 2;

  const tracks: Track[] = [
    track('t-drums', '鼓组', 'drums', 0.82, drumNotes(genre.drums, bars, rng, [leadFrom - 1]), drumPresetFor(genre)),
    track('t-bass', '贝斯', 'bass', 0.78, genreBass(genre.bass, chords, rng), genre.bass),
    track('t-keys', '和声', 'keys', 0.66, genreKeys(genre.keys, chords, rng), genre.keys),
  ];

  const lead = generateLead(chords, key, rng, genre.density, leadFrom, bars);
  if (lead.length > 0) {
    tracks.push(track('t-lead', '主旋律', 'lead', 0.6, lead, genre.lead));
  }

  // 人声切片轨：司凤 / 鬼畜 / Hyperpop 的"记忆点"来源。
  // 用共振峰合成发 /a/ /e/ 元音，按 16 或 32 分音符切，形成节奏化的"邦吧邦吧"。
  if (genre.sound?.chop) {
    const chops = generateChops(chords, bars, rng, leadFrom);
    if (chops.length > 0) {
      tracks.push(track('t-chop', '人声切片', 'lead', 0.62, chops, 'a'));
    }
  }

  const style: StyleProfile = {
    name: brief.explicit ? genre.name : mood.name,
    brightness: genre.brightness,
    density: genre.density,
    groove: genre.groove,
    tension: Math.max(mood.tension, genre.tension),
    dynamics: genre.dynamics,
    bpm: tempo,
    tags: [
      genre.name,
      ...genre.tags.filter((t) => t.toLowerCase() !== genre.name.toLowerCase()),
    ],
  };

  return {
    id: `gen-${hashString(seedStr)}`,
    title: brief.explicit ? genre.name : mood.name,
    tempo,
    meter: 4,
    bars,
    key,
    sections: [
      {
        id: 's1',
        name: '主歌',
        startBar: 0,
        bars: Math.ceil(bars / 2),
        energy: Math.max(0.2, genre.dynamics - 0.3),
      },
      {
        id: 's2',
        name: '副歌',
        startBar: Math.ceil(bars / 2),
        bars: Math.floor(bars / 2),
        energy: Math.min(1, genre.dynamics + 0.15),
      },
    ],
    chords,
    tracks,
    style,
    // trap 的踩镲带一点摇摆，dnb 必须直
    swing: genre.id === 'trap' ? 0.12 : genre.id === 'dnb' ? 0.02 : 0.06,
    matched: mood.matched,
    genre: genre.name,
    soundKit: genre.sound?.kit,
  };
}

export function interpretBrief(text: string): Brief {
  const mood = interpret(text);
  const explicit = matchGenre(text);
  const genre = explicit ?? genreForMood(mood.name);
  // 点名了流派就用流派速度；只说情绪则让情绪和流派各占一半
  let tempo = explicit ? genre.bpm : Math.round((genre.bpm + mood.tempo) / 2);
  const t = text.trim();
  if (!explicit) {
    if (/[！!]|燃|冲|热烈/.test(t)) tempo += 6;
    if (/安静|轻|慢|温柔|睡/.test(t)) tempo -= 5;
  }
  tempo = Math.max(60, Math.min(180, tempo));
  return { mood, genre, tempo, explicit: !!explicit };
}

export function composeSong(text: string, bars = 8, salt = ''): Song {
  return composeFromBrief(interpretBrief(text), bars, text + salt);
}

/**
 * 带显式覆盖的生成入口：Producer 解析出的 BPM / 小节数 / 标题直接生效。
 * 仍然走同一套受约束生成，不改乐理规则。
 */
export function composeSongEx(
  text: string,
  opts: {
    bars?: number;
    tempo?: number;
    salt?: string;
    title?: string;
    /** 显式指定风格：UI 里锁定的风格必须真的生效，不能被文本重新推断覆盖 */
    genre?: GenreSpec;
  } = {},
): Song {
  const brief = interpretBrief(text);
  const genre = opts.genre ?? brief.genre;
  const tempo = Math.max(60, Math.min(190, Math.round(opts.tempo ?? (opts.genre ? genre.bpm : brief.tempo))));
  const song = composeFromBrief({ ...brief, genre, tempo }, opts.bars ?? 8, text + (opts.salt ?? ''));
  return opts.title ? { ...song, title: opts.title } : song;
}

/** 用参考曲目提取出的风格参数生成 */
export function composeFromStyle(style: StyleProfile, detectedKey?: Key, salt = ''): Song {
  const genre = genreFromStyle(style.bpm, style.brightness, style.groove);
  const mood: MoodSpec = {
    name: style.name,
    mode: detectedKey?.mode ?? genre.mode,
    tempo: style.bpm,
    brightness: style.brightness,
    density: style.density,
    groove: style.groove,
    tension: style.tension,
    dynamics: style.dynamics,
    tags: [...style.tags],
  };
  return composeFromBrief(
    { mood, genre, tempo: style.bpm },
    8,
    `${style.name}|${style.bpm}|${salt}`,
    detectedKey?.tonic,
  );
}

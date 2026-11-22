import type { GenreId, GenreSpec } from '../music/genre';
import { GENRES, genreForMood, matchGenre } from '../music/genre';
import { interpret } from '../music/generate';
import { NOTE_NAMES } from '../music/theory';
import type { Mode } from '../music/types';

/**
 * AI Producer 的自然语言解析层。
 *
 * 这里不是「假装 LLM」：没有模型可用时，用一组确定性规则把中文描述拆成
 * 可解释的制作参数（流派 / 调式 / BPM / 小节数 / 密度 / 能量 / 音色提示）。
 * 每一条规则命中都会写进 reasoning，界面上原样展示，用户能看到"为什么是这首歌"。
 *
 * 如果以后接上真 LLM，只需要换掉 parsePrompt 的实现，
 * 返回同一个 ParsedIntent 结构即可，下游全部不用改。
 */

export interface ParsedIntent {
  prompt: string;
  genre: GenreSpec;
  genreExplicit: boolean;
  moodName: string;
  mode: Mode;
  /** 调式主音（0-11），用于界面展示真实调性 */
  keyTonic: number;
  /** 最终 BPM（可能来自用户显式指定，或流派/情绪推断） */
  bpm: number;
  bpmExplicit: boolean;
  /** 小节数（4/4，每小节 4 拍） */
  bars: number;
  barsExplicit: boolean;
  durationSec: number;
  /** 0-1，编曲疏密 */
  density: number;
  /** 0-1，情绪强度 */
  energy: number;
  brightness: number;
  swing: number;
  tags: string[];
  matched: string[];
  /** 0-1，解析自信度：显式信息越多越高 */
  confidence: number;
  /** 给人看的推断说明 */
  reasoning: string[];
  intent: 'compose' | 'meme';
  /** 写进歌曲标题的建议 */
  title: string;
}

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

/** 中文/英文里表达"更猛"的词 */
const HOT = /燃|炸|猛|高能|激烈|冲|燥|狂热|hard|energy|硬核|嗨|蹦迪|rave/i;
/** 表达"更轻"的词 */
const SOFT = /安静|温柔|轻声|轻|舒缓|治愈|慢|眠|chill|soft|氛围|ambient/i;

/** 乐句长度提示：短一点 / 长一点 */
const SHORT = /短|简短|几个小节|demo|片段/i;
const LONG = /长|完整|整首|一分|两分|三分钟/i;

function parseBpm(text: string): { bpm: number | null; raw: string | null } {
  // 130bpm / 130 BPM / 130拍 / 速度 130 / bpm 130
  const patterns = [
    /(\d{2,3})\s*(?:bpm|BPM|拍(?:\s*每分钟)?)/,
    /(?:bpm|BPM|速度|tempo)\s*[:：=]?\s*(\d{2,3})/,
    /(\d{2,3})\s*迈/,
  ];
  for (const re of patterns) {
    const m = re.exec(text);
    if (!m) continue;
    const v = parseInt(m[1], 10);
    if (v >= 50 && v <= 220) return { bpm: v, raw: m[0] };
  }
  return { bpm: null, raw: null };
}

function parseBars(text: string): { bars: number | null; raw: string | null } {
  const mBars = /(\d{1,2})\s*(?:个)?\s*小节/.exec(text);
  if (mBars) {
    const v = parseInt(mBars[1], 10);
    if (v >= 2 && v <= 64) return { bars: v, raw: mBars[0] };
  }
  const mSec = /(\d{1,3}(?:\.\d+)?)\s*(?:秒|s\b|sec)/i.exec(text);
  const mMin = /(\d{1,2}(?:\.\d+)?)\s*(?:分钟|min\b)/i.exec(text);
  let sec: number | null = null;
  if (mMin) sec = parseFloat(mMin[1]) * 60;
  else if (mSec) sec = parseFloat(mSec[1]);
  if (sec !== null && sec >= 4 && sec <= 600) {
    // 具体小节数要等 BPM 定了才算，这里先记下秒数，用 -1 占位
    return { bars: -Math.round(sec), raw: mMin ? mMin[0] : mSec ? mSec[0] : null };
  }
  return { bars: null, raw: null };
}

function parseKey(text: string): { tonic: number; mode: Mode } | null {
  // C大调 / #F小调 / Ab minor / F#m
  const m = /([A-Ga-g])([#♯b♭]?)\s*(大调|小调|major|minor|m\b)/.exec(text);
  if (!m) return null;
  const base: Record<string, number> = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  const letter = m[1].toUpperCase();
  const acc = m[2] === '#' || m[2] === '♯' ? 1 : m[2] === 'b' || m[2] === '♭' ? -1 : 0;
  const mode: Mode = /大调|major/.test(m[3]) ? 'major' : 'minor';
  return { tonic: ((base[letter] ?? 0) + acc + 12) % 12, mode };
}

function parseInstrumentHints(text: string): string[] {
  const hints: string[] = [];
  if (/钢琴|keys|和弦|piano/i.test(text)) hints.push('和声层加厚');
  if (/贝斯|bass|低音/i.test(text)) hints.push('贝斯推进');
  if (/鼓|drum|节奏/i.test(text)) hints.push('鼓组驱动');
  if (/主音|旋律|lead|solo/i.test(text)) hints.push('主旋律突出');
  return hints;
}

/**
 * 主解析入口。
 * @param text 用户随便写的一句话
 */
export function parsePrompt(text: string): ParsedIntent {
  const prompt = text.trim();
  const reasoning: string[] = [];

  const mood = interpret(prompt);
  const explicitGenre = matchGenre(prompt);
  const genre = explicitGenre ?? genreForMood(mood.name);

  if (explicitGenre) {
    reasoning.push(`命中流派关键词「${explicitGenre.name}」→ 采用它的编制与鼓型`);
  } else {
    reasoning.push(`没点名流派，按情绪「${mood.name}」推断为 ${genre.name}`);
  }

  const keyHit = parseKey(prompt);
  const mode: Mode = keyHit?.mode ?? mood.mode;
  // 用户没点调性时，小调按 A 小调、大调按 C 大调展示（电子乐最常见的两个中性选择）
  const keyTonic = keyHit?.tonic ?? (mode === 'major' ? 0 : 9);

  const bpmHit = parseBpm(prompt);
  let bpm = bpmHit.bpm ?? (explicitGenre ? genre.bpm : Math.round((genre.bpm + mood.tempo) / 2));
  if (bpmHit.bpm === null) {
    if (HOT.test(prompt)) bpm += 6;
    if (SOFT.test(prompt)) bpm -= 6;
    reasoning.push(`BPM 由${explicitGenre ? '流派基准' : '流派与情绪折中'}推算为 ${bpm}`);
  } else {
    reasoning.push(`你指定了速度 ${bpmHit.bpm} BPM`);
  }
  bpm = clamp(Math.round(bpm), 60, 190);

  const barsHit = parseBars(prompt);
  let bars: number;
  if (barsHit.bars === null) {
    bars = 16;
    reasoning.push('默认 16 小节：足够走完「前奏 → 铺陈 → Drop → Break → 二次 Drop」');
  } else if (barsHit.bars < 0) {
    // 负数存的是秒数
    const sec = -barsHit.bars;
    bars = clamp(Math.round((sec * bpm) / 60 / 4), 2, 64);
    reasoning.push(`按时长 ${sec} 秒、${bpm} BPM 折算成 ${bars} 小节`);
  } else {
    bars = barsHit.bars;
    reasoning.push(`你指定了长度 ${bars} 小节`);
  }
  if (!barsHit.bars && SHORT.test(prompt)) {
    bars = Math.min(bars, 8);
    reasoning.push('描述里提到「短」，压到 8 小节');
  } else if (!barsHit.bars && LONG.test(prompt)) {
    bars = Math.max(bars, 24);
    reasoning.push('描述里提到「完整/长」，拉到 24 小节');
  }

  // 能量与密度：情绪基础值 + 关键词修正
  let energyBase = clamp((genre.dynamics + (1 - mood.brightness) * 0.4 + mood.tension * 0.4) / 2 + 0.15, 0.2, 1);
  if (HOT.test(prompt)) {
    energyBase = clamp(energyBase + 0.18, 0, 1);
    reasoning.push('检测到「燃/炸/嗨」一类词 → 能量上调');
  }
  if (SOFT.test(prompt)) {
    energyBase = clamp(energyBase - 0.2, 0, 1);
    reasoning.push('检测到「安静/温柔」一类词 → 能量下调');
  }
  const density = clamp(genre.density * 0.75 + energyBase * 0.35, 0.2, 1);

  const tags = Array.from(
    new Set([
      genre.name,
      ...genre.tags,
      ...(explicitGenre ? [] : [mood.name]),
      ...parseInstrumentHints(prompt),
      ...(HOT.test(prompt) ? ['高能'] : []),
      ...(SOFT.test(prompt) ? ['柔和'] : []),
    ]),
  );

  // 置信度：显式信号越多越可信
  let signals = 0;
  if (explicitGenre) signals += 2;
  if (bpmHit.bpm !== null) signals += 1;
  if (barsHit.bars !== null) signals += 1;
  if (keyHit) signals += 1;
  if (mood.matched && mood.matched.length > 0) signals += 1;
  if (prompt.length > 8) signals += 1;
  const confidence = clamp(0.35 + signals * 0.11, 0.35, 0.97);

  const title =
    explicitGenre && prompt.length > 24
      ? `${explicitGenre.name} · ${mood.name}`
      : mood.name || genre.name;

  return {
    prompt,
    genre,
    genreExplicit: !!explicitGenre,
    moodName: mood.name,
    mode,
    keyTonic,
    bpm,
    bpmExplicit: bpmHit.bpm !== null,
    bars,
    barsExplicit: barsHit.bars !== null,
    durationSec: Math.round((bars * 4 * 60) / bpm),
    density,
    energy: energyBase,
    brightness: clamp(mood.brightness * 0.6 + genre.brightness * 0.4, 0, 1),
    swing: genre.id === 'trap' ? 0.12 : genre.id === 'dnb' ? 0.02 : 0.06,
    tags,
    matched: [...(mood.matched ?? []), ...(explicitGenre ? [explicitGenre.name] : [])],
    confidence,
    reasoning,
    intent: /梗|meme|整活|鬼畜|抽象|爆改/i.test(prompt) ? 'meme' : 'compose',
    title,
  };
}

/** 风格下拉选项：内置流派 + 自动 */
export const STYLE_OPTIONS: Array<{ id: GenreId | 'auto'; label: string; hint: string }> = [
  { id: 'auto', label: '自动推断', hint: '让解析器按描述决定' },
  ...GENRES.map((g) => ({
    id: g.id,
    label: g.name,
    hint: `${g.bpm} BPM 基准 · ${g.tags.slice(0, 2).join(' / ')}`,
  })),
];

/** 情绪选择：不是标签装饰，选中的情绪词会真的拼进解析文本，影响调式、速度、密度 */
export const MOOD_OPTIONS: Array<{ id: string; label: string; keywords: string }> = [
  { id: 'auto', label: '自动（由描述判断）', keywords: '' },
  { id: 'night', label: '深夜霓虹', keywords: '深夜 霓虹 一个人 失眠' },
  { id: 'rain', label: '窗边听雨', keywords: '下雨 窗 潮湿 安静' },
  { id: 'alone', label: '孤独 / emo', keywords: '孤独 寂寞 难过 失落' },
  { id: 'bright', label: '明亮 / 开心', keywords: '开心 明亮 阳光 温暖' },
  { id: 'hype', label: '燃 / 冲', keywords: '燃 冲 炸 舞台 高能' },
  { id: 'cyber', label: '赛博 / 未来', keywords: '赛博 未来 机器 城市 代码' },
  { id: 'memory', label: '怀旧 / 夏天', keywords: '童年 夏天 回忆 旧' },
  { id: 'road', label: '公路 / 自由', keywords: '公路 旅行 风 自由' },
  { id: 'office', label: '加班 / 疲惫', keywords: '加班 办公室 凌晨 咖啡' },
  { id: 'snow', label: '雪 / 冷', keywords: '雪 冬天 冷 冰' },
  { id: 'anger', label: '愤怒 / 失控', keywords: '愤怒 压抑 失控 砸' },
];

/** 把下拉选择覆盖到解析结果上 */
export function applyOverrides(
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

/** 给界面用的 key 展示 */
export function keyName(tonic: number, mode: Mode): string {
  return `${NOTE_NAMES[((tonic % 12) + 12) % 12]} ${mode === 'major' ? '大调' : '小调'}`;
}

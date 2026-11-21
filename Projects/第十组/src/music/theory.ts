import type { Chord, ChordQuality, Key, Mode } from './types';

export const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

/** 和弦性质 → 相对根音的半音音程 */
export const QUALITY_INTERVALS: Record<ChordQuality, number[]> = {
  maj: [0, 4, 7],
  min: [0, 3, 7],
  dim: [0, 3, 6],
  aug: [0, 4, 8],
  maj7: [0, 4, 7, 11],
  min7: [0, 3, 7, 10],
  dom7: [0, 4, 7, 10],
  m7b5: [0, 3, 6, 10],
  dim7: [0, 3, 6, 9],
  sus2: [0, 2, 7],
  sus4: [0, 5, 7],
  add9: [0, 4, 7, 14],
  six: [0, 4, 7, 9],
  min9: [0, 3, 7, 10, 14],
  maj9: [0, 4, 7, 11, 14],
};

export const QUALITY_SUFFIX: Record<ChordQuality, string> = {
  maj: '',
  min: 'm',
  dim: 'dim',
  aug: 'aug',
  maj7: 'maj7',
  min7: 'm7',
  dom7: '7',
  m7b5: 'm7b5',
  dim7: 'dim7',
  sus2: 'sus2',
  sus4: 'sus4',
  add9: 'add9',
  six: '6',
  min9: 'm9',
  maj9: 'maj9',
};

export function chordLabel(c: Chord): string {
  return NOTE_NAMES[c.root] + QUALITY_SUFFIX[c.quality];
}

/** 和声密度更高的性质，用于展示 */
export function isSeventh(c: Chord): boolean {
  return QUALITY_INTERVALS[c.quality].length >= 4;
}

/**
 * 把和弦展开成具体 MIDI 音高。
 * baseOctave = 4 表示根音落在第 4 八度（MIDI 60-71）。
 */
export function chordPitches(c: Chord, baseOctave = 4, inversion = 0): number[] {
  const root = 12 * (baseOctave + 1) + c.root;
  const pitches = QUALITY_INTERVALS[c.quality].map((i) => root + i);
  const inv = ((inversion % pitches.length) + pitches.length) % pitches.length;
  for (let k = 0; k < inv; k++) {
    const moved = pitches.shift()! + 12;
    pitches.push(moved);
  }
  return pitches;
}

function avg(xs: number[]): number {
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

/**
 * 给和弦选一个排列，使它离上一个和弦的排列最近。
 * 这一步能把「和弦忽高忽低」的业余感消掉一大半。
 */
export function voiceChord(c: Chord, prev: number[] | null, low = 52, high = 79): number[] {
  let best = chordPitches(c, 4, 0);
  let bestCost = Infinity;
  const target = prev ? avg(prev) : 64;
  for (let inv = 0; inv < 4; inv++) {
    for (let oct = 3; oct <= 5; oct++) {
      const p = chordPitches(c, oct, inv);
      if (p[0] < low || p[p.length - 1] > high) continue;
      const cost = Math.abs(avg(p) - target);
      if (cost < bestCost) {
        bestCost = cost;
        best = p;
      }
    }
  }
  return best;
}

export const SCALES: Record<Mode, number[]> = {
  major: [0, 2, 4, 5, 7, 9, 11],
  minor: [0, 2, 3, 5, 7, 8, 10],
};

export const DIATONIC_QUALITIES: Record<Mode, ChordQuality[]> = {
  major: ['maj', 'min', 'min', 'maj', 'maj', 'min', 'dim'],
  minor: ['min', 'dim', 'maj', 'min', 'min', 'maj', 'maj'],
};

export const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII'];

export function diatonicChords(key: Key): Chord[] {
  const scale = SCALES[key.mode];
  const qualities = DIATONIC_QUALITIES[key.mode];
  return scale.map((deg, i) => ({
    root: (key.tonic + deg) % 12,
    quality: qualities[i],
  }));
}

/** 判断和弦是否属于当前调的自然音级 */
export function degreeOf(c: Chord, key: Key): number {
  const scale = SCALES[key.mode];
  const idx = scale.findIndex((d) => (key.tonic + d) % 12 === c.root);
  return idx;
}

export function romanNumeral(c: Chord, key: Key): string {
  const idx = degreeOf(c, key);
  if (idx < 0) {
    // 借用和弦：用相对音级 + 升降号近似表示
    const rel = (c.root - key.tonic + 12) % 12;
    return (rel === 6 ? '♭VII' : rel === 8 ? '♭III' : '?') + QUALITY_SUFFIX[c.quality];
  }
  const base = ROMAN[idx];
  const minor = c.quality === 'min' || c.quality === 'min7' || c.quality === 'm7b5' || c.quality === 'min9';
  const numeral = minor ? base.toLowerCase() : base;
  return numeral + (isSeventh(c) ? '7' : '');
}

export function keyLabel(key: Key): string {
  return `${NOTE_NAMES[key.tonic]} ${key.mode === 'major' ? '大调' : '小调'}`;
}

/** 和弦的最低位音（用于贝斯） */
export function bassPitch(c: Chord, octave = 2): number {
  return 12 * (octave + 1) + c.root;
}

/** 音名 → MIDI，方便手写谱例：如 'A4' */
export function noteToMidi(name: string): number {
  const m = /^([A-G])([#b]?)(-?\d)$/.exec(name);
  if (!m) throw new Error(`无法解析音名: ${name}`);
  const base: Record<string, number> = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  const acc = m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0;
  const octave = parseInt(m[3], 10);
  return base[m[1]] + acc + (octave + 1) * 12;
}

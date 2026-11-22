import type { Chord, Clip, Key, Note, Song, Track } from './types';
import { bassPitch, voiceChord } from './theory';

const BARS = 8;
const BEATS_PER_BAR = 4;

const KEY: Key = { tonic: 9, mode: 'minor' }; // A 小调

/** i7 - VI - III - VII - i7 - VI - ii7 - V7：安全、耐听、有终上的小调进行 */
const PROGRESSION: Chord[] = [
  { root: 9, quality: 'min7' },
  { root: 5, quality: 'maj7' },
  { root: 0, quality: 'maj7' },
  { root: 7, quality: 'maj' },
  { root: 9, quality: 'min7' },
  { root: 5, quality: 'maj7' },
  { root: 2, quality: 'min7' },
  { root: 4, quality: 'dom7' },
];

/** [小节, 小节内第几拍, 时值, MIDI 音高] */
const MELODY: Array<[number, number, number, number]> = [
  [0, 0, 1.5, 76], [0, 1.5, 0.5, 72], [0, 2, 1, 74], [0, 3, 1, 76],
  [1, 0, 1, 72], [1, 1, 1, 69], [1, 2, 1.5, 72], [1, 3.5, 0.5, 74],
  [2, 0, 1, 76], [2, 1, 1, 74], [2, 2, 2, 72],
  [3, 0, 1.5, 71], [3, 1.5, 0.5, 74], [3, 2, 1, 71], [3, 3, 1, 67],
  [4, 0, 2, 69], [4, 2, 1, 72], [4, 3, 1, 76],
  [5, 0, 1, 69], [5, 1, 1, 72], [5, 2, 2, 76],
  [6, 0, 1, 74], [6, 1, 1, 77], [6, 2, 1, 72], [6, 3, 1, 69],
  [7, 0, 1, 71], [7, 1, 1, 68], [7, 2, 2, 71],
];

let clipSeq = 0;
function clip(startBeat: number, notes: Note[]): Clip {
  clipSeq += 1;
  return { id: `clip-${clipSeq}`, startBeat, notes };
}

/** 16 步鼓型 → Note 列表；'x' 正常，'o' 重音 */
function steps(pattern: string, pitch: number, bar: number, vel = 0.85): Note[] {
  const stepBeats = BEATS_PER_BAR / pattern.length;
  const out: Note[] = [];
  for (let i = 0; i < pattern.length; i++) {
    const ch = pattern[i];
    if (ch !== 'x' && ch !== 'o') continue;
    out.push({
      pitch,
      start: bar * BEATS_PER_BAR + i * stepBeats,
      dur: stepBeats * 0.9,
      vel: ch === 'o' ? vel : vel * 0.62,
    });
  }
  return out;
}

function buildDrums(): Note[] {
  const notes: Note[] = [];
  for (let bar = 0; bar < BARS; bar++) {
    const fill = bar === 7;
    notes.push(
      ...steps(fill ? 'x.......x.x.x...' : 'x.......x.x.....', 36, bar),
      ...steps(fill ? '....x.......x.xx' : '....x.......x...', 38, bar),
      ...steps('x.x.x.x.x.x.x.x.', 42, bar, 0.5),
      ...steps(fill ? '..............x.' : '..............x.', 46, bar, 0.45),
    );
  }
  return notes;
}

function buildBass(): Note[] {
  const notes: Note[] = [];
  PROGRESSION.forEach((chord, bar) => {
    const root = bassPitch(chord, 2);
    const fifth = chord.root === 4 ? 47 : root + 7; // E7 的五度取 B2
    const base = bar * BEATS_PER_BAR;
    notes.push(
      { pitch: root, start: base, dur: 1.5, vel: 0.9 },
      { pitch: root, start: base + 2, dur: 0.9, vel: 0.72 },
      { pitch: fifth, start: base + 3, dur: 0.9, vel: 0.6 },
    );
  });
  return notes;
}

function buildKeys(): Note[] {
  const notes: Note[] = [];
  let prev: number[] | null = null;
  PROGRESSION.forEach((chord, bar) => {
    const voicing = voiceChord(chord, prev);
    prev = voicing;
    const base = bar * BEATS_PER_BAR;
    for (const p of voicing) {
      notes.push({ pitch: p, start: base, dur: 1.15, vel: 0.5 });
      notes.push({ pitch: p, start: base + 2.5, dur: 1.2, vel: 0.42 });
    }
  });
  return notes;
}

function buildLead(): Note[] {
  return MELODY.map(([bar, beat, dur, pitch]) => ({
    pitch,
    start: bar * BEATS_PER_BAR + beat,
    // 缩到 82%，留出音与音之间的缝隙，避免连成一片
    dur: Math.max(0.25, dur * 0.82),
    vel: 0.78,
  }));
}

function track(
  id: string,
  name: string,
  kind: Track['kind'],
  gain: number,
  notes: Note[],
  preset?: string,
): Track {
  return { id, name, kind, preset, gain, mute: false, locked: false, clips: [clip(0, notes)] };
}

/**
 * 预置曲目：现场演示的兜底。
 * 不依赖网络、不依赖模型，打开就能听。
 */
export function createSeedSong(): Song {
  clipSeq = 0;
  return {
    id: 'seed-neon',
    title: '深夜霓虹',
    tempo: 84,
    meter: BEATS_PER_BAR,
    bars: BARS,
    key: KEY,
    sections: [
      { id: 's1', name: '主歌', startBar: 0, bars: 4, energy: 0.34 },
      { id: 's2', name: '副歌', startBar: 4, bars: 4, energy: 0.78 },
    ],
    chords: PROGRESSION.map((chord, i) => ({
      startBeat: i * BEATS_PER_BAR,
      beats: BEATS_PER_BAR,
      chord,
    })),
    tracks: [
      track('t-drums', '鼓组', 'drums', 0.9, buildDrums()),
      track('t-bass', '贝斯', 'bass', 0.8, buildBass(), 'sub'),
      track('t-keys', '和声', 'keys', 0.7, buildKeys(), 'supersaw'),
      track('t-lead', '主旋律', 'lead', 0.6, buildLead(), 'soft'),
    ],
    style: {
      name: '深夜 Lo-fi',
      brightness: 0.36,
      density: 0.44,
      groove: 0.58,
      tension: 0.32,
      dynamics: 0.62,
      bpm: 84,
      tags: ['lo-fi', 'A 小调', '钢琴', '吉他', '半拍律动'],
    },
    swing: 0.18,
  };
}

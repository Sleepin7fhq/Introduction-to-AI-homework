/**
 * 核心数据模型：整首曲子是一份可序列化的 JSON。
 * AI 生成、编辑器、播放引擎、导出全部围绕这一份结构工作。
 */

export type Mode = 'major' | 'minor';

export interface Key {
  /** 音级 0-11，0 = C */
  tonic: number;
  mode: Mode;
}

export type ChordQuality =
  | 'maj'
  | 'min'
  | 'dim'
  | 'aug'
  | 'maj7'
  | 'min7'
  | 'dom7'
  | 'm7b5'
  | 'dim7'
  | 'sus2'
  | 'sus4'
  | 'add9'
  | 'six'
  | 'min9'
  | 'maj9';

export interface Chord {
  /** 根音音级 0-11 */
  root: number;
  quality: ChordQuality;
  /** 转位次数 */
  inversion?: number;
}

export interface ChordEvent {
  /** 绝对拍数 */
  startBeat: number;
  beats: number;
  chord: Chord;
}

export type InstrumentKind = 'drums' | 'bass' | 'keys' | 'pad' | 'lead' | 'guitar';

export interface Note {
  /** MIDI 音高；鼓轨用 36=底鼓 38=军鼓 42=闭镲 46=开镲 */
  pitch: number;
  /** 相对 clip 起点的拍数 */
  start: number;
  /** 时值，拍 */
  dur: number;
  /** 力度 0-1 */
  vel: number;
}

export interface Clip {
  id: string;
  /** 绝对拍数 */
  startBeat: number;
  notes: Note[];
}

export interface Track {
  id: string;
  name: string;
  kind: InstrumentKind;
  /** 音色预设：house 的 stab、trap 的 808、DnB 的 reese 等 */
  preset?: string;
  /** 线性增益 0-1.5 */
  gain: number;
  mute: boolean;
  /** 锁定的轨道不会被 AI 改动 */
  locked: boolean;
  clips: Clip[];
}

export interface Section {
  id: string;
  name: string;
  startBar: number;
  bars: number;
  /** 0-1，用于情绪曲线 */
  energy: number;
}

export interface StyleProfile {
  name: string;
  brightness: number;
  density: number;
  groove: number;
  tension: number;
  dynamics: number;
  bpm: number;
  tags: string[];
}

export interface Song {
  id: string;
  title: string;
  tempo: number;
  /** 每小节拍数，固定 4 拍（4/4） */
  meter: number;
  bars: number;
  key: Key;
  sections: Section[];
  chords: ChordEvent[];
  tracks: Track[];
  style?: StyleProfile;
  /** 摇摆量 0-0.5，把反拍 8 分音符往后推，消除机械感 */
  swing?: number;
  /** 从描述里识别到的关键词，用于向用户解释"为什么是这首歌" */
  matched?: string[];
  /** 电子乐流派名，如 House / Techno / Trap */
  genre?: string;
  /** 采样套件（决定用哪组 one-shot 发声） */
  soundKit?: string;
}

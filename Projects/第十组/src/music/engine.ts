import * as Tone from 'tone';
import type { Song } from './types';
import { ensureSamplesLoaded, getBank, setActiveKit } from '../audio/sampler';

/**
 * 播放引擎：按小节滚动调度。
 * 每个小节开始时读取最新的 song 引用，所以编辑后下一个小节就能听到，
 * 不需要重新调度整首，也不会打断正在播放的声音。
 */

import { createVoice } from './voices';
import type { Voice } from './voices';

export { createVoice };
export type { Voice };

export class SongPlayer {
  private song: Song | null = null;
  private voices = new Map<string, Voice>();
  private reverb: Tone.Reverb;
  private bus: Tone.Gain;
  private limiter: Tone.Limiter;
  private compressor: Tone.Compressor;
  private eq: Tone.EQ3;
  private repeatId: number | null = null;
  private bar = 0;
  private playing = false;
  private audioReady: Promise<void> | null = null;
  /** 接在限幅器之后的真实波形分析器，给界面画示波器用 */
  private analyser: Tone.Analyser;

  onBar: ((bar: number) => void) | null = null;

  constructor() {
    this.limiter = new Tone.Limiter(-1).toDestination();
    // 限幅器后分一路给分析器：界面上的波形是真正在出声的那一路信号
    this.analyser = new Tone.Analyser('waveform', 1024);
    this.limiter.connect(this.analyser);
    // 总线压缩：把各轨粘在一起，避免"几轨各弹各的"
    this.compressor = new Tone.Compressor({
      threshold: -18,
      ratio: 2.5,
      attack: 0.02,
      release: 0.25,
      knee: 12,
    }).connect(this.limiter);
    // 总线 EQ：补低频重量与高频空气感（旧版直接进压缩，听起来单薄）
    this.eq = new Tone.EQ3({ low: 2, mid: 0, high: 1.5, lowFrequency: 200, highFrequency: 3200 })
      .connect(this.compressor);
    this.bus = new Tone.Gain(0.9).connect(this.eq);
    this.reverb = new Tone.Reverb({ decay: 2.4, preDelay: 0.015, wet: 0.26 }).connect(this.compressor);
  }

  get isPlaying(): boolean {
    return this.playing;
  }

  /** 真实波形数据（Float32Array，-1..1）。没在播放时是一串接近 0 的值。 */
  getWaveform(): Float32Array {
    const v = this.analyser.getValue();
    return v instanceof Float32Array ? v : new Float32Array(1024);
  }

  /** 主输出电平（0-1），给总线表头用 */
  getLevel(): number {
    const v = this.getWaveform();
    let peak = 0;
    for (let i = 0; i < v.length; i++) peak = Math.max(peak, Math.abs(v[i]));
    return Math.min(1, peak);
  }

  /**
   * 音频上下文必须在用户手势的同一个任务里 resume，
   * 所以点击时先调这个（不 await），后面再 await 同一个 promise。
   */
  ensureAudio(): Promise<void> {
    if (!this.audioReady) this.audioReady = Tone.start();
    return this.audioReady;
  }

  setSong(song: Song) {
    setActiveKit(song.soundKit as never);
    const firstLoad = this.song === null;
    this.song = song;
    Tone.Transport.bpm.value = song.tempo;
    Tone.Transport.loop = true;
    Tone.Transport.loopStart = 0;
    Tone.Transport.loopEnd = `${song.bars}m`;
    for (const t of song.tracks) {
      this.voices.get(t.id)?.setGain(t.mute ? 0 : t.gain);
    }
    if (firstLoad) return;
  }

  private syncVoices() {
    const song = this.song;
    if (!song) return;
    for (const t of song.tracks) {
      if (!this.voices.has(t.id)) {
        this.voices.set(t.id, createVoice(t, this.bus, this.reverb));
      }
    }
    for (const id of Array.from(this.voices.keys())) {
      if (!song.tracks.some((t) => t.id === id)) {
        this.voices.get(id)?.dispose();
        this.voices.delete(id);
      }
    }
  }

  async play() {
    if (!this.song) return;
    await this.ensureAudio();
    // 采样库：先加载并解码到当前实时上下文（失败则自动退回合成）
    await ensureSamplesLoaded();
    await getBank().prepare(Tone.getContext().rawContext as unknown as BaseAudioContext);
    // 重新生成时旧的发声器必须销毁：
    // AudioParam 上残留的自动化事件会让新的调度时间比它早，Tone 会直接抛错。
    for (const voice of this.voices.values()) voice.dispose();
    this.voices.clear();
    this.syncVoices();
    if (this.repeatId !== null) {
      Tone.Transport.clear(this.repeatId);
      this.repeatId = null;
    }
    Tone.Transport.stop();
    Tone.Transport.position = 0;
    this.bar = 0;
    this.repeatId = Tone.Transport.scheduleRepeat((time) => this.tick(time), '1m', 0);
    Tone.Transport.start('+0.08');
    this.playing = true;
  }

  stop() {
    Tone.Transport.stop();
    if (this.repeatId !== null) {
      Tone.Transport.clear(this.repeatId);
      this.repeatId = null;
    }
    Tone.Transport.position = 0;
    this.bar = 0;
    this.playing = false;
    this.onBar?.(0);
  }

  /** 当前播放位置（用于编辑器的步进游标） */
  getPosition(): { bar: number; step: number } {
    const ppq = Tone.Transport.PPQ;
    const beats = Tone.Transport.ticks / ppq;
    const bars = this.song?.bars ?? 1;
    const bar = Math.floor(beats / 4) % bars;
    const step = Math.floor((((beats % 4) + 4) % 4) / 0.25);
    return { bar, step };
  }

  /** 当前小节内的拍位置（0-4 的浮点数），播放头平滑移动用 */
  getBeatFraction(): number {
    const beats = Tone.Transport.ticks / Tone.Transport.PPQ;
    return ((beats % 4) + 4) % 4;
  }

  /** 试听一个和弦（编辑器里点选时用） */
  async previewChord(pitches: number[], dur = 1.2) {
    await this.ensureAudio();
    const song = this.song;
    if (!song) return;
    this.syncVoices();
    const keysTrack = song.tracks.find((t) => t.kind === 'keys');
    if (!keysTrack) return;
    const voice = this.voices.get(keysTrack.id);
    if (!voice) return;
    const now = Tone.now() + 0.02;
    for (const p of pitches) voice.trigger(p, dur, now, 0.55);
  }

  private tick(time: number) {
    const song = this.song;
    if (!song) return;
    const bar = this.bar % song.bars;
    this.scheduleBar(bar, time);
    Tone.getDraw().schedule(() => this.onBar?.(bar), time);
    this.bar += 1;
  }

  private scheduleBar(bar: number, time: number) {
    const song = this.song;
    if (!song) return;
    const beat0 = bar * song.meter;
    const secPerBeat = 60 / song.tempo;
    const swing = song.swing ?? 0;

    for (const track of song.tracks) {
      if (track.mute) continue;
      const voice = this.voices.get(track.id);
      if (!voice) continue;
      for (const clip of track.clips) {
        for (const n of clip.notes) {
          const abs = clip.startBeat + n.start;
          if (abs < beat0 || abs >= beat0 + song.meter) continue;
          let t = time + (abs - beat0) * secPerBeat;
          // 摇摆：反拍 8 分音符往后推一点，这是"人味"的最大来源
          if (swing > 0) {
            const off = ((abs % 1) + 1) % 1;
            if (Math.abs(off - 0.5) < 0.02) t += swing * 0.5 * secPerBeat;
          }
          // 微抖动：几毫秒的时间 + 力度偏差，避免每个音都像尺子量过
          t += (Math.random() - 0.5) * 0.013;
          const vel = Math.max(0.05, Math.min(1, n.vel + (Math.random() - 0.5) * 0.1));
          voice.trigger(n.pitch, Math.max(0.05, n.dur * secPerBeat), t, vel);
        }
      }
    }
  }
}

let instance: SongPlayer | null = null;

export function getPlayer(): SongPlayer {
  if (!instance) instance = new SongPlayer();
  return instance;
}

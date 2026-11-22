import * as Tone from 'tone';
import type { Track } from '../music/types';
import type { Voice } from '../music/voices';

/**
 * 采样库与采样器（2.2）。
 *
 * 关键设计：
 *   - WAV 放在 public/samples/，manifest.json 记录类型/根音/许可证；
 *   - AudioBuffer 与 AudioContext 绑定，所以按上下文预解码（prepare）：
 *     实时播放前解一次，离线渲染在 Offline 回调里再解一次；
 *   - 触发用原生 AudioBufferSourceNode：支持变调（playbackRate）、力度、声像、
 *     切片起点、复音叠加；
 *   - 经过原生 Gain/StereoPanner 后用 Tone.connect 汇入 Tone 总线，主链路不变。
 */

export interface SampleEntry {
  file: string;
  category: string;
  kind: string;
  duration: number;
  sampleRate: number;
  channels: number;
  rootNote: string | null;
  bpm: number | null;
  tags: string[];
  source: string;
  author: string;
  license: string;
  commercialUse: boolean;
  attributionRequired: boolean;
}

export interface SampleManifest {
  version: string;
  count: number;
  samples: SampleEntry[];
}

export type KitId = 'sifeng' | 'hardstyle' | 'techno' | 'edm' | 'chop' | 'hyper' | 'chaos';

interface Kit {
  kick: string[];
  snare: string[];
  clap: string[];
  hatClosed: string[];
  hatOpen: string[];
  cymbal: string[];
  bass: string;
  lead: string;
  pad: string;
  chop: string[];
}

/**
 * 乐器级音量配平。
 * 采样都归一化到 -1 dBFS，如果直接按力度触发，五轨叠起来会把限幅器打爆
 * （实测 RMS -7dB、air 20%）。这里按"鼓组内部比例"做一次静态配平。
 */
const OUTPUT_TRIM = 0.8;

const TRIM: Record<string, number> = {
  kick: 0.95,
  snare: 0.5,
  clap: 0.42,
  hat: 0.2,
  openhat: 0.18,
  cymbal: 0.22,
  bass: 0.4,
  lead: 0.32,
  chop: 0.26,
  pad: 0.2,
};

const KITS: Record<KitId, Kit> = {
  sifeng: {
    kick: ['drums/kick/kick_hard.wav'],
    snare: ['drums/snare/snare_crack.wav'],
    clap: ['drums/clap/clap_tight.wav'],
    hatClosed: ['drums/hihat/hat_closed.wav', 'drums/hihat/hat_tick.wav'],
    hatOpen: ['drums/hihat/hat_open.wav'],
    cymbal: ['drums/cymbal/crash.wav'],
    bass: 'bass/hardstyle/hard_bass_C1.wav',
    lead: 'synth/lead/lead_siren_C4.wav',
    pad: 'synth/pad/pad_dark_C3.wav',
    chop: ['vocal/chop/chop_a.wav', 'vocal/chop/chop_e.wav', 'vocal/chop/chop_o.wav'],
  },
  hardstyle: {
    kick: ['drums/kick/kick_hard.wav'],
    snare: ['drums/snare/snare_crack.wav'],
    clap: ['drums/clap/clap_wide.wav'],
    hatClosed: ['drums/hihat/hat_closed.wav'],
    hatOpen: ['drums/hihat/hat_open.wav'],
    cymbal: ['drums/cymbal/crash.wav'],
    bass: 'bass/hardstyle/hard_bass_F1.wav',
    lead: 'synth/lead/lead_hard_C4.wav',
    pad: 'synth/pad/pad_dark_C3.wav',
    chop: ['vocal/chop/chop_a.wav'],
  },
  techno: {
    kick: ['drums/kick/kick_deep.wav'],
    snare: ['drums/snare/snare_rim.wav'],
    clap: ['drums/clap/clap_tight.wav'],
    hatClosed: ['drums/hihat/hat_tick.wav', 'drums/hihat/hat_closed.wav'],
    hatOpen: ['drums/hihat/hat_open.wav'],
    cymbal: ['drums/cymbal/ride.wav'],
    bass: 'bass/reese/reese_C1.wav',
    lead: 'synth/lead/lead_saw_C4.wav',
    pad: 'synth/pad/pad_warm_C3.wav',
    chop: ['vocal/chop/chop_o.wav'],
  },
  edm: {
    kick: ['drums/kick/kick_punch.wav'],
    snare: ['drums/snare/snare_body.wav'],
    clap: ['drums/clap/clap_wide.wav'],
    hatClosed: ['drums/hihat/hat_closed.wav'],
    hatOpen: ['drums/hihat/hat_open.wav'],
    cymbal: ['drums/cymbal/crash.wav'],
    bass: 'bass/sub/sub_C1.wav',
    lead: 'synth/lead/lead_supersaw_C4.wav',
    pad: 'synth/pad/pad_wide_C3.wav',
    chop: ['vocal/chop/chop_a.wav'],
  },
  chop: {
    kick: ['drums/kick/kick_punch.wav'],
    snare: ['drums/snare/snare_trap.wav'],
    clap: ['drums/clap/clap_tight.wav'],
    hatClosed: ['drums/hihat/hat_tick.wav', 'drums/hihat/hat_closed.wav'],
    hatOpen: ['drums/hihat/hat_open.wav'],
    cymbal: ['drums/cymbal/ride.wav'],
    bass: 'bass/sub/sub_F1.wav',
    lead: 'vocal/chop/chop_a.wav',
    pad: 'synth/pad/pad_warm_C3.wav',
    chop: ['vocal/chop/chop_hey.wav', 'vocal/chop/chop_woo.wav', 'vocal/chop/chop_e.wav'],
  },
  hyper: {
    kick: ['drums/kick/kick_punch.wav'],
    snare: ['drums/snare/snare_crack.wav'],
    clap: ['drums/clap/clap_wide.wav'],
    hatClosed: ['drums/hihat/hat_closed.wav'],
    hatOpen: ['drums/hihat/hat_open.wav'],
    cymbal: ['drums/cymbal/crash.wav'],
    bass: 'bass/sub/sub_G1.wav',
    lead: 'synth/lead/lead_square_C4.wav',
    pad: 'synth/pad/pad_wide_C3.wav',
    chop: ['vocal/chop/chop_i.wav', 'vocal/chop/chop_e.wav'],
  },
  chaos: {
    kick: ['drums/kick/kick_hard.wav'],
    snare: ['drums/snare/snare_crack.wav'],
    clap: ['drums/clap/clap_wide.wav'],
    hatClosed: ['drums/hihat/hat_open.wav'],
    hatOpen: ['drums/hihat/hat_open.wav'],
    cymbal: ['drums/cymbal/crash.wav'],
    bass: 'bass/reese/reese_F1.wav',
    lead: 'synth/lead/lead_siren_C4.wav',
    pad: 'synth/pad/pad_dark_C3.wav',
    chop: ['vocal/chop/chop_a.wav', 'vocal/chop/chop_hey.wav'],
  },
};

export const KIT_IDS = Object.keys(KITS) as KitId[];

const SEMI: Record<string, number> = {
  C: 0, 'C#': 1, D: 2, 'D#': 3, E: 4, F: 5, 'F#': 6, G: 7, 'G#': 8, A: 9, 'A#': 10, B: 11,
};

function noteToMidi(name: string | null): number {
  if (!name) return 60;
  const m = /^([A-G]#?)(-?\d)$/.exec(name.trim());
  if (!m) return 60;
  return (parseInt(m[2], 10) + 1) * 12 + (SEMI[m[1]] ?? 0);
}

class SampleBankImpl {
  manifest: SampleManifest | null = null;
  ready = false;
  failed = false;
  private raw = new Map<string, ArrayBuffer>();
  private decoded = new WeakMap<BaseAudioContext, Map<string, AudioBuffer>>();
  private loading: Promise<void> | null = null;
  private preparing = new WeakMap<BaseAudioContext, Promise<void>>();
  private base = './samples/';

  setBase(base: string) {
    this.base = base.endsWith('/') ? base : base + '/';
  }

  load(): Promise<void> {
    if (this.loading) return this.loading;
    this.loading = this.loadInternal();
    return this.loading;
  }

  private async loadInternal() {
    try {
      const res = await fetch(this.base + 'manifest.json');
      if (!res.ok) throw new Error('manifest HTTP ' + res.status);
      this.manifest = (await res.json()) as SampleManifest;
      await Promise.all(
        this.manifest.samples.map(async (s) => {
          const r = await fetch(this.base + s.file);
          if (!r.ok) throw new Error('sample HTTP ' + r.status + ' ' + s.file);
          this.raw.set(s.file, await r.arrayBuffer());
        }),
      );
      this.ready = true;
    } catch (err) {
      this.failed = true;
      // 采样加载失败不能让播放挂掉：退回合成音色
      console.warn('[samples] 加载失败，回退合成音色：', err);
    }
  }

  /** 在指定上下文里解码全部素材（幂等） */
  prepare(ctx: BaseAudioContext): Promise<void> {
    const exist = this.preparing.get(ctx);
    if (exist) return exist;
    const task = (async () => {
      if (!this.ready) await this.load();
      if (!this.ready) return;
      let map = this.decoded.get(ctx);
      if (!map) {
        map = new Map();
        this.decoded.set(ctx, map);
      }
      await Promise.all(
        Array.from(this.raw.entries()).map(async ([file, buf]) => {
          if (map!.has(file)) return;
          try {
            const audio = await ctx.decodeAudioData(buf.slice(0));
            map!.set(file, audio);
          } catch (e) {
            console.warn('[samples] 解码失败', file, e);
          }
        }),
      );
    })();
    this.preparing.set(ctx, task);
    return task;
  }

  get(ctx: BaseAudioContext, file: string): AudioBuffer | undefined {
    return this.decoded.get(ctx)?.get(file);
  }

  entry(file: string): SampleEntry | undefined {
    return this.manifest?.samples.find((s) => s.file === file);
  }

  isReady(): boolean {
    return this.ready;
  }

  /** 该上下文是否已经解码好素材 */
  isPrepared(ctx: BaseAudioContext): boolean {
    const m = this.decoded.get(ctx);
    return !!m && m.size > 0;
  }
}

let bank: SampleBankImpl | null = null;
let activeKit: KitId = 'edm';

export function getBank(): SampleBankImpl {
  if (!bank) bank = new SampleBankImpl();
  return bank;
}

export function ensureSamplesLoaded(): Promise<void> {
  return getBank().load();
}

export function setActiveKit(kit: KitId | undefined) {
  if (kit && KITS[kit]) activeKit = kit;
}

export function currentKitId(): KitId {
  return activeKit;
}

function kitOf(id: KitId): Kit {
  return KITS[id];
}

/** 按音高/时间做一个确定性的变体选择，避免每次随机导致不可复现 */
function pickVariant(list: string[], pitch: number, time: number): string {
  if (list.length === 1) return list[0];
  const idx = Math.abs(Math.round(pitch) + Math.round(time * 1000)) % list.length;
  return list[idx];
}

export function createSampleVoice(track: Track, bus: Tone.Gain): Voice {
  const ctx = Tone.getContext().rawContext as unknown as BaseAudioContext;
  const kit = kitOf(activeKit);

  const out = ctx.createGain();
  out.gain.value = track.mute ? 0 : track.gain;
  const pan = ctx.createStereoPanner();
  pan.pan.value = 0;
  out.connect(pan);
  Tone.connect(pan, bus);

  let lastStart = -1;

  function play(file: string, pitch: number, durSec: number, time: number, vel: number, oneShot: boolean, trim = 1) {
    const buffer = getBank().get(ctx, file);
    if (!buffer) return;
    const entry = getBank().entry(file);
    const root = noteToMidi(entry?.rootNote ?? null);
    const rate = oneShot ? 1 : Math.pow(2, (pitch - root) / 12);
    // 防止极端变调把音色拉爆
    const safeRate = Math.max(0.25, Math.min(4, rate));

    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.playbackRate.value = safeRate;

    const g = ctx.createGain();
    const v = Math.max(0.02, Math.min(1, vel)) * trim * OUTPUT_TRIM;
    const attack = 0.002;
    const bufferDur = buffer.duration / safeRate;

    // 时间必须单调，否则 Tone/AudioParam 会互相覆盖
    const t0 = Math.max(time, lastStart + 0.0005);
    lastStart = t0;

    g.gain.setValueAtTime(0.0001, t0);
    g.gain.linearRampToValueAtTime(v, t0 + attack);

    let stopAt = t0 + bufferDur + 0.05;
    if (!oneShot) {
      // 有明确时值的音符：在时值末尾做 30ms 释放，避免咔嗒
      const hold = Math.max(0.03, durSec);
      const release = 0.03;
      if (t0 + hold < stopAt) {
        g.gain.setValueAtTime(v, t0 + hold);
        g.gain.linearRampToValueAtTime(0.0001, t0 + hold + release);
        stopAt = t0 + hold + release + 0.02;
      }
    }

    src.connect(g);
    g.connect(out);
    src.start(t0);
    src.stop(stopAt);
    src.onended = () => {
      try {
        src.disconnect();
        g.disconnect();
      } catch {
        /* 已断开 */
      }
    };
  }

  return {
    trigger: (pitch, dur, time, vel) => {
      if (!getBank().isReady()) return;
      if (track.kind === 'drums') {
        if (pitch === 36) play(pickVariant(kit.kick, pitch, time), pitch, dur, time, vel, true, TRIM.kick);
        else if (pitch === 38) play(pickVariant(kit.snare, pitch, time), pitch, dur, time, vel, true, TRIM.snare);
        else if (pitch === 39) play(pickVariant(kit.clap, pitch, time), pitch, dur, time, vel, true, TRIM.clap);
        else if (pitch === 42) play(pickVariant(kit.hatClosed, pitch, time), pitch, dur, time, vel, true, TRIM.hat);
        else if (pitch === 46) play(pickVariant(kit.hatOpen, pitch, time), pitch, dur, time, vel, true, TRIM.openhat);
        else if (pitch === 49) play(pickVariant(kit.cymbal, pitch, time), pitch, dur, time, vel, true, TRIM.cymbal);
        return;
      }
      if (track.kind === 'bass') {
        play(kit.bass, pitch, dur, time, vel, false, TRIM.bass);
        return;
      }
      if (track.kind === 'pad') {
        play(kit.pad, pitch, Math.max(dur, 0.6), time, vel, false, TRIM.pad);
        return;
      }
      if (track.kind === 'lead') {
        // 人声切片轨（preset 为元音名）走 chop 素材，其余走 lead 素材
        const isChop = ['a', 'e', 'i', 'o', 'u'].includes(track.preset ?? '');
        if (isChop) {
          play(pickVariant(kit.chop, pitch, time), pitch, Math.min(dur, 0.35), time, vel, false, TRIM.chop);
        } else {
          play(kit.lead, pitch, dur, time, vel, false, TRIM.lead);
        }
        return;
      }
      if (track.kind === 'keys') {
        play(kit.pad, pitch, Math.min(dur, 0.5), time, vel, false, TRIM.pad);
      }
    },
    setGain: (g) => {
      out.gain.setTargetAtTime(track.mute ? 0 : g, ctx.currentTime, 0.02);
    },
    dispose: () => {
      try {
        pan.disconnect();
        out.disconnect();
      } catch {
        /* ignore */
      }
    },
  };
}

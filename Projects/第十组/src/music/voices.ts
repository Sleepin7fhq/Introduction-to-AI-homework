import * as Tone from 'tone';
import type { Track } from './types';
import { createSampleVoice, getBank } from '../audio/sampler';

/**
 * 音色引擎（2.1 版）。
 *
 * 旧版的问题：所有音色都是"一个振荡器 + 一条包络"，没有分层、没有失真、
 * 没有延迟/混响差异，结果就是薄、像提示音、像口水声。
 *
 * 新版原则：
 *   1. 鼓组必须是分层的（body + sub + click / noise + body），单层永远做不出冲击力；
 *   2. 贝斯必须 sub 与 mid 分轨，只用一个锯齿会糊成一团；
 *   3. 主音必须 detune 叠层 + 滤波 + 延迟，单振荡器就是"电子提示音"；
 *   4. 每个音都要有最小 attack/release（2ms/40ms），否则会有咔嗒声；
 *   5. 人声切片用共振峰合成（3 个带通模拟元音），不采样、不侵权。
 */

export interface Voice {
  trigger: (pitch: number, durSec: number, time: number, velocity: number) => void;
  setGain: (g: number) => void;
  dispose: () => void;
}

const midiToNote = (p: number) => Tone.Frequency(p, 'midi').toNote();

/** 软削波曲线：比硬限幅温和，能增加"厚度"而不炸 */
function driveCurve(amount: number): (x: number) => number {
  const k = 1 + amount * 12;
  return (x: number) => Math.tanh(x * k) / Math.tanh(k);
}

function shaper(amount: number): Tone.WaveShaper {
  return new Tone.WaveShaper(driveCurve(amount), 2048);
}

interface Ctx {
  out: Tone.Gain;
  rev: Tone.Gain;
  dly: Tone.Gain;
  disposables: Array<{ dispose: () => void }>;
}

function makeCtx(track: Track, bus: Tone.Gain, reverb: Tone.Reverb, revAmt: number, dlyAmt: number): Ctx {
  const out = new Tone.Gain(track.mute ? 0 : track.gain).connect(bus);
  const rev = new Tone.Gain(revAmt).connect(reverb);
  out.connect(rev);
  const delay = new Tone.FeedbackDelay({ delayTime: 0.1875, feedback: 0.28, wet: 1 });
  const dly = new Tone.Gain(dlyAmt).connect(delay);
  delay.connect(bus);
  out.connect(dly);
  return { out, rev, dly, disposables: [out, rev, dly, delay] };
}

/* ------------------------------------------------------------------ */
/* 鼓组                                                                */
/* ------------------------------------------------------------------ */

function createDrums(track: Track, bus: Tone.Gain, reverb: Tone.Reverb): Voice {
  const preset = track.preset ?? 'electronic';
  const isHard = preset === 'hardstyle';
  const isRave = preset === 'rave' || preset === 'chaos';
  const ctx = makeCtx(track, bus, reverb, isHard ? 0.1 : 0.12, 0.05);
  const d = ctx.disposables;

  // ---- Kick：body（音高下坠）+ sub（低频垫）+ click（高频瞬态）----
  const kickDrive = new Tone.WaveShaper(driveCurve(isHard ? 0.5 : isRave ? 0.3 : 0.15), 2048);
  kickDrive.connect(ctx.out);
  const kickBody = new Tone.MembraneSynth({
    pitchDecay: isHard ? 0.11 : 0.048,
    octaves: isHard ? 8 : 6,
    oscillator: { type: 'sine' },
    envelope: { attack: 0.001, decay: isHard ? 0.42 : 0.3, sustain: 0, release: 0.14 },
    volume: isHard ? 1 : -1,
  }).connect(kickDrive);

  const kickSub = new Tone.MonoSynth({
    oscillator: { type: 'sine' },
    envelope: { attack: 0.002, decay: 0.24, sustain: 0.0, release: 0.18 },
    filter: { type: 'lowpass', Q: 0.4, rolloff: -12 },
    filterEnvelope: { attack: 0.001, decay: 0.2, sustain: 0.0, release: 0.1, baseFrequency: 120, octaves: 0.6 },
    volume: isHard ? -2 : -5,
  }).connect(kickDrive);

  const clickFilter = new Tone.Filter(2600, 'highpass').connect(ctx.out);
  const kickClick = new Tone.NoiseSynth({
    noise: { type: 'white' },
    envelope: { attack: 0.001, decay: 0.012, sustain: 0 },
    volume: isHard ? -14 : -20,
  }).connect(clickFilter);

  // ---- Snare：噪声（沙）+ 鼓皮（咚）+ 高频 crack ----
  const snareBand = new Tone.Filter({ type: 'bandpass', frequency: 1750, Q: 0.9 }).connect(ctx.out);
  const snareNoise = new Tone.NoiseSynth({
    noise: { type: 'pink' },
    envelope: { attack: 0.001, decay: isHard ? 0.22 : 0.16, sustain: 0 },
    volume: isHard ? -7 : -10,
  }).connect(snareBand);

  const snareBody = new Tone.MembraneSynth({
    pitchDecay: 0.012,
    octaves: 2.5,
    oscillator: { type: 'triangle' },
    envelope: { attack: 0.001, decay: 0.09, sustain: 0 },
    volume: -17,
  }).connect(ctx.out);

  const crackHp = new Tone.Filter(5200, 'highpass').connect(ctx.out);
  const snareCrack = new Tone.NoiseSynth({
    noise: { type: 'white' },
    envelope: { attack: 0.0008, decay: 0.008, sustain: 0 },
    volume: -22,
  }).connect(crackHp);

  // ---- Clap：三连击噪声（比单次拍手真实得多）----
  const clapBand = new Tone.Filter({ type: 'bandpass', frequency: 1250, Q: 1.2 }).connect(ctx.out);
  const clap = new Tone.NoiseSynth({
    noise: { type: 'white' },
    envelope: { attack: 0.001, decay: 0.02, sustain: 0 },
    volume: -12,
  }).connect(clapBand);

  // ---- Hats ----
  const hatHp = new Tone.Filter(isHard ? 9200 : 8400, 'highpass').connect(ctx.out);
  const hat = new Tone.NoiseSynth({
    noise: { type: 'white' },
    envelope: { attack: 0.001, decay: isHard ? 0.028 : 0.042, sustain: 0 },
    volume: -24,
  }).connect(hatHp);

  const openBand = new Tone.Filter({ type: 'highpass', frequency: 7200 }).connect(ctx.out);
  const openHat = new Tone.NoiseSynth({
    noise: { type: 'white' },
    envelope: { attack: 0.002, decay: 0.22, sustain: 0.0 },
    volume: -27,
  }).connect(openBand);

  d.push(kickDrive, kickBody, kickSub, clickFilter, kickClick, snareBand, snareNoise, snareBody,
    crackHp, snareCrack, clapBand, clap, hatHp, hat, openBand, openHat);

  return {
    trigger: (pitch, _dur, time, vel) => {
      const v = Math.max(0.05, Math.min(1, vel));
      if (pitch === 36) {
        kickBody.triggerAttackRelease('C1', isHard ? 0.32 : 0.22, time, v * 1.0);
        kickSub.triggerAttackRelease('C1', 0.18, time, v * 0.85);
        kickClick.triggerAttackRelease(0.01, time, v * 0.55);
      } else if (pitch === 38) {
        snareNoise.triggerAttackRelease(isHard ? 0.2 : 0.14, time, v * 0.95);
        snareBody.triggerAttackRelease('G2', 0.08, time, v * 0.6);
        snareCrack.triggerAttackRelease(0.008, time, v * 0.5);
      } else if (pitch === 39) {
        // 三连击：0 / 12ms / 26ms
        clap.triggerAttackRelease(0.018, time, v * 0.85);
        clap.triggerAttackRelease(0.018, time + 0.012, v * 0.7);
        clap.triggerAttackRelease(0.05, time + 0.026, v * 0.55);
      } else if (pitch === 42) {
        hat.triggerAttackRelease(isHard ? 0.025 : 0.038, time, v * 0.75);
      } else if (pitch === 46) {
        openHat.triggerAttackRelease(0.2, time, v * 0.6);
      }
    },
    setGain: (g) => ctx.out.gain.rampTo(track.mute ? 0 : g, 0.05),
    dispose: () => d.forEach((x) => x.dispose()),
  };
}

/* ------------------------------------------------------------------ */
/* 贝斯：sub + mid 双层                                                 */
/* ------------------------------------------------------------------ */

function createBass(track: Track, bus: Tone.Gain, reverb: Tone.Reverb): Voice {
  const preset = track.preset ?? 'sub';
  const ctx = makeCtx(track, bus, reverb, preset === 'reese' ? 0.1 : 0.06, 0.04);
  const d = ctx.disposables;

  // sub 层：只负责 40-80Hz 的"胸口"
  const sub = new Tone.MonoSynth({
    oscillator: { type: 'sine' },
    envelope: { attack: 0.004, decay: 0.22, sustain: 0.55, release: 0.12 },
    filter: { type: 'lowpass', Q: 0.3, rolloff: -12 },
    volume: -4,
  }).connect(ctx.out);

  // mid 层：负责"听得见的贝斯"
  const bassDrive = shaper(preset === 'hard' || preset === 'rave' ? 0.42 : 0.18);
  bassDrive.connect(ctx.out);
  const midFilter = new Tone.Filter({ type: 'lowpass', frequency: 900, Q: preset === 'acid' ? 8 : 1.2, rolloff: -24 }).connect(bassDrive);

  const midOpts: Record<string, Record<string, unknown>> = {
    sub: { oscillator: { type: 'sawtooth' }, volume: -16 },
    pluck: { oscillator: { type: 'sawtooth' }, volume: -13 },
    acid: { oscillator: { type: 'sawtooth' }, volume: -12 },
    reese: { oscillator: { type: 'fatsawtooth', count: 3, spread: 22 }, volume: -15 },
    e808: { oscillator: { type: 'sine' }, volume: -22 },
    rave: { oscillator: { type: 'fatsawtooth', count: 2, spread: 14 }, volume: -11 },
    hard: { oscillator: { type: 'sawtooth' }, volume: -9 },
    hoover: { oscillator: { type: 'fatsawtooth', count: 3, spread: 30 }, volume: -12 },
  };

  const mid = new Tone.MonoSynth({
    ...(midOpts[preset] ?? midOpts.sub),
    filter: { type: 'lowpass', Q: 1, rolloff: -24 },
    envelope: { attack: 0.006, decay: 0.2, sustain: preset === 'sub' ? 0.4 : 0.6, release: 0.12 },
    filterEnvelope: {
      attack: 0.004,
      decay: preset === 'acid' ? 0.14 : 0.22,
      sustain: preset === 'acid' ? 0.05 : 0.35,
      release: 0.12,
      baseFrequency: preset === 'acid' ? 180 : 120,
      octaves: preset === 'acid' ? 4.2 : 2.4,
    },
  }).connect(midFilter);

  d.push(sub, bassDrive, midFilter, mid);

  return {
    trigger: (pitch, dur, time, vel) => {
      const len = Math.max(0.09, dur);
      if (preset === 'e808') {
        // 808：正弦 + 滑音 + 长衰减，不需要 sub 层
        mid.triggerAttackRelease(midiToNote(pitch - 12), Math.max(0.3, len * 1.4), time, vel);
        return;
      }
      sub.triggerAttackRelease(midiToNote(Math.max(24, pitch - 12)), len * 0.95, time, vel * 0.95);
      mid.triggerAttackRelease(midiToNote(pitch), len, time, vel * 0.9);
    },
    setGain: (g) => ctx.out.gain.rampTo(track.mute ? 0 : g, 0.05),
    dispose: () => d.forEach((x) => x.dispose()),
  };
}

/* ------------------------------------------------------------------ */
/* 和声 / Pad                                                          */
/* ------------------------------------------------------------------ */

function polySaw(count: number, spread: number, opts: Record<string, unknown> = {}) {
  return new Tone.PolySynth(Tone.Synth, {
    oscillator: { type: 'fatsawtooth', count, spread },
    ...opts,
  });
}

function createKeys(track: Track, bus: Tone.Gain, reverb: Tone.Reverb): Voice {
  const preset = track.preset ?? 'stab';
  const ctx = makeCtx(track, bus, reverb, preset === 'supersaw' ? 0.42 : 0.28, preset === 'pluck' ? 0.22 : 0.12);
  const d = ctx.disposables;

  const chorus = new Tone.Chorus({ frequency: 0.8, delayTime: 3.5, depth: 0.5, wet: 0.4 }).start();
  const hp = new Tone.Filter(140, 'highpass').connect(chorus);
  chorus.connect(ctx.out);
  d.push(chorus, hp);

  if (preset === 'stab_wide') {
    const filter = new Tone.Filter({ type: 'lowpass', frequency: 3000, Q: 1.4 }).connect(hp);
    const synth = polySaw(4, 26, {
      envelope: { attack: 0.004, decay: 0.18, sustain: 0, release: 0.16 },
      volume: -18,
    }).connect(filter);
    d.push(filter, synth);
    return {
      trigger: (pitch, dur, time, vel) =>
        synth.triggerAttackRelease(midiToNote(pitch), Math.min(0.26, Math.max(0.08, dur)), time, vel),
      setGain: (g) => ctx.out.gain.rampTo(track.mute ? 0 : g, 0.05),
      dispose: () => d.forEach((x) => x.dispose()),
    };
  }

  if (preset === 'stab') {
    const filter = new Tone.Filter({ type: 'lowpass', frequency: 2600, Q: 2.2 }).connect(hp);
    const synth = polySaw(2, 12, {
      envelope: { attack: 0.003, decay: 0.16, sustain: 0, release: 0.12 },
      volume: -17,
    }).connect(filter);
    d.push(filter, synth);
    return {
      trigger: (pitch, dur, time, vel) =>
        synth.triggerAttackRelease(midiToNote(pitch), Math.min(0.22, Math.max(0.08, dur)), time, vel),
      setGain: (g) => ctx.out.gain.rampTo(track.mute ? 0 : g, 0.05),
      dispose: () => d.forEach((x) => x.dispose()),
    };
  }

  if (preset === 'supersaw') {
    const filter = new Tone.Filter({ type: 'lowpass', frequency: 3200, Q: 0.7 }).connect(hp);
    const synth = polySaw(5, 30, {
      envelope: { attack: 0.12, decay: 0.9, sustain: 0.72, release: 1.4 },
      volume: -26,
    }).connect(filter);
    d.push(filter, synth);
    return {
      trigger: (pitch, dur, time, vel) =>
        synth.triggerAttackRelease(midiToNote(pitch), Math.max(0.25, dur), time, vel),
      setGain: (g) => ctx.out.gain.rampTo(track.mute ? 0 : g, 0.05),
      dispose: () => d.forEach((x) => x.dispose()),
    };
  }

  if (preset === 'pluck') {
    const filter = new Tone.Filter({ type: 'lowpass', frequency: 4200, Q: 1.2 }).connect(hp);
    const synth = new Tone.PolySynth(Tone.Synth, {
      oscillator: { type: 'fatsawtooth', count: 2, spread: 9 },
      envelope: { attack: 0.002, decay: 0.14, sustain: 0, release: 0.1 },
      volume: -14,
    }).connect(filter);
    d.push(filter, synth);
    return {
      trigger: (pitch, dur, time, vel) =>
        synth.triggerAttackRelease(midiToNote(pitch), Math.min(0.3, Math.max(0.07, dur)), time, vel),
      setGain: (g) => ctx.out.gain.rampTo(track.mute ? 0 : g, 0.05),
      dispose: () => d.forEach((x) => x.dispose()),
    };
  }

  // piano
  const filter = new Tone.Filter(3600, 'lowpass').connect(hp);
  const synth = new Tone.PolySynth(Tone.FMSynth, {
    harmonicity: 1,
    modulationIndex: 5,
    oscillator: { type: 'sine' },
    envelope: { attack: 0.002, decay: 1.4, sustain: 0.03, release: 0.6 },
    modulation: { type: 'sine' },
    modulationEnvelope: { attack: 0.001, decay: 0.3, sustain: 0, release: 0.2 },
    volume: -14,
  }).connect(filter);
  d.push(filter, synth);
  return {
    trigger: (pitch, dur, time, vel) => synth.triggerAttackRelease(midiToNote(pitch), Math.max(0.12, dur), time, vel),
    setGain: (g) => ctx.out.gain.rampTo(track.mute ? 0 : g, 0.05),
    dispose: () => d.forEach((x) => x.dispose()),
  };
}

/* ------------------------------------------------------------------ */
/* 人声切片：共振峰合成                                                */
/* ------------------------------------------------------------------ */

/** 元音共振峰（男声近似）：a / o / e / i */
const VOWELS: Record<string, Array<[number, number]>> = {
  a: [[730, 1.0], [1090, 0.5], [2440, 0.25]],
  o: [[570, 1.0], [840, 0.6], [2410, 0.12]],
  e: [[530, 1.0], [1840, 0.4], [2480, 0.2]],
  i: [[270, 1.0], [2290, 0.3], [3010, 0.2]],
};

function createVocalChop(track: Track, bus: Tone.Gain, reverb: Tone.Reverb): Voice {
  const ctx = makeCtx(track, bus, reverb, 0.34, 0.22);
  const d = ctx.disposables;

  const preset = track.preset ?? 'a';
  const formants = VOWELS[preset] ?? VOWELS.a;

  const src = new Tone.PolySynth(Tone.Synth, {
    oscillator: { type: 'sawtooth' },
    envelope: { attack: 0.008, decay: 0.12, sustain: 0.25, release: 0.09 },
    volume: -12,
  });

  const vibrato = new Tone.Vibrato(5.6, 0.06).connect(ctx.out);
  const drive = shaper(0.22).connect(vibrato);
  d.push(vibrato, drive);

  for (const [freq, gainAmt] of formants) {
    const bp = new Tone.Filter({ type: 'bandpass', frequency: freq, Q: 6 }).connect(drive);
    const g = new Tone.Gain(gainAmt * 2.2).connect(bp);
    src.connect(g);
    d.push(bp, g);
  }
  d.push(src);

  return {
    trigger: (pitch, dur, time, vel) => {
      const len = Math.min(0.22, Math.max(0.06, dur));
      src.triggerAttackRelease(midiToNote(pitch + 12), len, time, Math.max(0.1, vel));
    },
    setGain: (g) => ctx.out.gain.rampTo(track.mute ? 0 : g, 0.05),
    dispose: () => d.forEach((x) => x.dispose()),
  };
}

/* ------------------------------------------------------------------ */
/* 主音                                                                */
/* ------------------------------------------------------------------ */

function createLead(track: Track, bus: Tone.Gain, reverb: Tone.Reverb): Voice {
  const preset = track.preset ?? 'saw';

  if (preset === 'vocal' || preset === 'a' || preset === 'o' || preset === 'e' || preset === 'i') {
    return createVocalChop(track, bus, reverb);
  }

  const isRave = preset === 'rave';
  const isHard = preset === 'hard';
  const isSiren = preset === 'siren' || preset === 'grit';
  const isHyper = preset === 'hyper';

  const ctx = makeCtx(
    track, bus, reverb,
    isHard ? 0.16 : 0.3,
    isRave ? 0.3 : isHyper ? 0.4 : isSiren ? 0.24 : 0.2,
  );
  const d = ctx.disposables;

  const driveAmount = isHard ? 0.55 : isRave ? 0.3 : isHyper ? 0.45 : isSiren ? 0.4 : 0.12;
  const drive = shaper(driveAmount);
  const filter = new Tone.Filter({
    type: 'lowpass',
    frequency: isHard ? 4600 : isRave ? 6800 : isSiren ? 6200 : isHyper ? 7600 : 5200,
    Q: isSiren ? 6 : 1.1,
  }).connect(drive);

  if (isSiren) {
    const vib = new Tone.Vibrato(5.2, 0.12).connect(ctx.out);
    const dist = new Tone.Distortion(0.35).connect(vib);
    d.push(vib, dist);
    filter.connect(dist);
  } else {
    filter.connect(ctx.out);
  }
  d.push(drive, filter);

  const count = isHard ? 5 : isRave ? 4 : isHyper ? 3 : 3;
  const spread = isHard ? 32 : isRave ? 24 : isHyper ? 18 : 16;
  const synth = new Tone.PolySynth(Tone.Synth, {
    oscillator: { type: isHyper ? 'pulse' : 'fatsawtooth', count, spread },
    envelope: {
      attack: isSiren ? 0.02 : 0.008,
      decay: isHard ? 0.18 : 0.24,
      sustain: isSiren ? 0.8 : 0.55,
      release: isSiren ? 0.22 : 0.3,
    },
    volume: isHard ? -18 : -16,
  }).connect(filter);

  const chorus = new Tone.Chorus({ frequency: 1.2, delayTime: 2.8, depth: 0.35, wet: isRave || isHyper ? 0.5 : 0.25 }).start();
  synth.disconnect();
  synth.connect(chorus);
  chorus.connect(filter);
  d.push(chorus, synth);

  return {
    trigger: (pitch, dur, time, vel) => {
      const len = Math.max(0.1, Math.min(isSiren ? 0.6 : 0.9, dur));
      synth.triggerAttackRelease(midiToNote(pitch), len, time, Math.max(0.1, vel));
    },
    setGain: (g) => ctx.out.gain.rampTo(track.mute ? 0 : g, 0.05),
    dispose: () => d.forEach((x) => x.dispose()),
  };
}

/* ------------------------------------------------------------------ */
/* Pad                                                                 */
/* ------------------------------------------------------------------ */

function createPad(track: Track, bus: Tone.Gain, reverb: Tone.Reverb): Voice {
  const ctx = makeCtx(track, bus, reverb, 0.55, 0.1);
  const d = ctx.disposables;
  const filter = new Tone.Filter({ type: 'lowpass', frequency: 1250, Q: 0.6 }).connect(ctx.out);
  const lfo = new Tone.LFO(0.07, 800, 1600).connect(filter.frequency);
  lfo.start();
  const chorus = new Tone.Chorus({ frequency: 0.35, delayTime: 5, depth: 0.7, wet: 0.6 }).start();
  chorus.connect(filter);
  const synth = polySaw(4, 26, {
    envelope: { attack: 0.7, decay: 1.2, sustain: 0.72, release: 2.8 },
    volume: -30,
  }).connect(chorus);
  d.push(filter, lfo, chorus, synth);

  return {
    trigger: (pitch, dur, time, vel) => synth.triggerAttackRelease(midiToNote(pitch), Math.max(0.4, dur), time, vel),
    setGain: (g) => ctx.out.gain.rampTo(track.mute ? 0 : g, 0.05),
    dispose: () => d.forEach((x) => x.dispose()),
  };
}

/* ------------------------------------------------------------------ */

export function createVoice(track: Track, bus: Tone.Gain, reverb: Tone.Reverb): Voice {
  // 采样库就绪时优先用真实 one-shot；否则自动退回合成音色
  const bank = getBank();
  const ctx = Tone.getContext().rawContext as unknown as BaseAudioContext;
  if (bank.isReady() && bank.isPrepared(ctx)) {
    return createSampleVoice(track, bus);
  }
  if (track.kind === 'drums') return createDrums(track, bus, reverb);
  if (track.kind === 'bass') return createBass(track, bus, reverb);
  if (track.kind === 'keys') return createKeys(track, bus, reverb);
  if (track.kind === 'pad') return createPad(track, bus, reverb);
  if (track.kind === 'lead') return createLead(track, bus, reverb);
  return createKeys(track, bus, reverb);
}

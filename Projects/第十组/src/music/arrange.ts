import type { Note, Song, Track } from './types';

/**
 * 编曲层：生成器负责"音符对不对"，这一层负责"什么时候该有、什么时候该停"。
 *
 * 电子舞曲的现场冲击力基本来自三件事：
 *   1. 进入（instrumentation 一层层加）
 *   2. 抽空（Drop 前把所有声部掐掉，制造真空）
 *   3. 回归（全编制砸下来）
 * 这里把它们做成可计算的段落计划，而不是靠随机。
 */

export interface ArrangePlan {
  kind: 'rave' | 'song';
  bars: number;
  introEnd: number;
  buildEnd: number;
  dropEnd: number;
  breakEnd: number;
  /** 0-1，越高鼓越密、Drop 越满 */
  hype: number;
}

export function planRave(bars: number, energy: number): ArrangePlan {
  const q = Math.max(1, Math.floor(bars / 4));
  return {
    kind: 'rave',
    bars,
    introEnd: q,
    buildEnd: q * 2,
    dropEnd: q * 3,
    breakEnd: q * 3 + Math.max(1, Math.floor(q / 2)),
    hype: Math.max(0.2, Math.min(1, energy)),
  };
}

export function planSong(bars: number, energy: number): ArrangePlan {
  const q = Math.max(1, Math.floor(bars / 4));
  return {
    kind: 'song',
    bars,
    introEnd: q,
    buildEnd: q * 2,
    dropEnd: q * 3,
    breakEnd: q * 3 + Math.max(1, Math.floor(q / 2)),
    hype: Math.max(0.2, Math.min(1, energy)),
  };
}

type Phase = 'intro' | 'build' | 'drop' | 'break' | 'last';

export function phaseAt(plan: ArrangePlan, bar: number): Phase {
  if (bar < plan.introEnd) return 'intro';
  if (bar < plan.buildEnd) return 'build';
  if (bar < plan.dropEnd) return 'drop';
  if (bar < plan.breakEnd) return 'break';
  return 'last';
}

/** 给时间轴画能量曲线用：0-1 */
export function energyAtBar(plan: ArrangePlan, bar: number): number {
  const p = phaseAt(plan, bar);
  switch (p) {
    case 'intro':
      return 0.22;
    case 'build':
      return 0.45 + (0.3 * (bar - plan.introEnd)) / Math.max(1, plan.buildEnd - plan.introEnd);
    case 'drop':
      return 0.9;
    case 'break':
      return 0.35;
    case 'last':
      return 1;
  }
}

/**
 * 把生成的 Song 套上段落编排。
 * 纯函数：返回新对象，不改原 song。
 */
export function arrangeSong(song: Song, plan: ArrangePlan): Song {
  const bars = Math.min(song.bars, plan.bars);
  const dropOutStart = (plan.buildEnd - 1) * 4 + 3; // 最后一小节第 4 拍
  const dropOutEnd = plan.buildEnd * 4;

  const tracks: Track[] = song.tracks.map((track) => {
    const notes: Note[] = [];

    for (const clip of track.clips) {
      for (const n of clip.notes) {
        const abs = clip.startBeat + n.start;
        const bar = Math.floor(abs / 4);
        if (bar >= bars) continue;
        const phase = phaseAt(plan, bar);

        // Drop 前的真空：最后一拍全部静音，制造下坠感
        if (abs >= dropOutStart && abs < dropOutEnd) continue;

        const isKick = n.pitch === 36;
        const isSnare = n.pitch === 38 || n.pitch === 39;
        const isHat = n.pitch === 42 || n.pitch === 46;

        if (track.kind === 'drums') {
          if (phase === 'intro') {
            if (!isKick) continue;
            // 前奏只要每小节第 1、3 拍，留出空间
            if (Math.round((abs % 4) * 100) / 100 % 2 !== 0) continue;
          }
          if (phase === 'build') {
            if (isSnare && bar === plan.introEnd) continue;
            if (isHat && plan.hype < 0.55 && Math.floor(abs * 4) % 2 === 1) continue;
          }
          if (phase === 'break') {
            if (!isKick) continue;
            if (Math.round(abs % 4) !== 0) continue;
          }
          notes.push({ ...n, start: abs, vel: Math.min(1, n.vel * (phase === 'last' ? 1.08 : 1)) });
          continue;
        }

        if (track.kind === 'bass') {
          if (phase === 'intro' || phase === 'break') continue;
          notes.push({ ...n, start: abs });
          continue;
        }

        if (track.kind === 'lead') {
          if (phase === 'intro' || phase === 'build') continue;
          notes.push({ ...n, start: abs });
          continue;
        }

        // keys / pad / guitar：全程铺，但前奏与 Break 减力度，避免糊
        const factor = phase === 'intro' ? 0.72 : phase === 'break' ? 0.8 : 1;
        notes.push({ ...n, start: abs, vel: Math.min(1, n.vel * factor) });
      }
    }

    return {
      ...track,
      clips: [{ id: `${track.id}-clip`, startBeat: 0, notes }],
    };
  });

  // Riser：Drop 前两小节的一条上行铺底，这是段落能量的"电梯"
  const riser = buildRiser(plan, dropOutStart);
  if (riser.length > 0) {
    tracks.push({
      id: 't-riser',
      name: 'Riser',
      kind: 'pad',
      preset: 'riser',
      gain: 0.34,
      mute: false,
      locked: false,
      clips: [{ id: 't-riser-clip', startBeat: 0, notes: riser }],
    });
  }

  // Drop 落点加一记开镲 + 底鼓，让"砸下来"有物理冲击
  const dropBar = plan.buildEnd;
  for (const t of tracks) {
    if (t.kind !== 'drums') continue;
    const clip = t.clips[0];
    if (!clip) continue;
    clip.notes.push({ pitch: 46, start: dropBar * 4, dur: 0.4, vel: 1 });
    if (!clip.notes.some((n) => n.pitch === 36 && Math.abs(n.start - dropBar * 4) < 0.01)) {
      clip.notes.push({ pitch: 36, start: dropBar * 4, dur: 0.3, vel: 1 });
    }
  }

  return {
    ...song,
    bars,
    tracks,
    swing: plan.kind === 'rave' ? Math.min(0.1, song.swing ?? 0) : song.swing,
    sections: [
      { id: 's-intro', name: '前奏', startBar: 0, bars: plan.introEnd, energy: 0.22 },
      {
        id: 's-build',
        name: '铺陈',
        startBar: plan.introEnd,
        bars: plan.buildEnd - plan.introEnd,
        energy: 0.55,
      },
      {
        id: 's-drop',
        name: 'Drop',
        startBar: plan.buildEnd,
        bars: plan.dropEnd - plan.buildEnd,
        energy: 0.95,
      },
      {
        id: 's-break',
        name: 'Break',
        startBar: plan.dropEnd,
        bars: plan.breakEnd - plan.dropEnd,
        energy: 0.38,
      },
      {
        id: 's-last',
        name: '二次 Drop',
        startBar: plan.breakEnd,
        bars: Math.max(0, bars - plan.breakEnd),
        energy: 1,
      },
    ].filter((s) => s.bars > 0),
  };
}

function buildRiser(plan: ArrangePlan, stopBeat: number): Note[] {
  const startBar = Math.max(0, plan.buildEnd - 2);
  const notes: Note[] = [];
  const steps = 16;
  const from = startBar * 4;
  // riser 在 Drop 前最后一拍必须掐掉，否则"真空"就漏气了
  const span = Math.min((plan.buildEnd - startBar) * 4, stopBeat - from);
  if (span <= 0) return notes;
  // 从 A3 一路推到 A5，力度递增，越接近 Drop 越紧
  for (let i = 0; i < steps; i++) {
    const t = i / steps;
    notes.push({
      pitch: Math.round(57 + t * 24),
      start: from + t * span,
      dur: 0.3,
      vel: 0.2 + t * 0.55,
    });
  }
  return notes;
}

import type { InstrumentKind, Song } from './types';

/**
 * 导出标准 MIDI 文件（SMF format 1）。
 * 每件乐器一条轨，鼓走第 10 通道，可以直接拖进任何 DAW。
 */

const TICKS_PER_BEAT = 480;

const PROGRAM: Record<InstrumentKind, number> = {
  keys: 0, // Acoustic Grand Piano
  bass: 33, // Electric Bass (finger)
  pad: 89, // Pad 2 (warm)
  lead: 81, // Lead 2 (sawtooth)
  guitar: 24, // Acoustic Guitar (nylon)
  drums: 0,
};

function varLen(value: number): number[] {
  const bytes = [value & 0x7f];
  let v = value >> 7;
  while (v > 0) {
    bytes.unshift((v & 0x7f) | 0x80);
    v >>= 7;
  }
  return bytes;
}

function ascii(s: string): number[] {
  return s.split('').map((c) => c.charCodeAt(0));
}

function chunk(type: string, data: number[]): number[] {
  const len = data.length;
  return [
    ...ascii(type),
    (len >>> 24) & 0xff,
    (len >>> 16) & 0xff,
    (len >>> 8) & 0xff,
    len & 0xff,
    ...data,
  ];
}

interface Ev {
  tick: number;
  /** 同一 tick 上的排序权重：元事件 < note off < program < note on */
  order: number;
  data: number[];
}

function buildTrack(name: string, events: Ev[]): number[] {
  const sorted = events.slice().sort((a, b) => a.tick - b.tick || a.order - b.order);
  const out: number[] = [...varLen(0), 0xff, 0x03, ...varLen(name.length), ...ascii(name)];
  let last = 0;
  for (const ev of sorted) {
    const delta = ev.tick - last;
    last = ev.tick;
    out.push(...varLen(delta), ...ev.data);
  }
  out.push(...varLen(0), 0xff, 0x2f, 0x00);
  return chunk('MTrk', out);
}

export function songToMidi(song: Song): Uint8Array {
  const tempoTrack: Ev[] = [];
  const usPerQuarter = Math.round(60000000 / song.tempo);
  tempoTrack.push({
    tick: 0,
    order: 0,
    data: [
      0xff,
      0x51,
      0x03,
      (usPerQuarter >> 16) & 0xff,
      (usPerQuarter >> 8) & 0xff,
      usPerQuarter & 0xff,
    ],
  });
  tempoTrack.push({
    tick: 0,
    order: 0,
    data: [0xff, 0x58, 0x04, 0x04, 0x02, 0x18, 0x08],
  });

  const chunks: number[][] = [buildTrack(`${song.title} - tempo`, tempoTrack)];

  song.tracks.forEach((track, index) => {
    const isDrum = track.kind === 'drums';
    const channel = isDrum ? 9 : Math.min(8, index);
    const evs: Ev[] = [];

    if (!isDrum) {
      evs.push({ tick: 0, order: 1, data: [0xc0 | channel, PROGRAM[track.kind] & 0x7f] });
    }

    for (const clip of track.clips) {
      for (const n of clip.notes) {
        const startTick = Math.round((clip.startBeat + n.start) * TICKS_PER_BEAT);
        const endTick = Math.round((clip.startBeat + n.start + n.dur) * TICKS_PER_BEAT);
        const vel = Math.max(1, Math.min(127, Math.round(n.vel * 127)));
        const pitch = Math.max(0, Math.min(127, Math.round(n.pitch)));
        evs.push({ tick: startTick, order: 2, data: [0x90 | channel, pitch, vel] });
        evs.push({ tick: Math.max(startTick + 1, endTick), order: 1, data: [0x80 | channel, pitch, 0] });
      }
    }

    chunks.push(buildTrack(track.name, evs));
  });

  const header = chunk('MThd', [
    0x00,
    0x01,
    (chunks.length >>> 8) & 0xff,
    chunks.length & 0xff,
    (TICKS_PER_BEAT >>> 8) & 0xff,
    TICKS_PER_BEAT & 0xff,
  ]);

  const bytes: number[] = [...header];
  for (const c of chunks) bytes.push(...c);
  return new Uint8Array(bytes);
}

export function downloadMidi(song: Song): void {
  const bytes = songToMidi(song);
  const blob = new Blob([bytes.buffer as ArrayBuffer], { type: 'audio/midi' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${song.title || 'song'}.mid`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

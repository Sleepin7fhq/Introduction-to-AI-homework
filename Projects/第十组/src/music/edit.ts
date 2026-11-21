import type { Song } from './types';

/**
 * 音符级编辑。
 * 所有函数都返回新的 Song，方便撤销和 React 重渲染。
 */

function withTrack(song: Song, trackId: string, fn: (t: Song['tracks'][number]) => Song['tracks'][number]): Song {
  return { ...song, tracks: song.tracks.map((t) => (t.id === trackId ? fn(t) : t)) };
}

export function noteAtBeat(song: Song, trackId: string, pitch: number, absBeat: number) {
  const track = song.tracks.find((t) => t.id === trackId);
  if (!track) return null;
  for (const clip of track.clips) {
    for (const n of clip.notes) {
      if (n.pitch !== pitch) continue;
      const start = clip.startBeat + n.start;
      if (absBeat >= start - 1e-6 && absBeat < start + n.dur - 1e-6) return { clip, note: n };
    }
  }
  return null;
}

/** 点格子：有音符就删掉，没有就加一个 */
export function toggleNote(song: Song, trackId: string, pitch: number, absBeat: number, dur: number): Song {
  return withTrack(song, trackId, (t) => {
    const clips = t.clips.map((c) => ({ ...c, notes: [...c.notes] }));
    for (const clip of clips) {
      const rel = absBeat - clip.startBeat;
      const idx = clip.notes.findIndex(
        (n) => n.pitch === pitch && rel >= n.start - 1e-6 && rel < n.start + n.dur - 1e-6,
      );
      if (idx >= 0) {
        clip.notes.splice(idx, 1);
        return { ...t, clips };
      }
    }
    let target = clips.find((c) => c.startBeat <= absBeat);
    if (!target) {
      target = { id: `${t.id}-clip-${clips.length}`, startBeat: 0, notes: [] };
      clips.push(target);
    }
    target.notes.push({ pitch, start: absBeat - target.startBeat, dur, vel: 0.8 });
    return { ...t, clips };
  });
}

export function setChordAt(song: Song, index: number, chord: Song['chords'][number]['chord']): Song {
  return {
    ...song,
    chords: song.chords.map((ev, i) => (i === index ? { ...ev, chord } : ev)),
  };
}

export function patchTrack(song: Song, trackId: string, patch: Partial<Song['tracks'][number]>): Song {
  return withTrack(song, trackId, (t) => ({ ...t, ...patch }));
}

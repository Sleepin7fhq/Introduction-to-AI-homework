import { useMemo } from 'react';
import type { CSSProperties } from 'react';
import { NOTE_NAMES } from '../music/theory';
import type { Song, Track } from '../music/types';

const STEPS = 16;

const DRUM_ROWS = [
  { pitch: 36, label: '底鼓' },
  { pitch: 38, label: '军鼓' },
  { pitch: 42, label: '闭镲' },
  { pitch: 46, label: '开镲' },
];

function pitchLabel(p: number): string {
  return NOTE_NAMES[((p % 12) + 12) % 12] + (Math.floor(p / 12) - 1);
}

function noteHitAt(track: Track, pitch: number, beat: number): boolean {
  for (const clip of track.clips) {
    for (const n of clip.notes) {
      if (n.pitch !== pitch) continue;
      const start = clip.startBeat + n.start;
      if (beat >= start - 1e-6 && beat < start + n.dur - 1e-6) return true;
    }
  }
  return false;
}

interface Props {
  song: Song;
  trackId: string;
  bar: number;
  playhead: { bar: number; step: number } | null;
  onToggle: (pitch: number, absBeat: number) => void;
  onSelectTrack: (id: string) => void;
  onBar: (bar: number) => void;
  onToggleMute: (id: string) => void;
}

export function StepEditor({
  song,
  trackId,
  bar,
  playhead,
  onToggle,
  onSelectTrack,
  onBar,
  onToggleMute,
}: Props) {
  const track = song.tracks.find((t) => t.id === trackId) ?? song.tracks[0];
  const isDrum = track.kind === 'drums';

  const rows = useMemo(() => {
    if (isDrum) return DRUM_ROWS;
    const ps = track.clips.flatMap((c) => c.notes.map((n) => n.pitch));
    let lo = ps.length ? Math.min(...ps) : 60;
    let hi = ps.length ? Math.max(...ps) : 72;
    while (hi - lo < 11) {
      lo -= 1;
      hi += 1;
    }
    const out: Array<{ pitch: number; label: string }> = [];
    for (let p = hi; p >= lo; p--) out.push({ pitch: p, label: pitchLabel(p) });
    return out;
  }, [track, isDrum]);

  const gridStyle = { gridTemplateColumns: `46px repeat(${STEPS}, minmax(0, 1fr))` } as CSSProperties;

  return (
    <div className="editor">
      <div className="editor-head">
        <div className="tabs">
          {song.tracks.map((t) => (
            <button
              key={t.id}
              className={`tab ${t.id === track.id ? 'on' : ''} ${t.mute ? 'muted' : ''}`}
              onClick={() => onSelectTrack(t.id)}
            >
              {t.name}
            </button>
          ))}
        </div>
        <div className="bar-nav">
          <button onClick={() => onBar(Math.max(0, bar - 1))} aria-label="上一小节">
            ‹
          </button>
          <span>
            {bar + 1} / {song.bars}
          </span>
          <button onClick={() => onBar(Math.min(song.bars - 1, bar + 1))} aria-label="下一小节">
            ›
          </button>
          <button
            className={`tab-mute ${track.mute ? 'on' : ''}`}
            onClick={() => onToggleMute(track.id)}
          >
            {track.mute ? '静音中' : '出声'}
          </button>
        </div>
      </div>

      <div className="grid">
        <div className="grid-row grid-ruler" style={gridStyle}>
          <span />
          {Array.from({ length: STEPS }, (_, s) => (
            <span key={s} className={`ruler-cell ${s % 4 === 0 ? 'beat' : ''}`}>
              {s % 4 === 0 ? s / 4 + 1 : ''}
            </span>
          ))}
        </div>

        {rows.map((row) => (
          <div className="grid-row" style={gridStyle} key={row.pitch}>
            <span className={`grid-label ${isDrum ? 'drum' : ''}`}>{row.label}</span>
            {Array.from({ length: STEPS }, (_, s) => {
              const abs = bar * 4 + s * 0.25;
              const on = noteHitAt(track, row.pitch, abs);
              const now =
                !!playhead && playhead.bar === bar && playhead.step === s && !track.mute;
              const beatStart = s % 4 === 0;
              return (
                <button
                  key={s}
                  className={`cell ${on ? 'on' : ''} ${now ? 'now' : ''} ${beatStart ? 'beat' : ''}`}
                  onClick={() => onToggle(row.pitch, abs)}
                />
              );
            })}
          </div>
        ))}
      </div>

      <p className="editor-tip">
        点格子加音 / 删音，循环播放时改完下个小节就生效。{isDrum ? '每行是一种鼓。' : ''}
      </p>
    </div>
  );
}

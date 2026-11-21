import { useEffect, useMemo, useRef } from 'react';
import { getPlayer } from '../music/engine';
import { chordLabel } from '../music/theory';
import type { Song, Track } from '../music/types';

const DRUM_ROWS = [36, 38, 39, 42, 46];

interface Props {
  song: Song;
  selected: string | null;
  onSelect: (id: string) => void;
  playing: boolean;
  bar: number;
}

interface NoteBox {
  left: number;
  width: number;
  bottom: number;
  height: number;
  vel: number;
}

function layoutTrack(track: Track, totalBeats: number): NoteBox[] {
  const all = track.clips.flatMap((c) => c.notes.map((n) => ({ ...n, abs: c.startBeat + n.start })));
  if (all.length === 0) return [];
  const isDrum = track.kind === 'drums';
  const lo = isDrum ? 0 : Math.min(...all.map((n) => n.pitch));
  const hi = isDrum ? DRUM_ROWS.length - 1 : Math.max(...all.map((n) => n.pitch));
  const span = Math.max(1, hi - lo);

  return all.map((n) => {
    const row = isDrum ? Math.max(0, DRUM_ROWS.indexOf(n.pitch)) : ((n.pitch - lo) / span) * 100;
    return {
      left: (n.abs / totalBeats) * 100,
      width: Math.max(0.25, (n.dur / totalBeats) * 100),
      bottom: isDrum ? (row / DRUM_ROWS.length) * 100 + 4 : 6 + row * 0.8,
      height: isDrum ? 7 : 5,
      vel: n.vel,
    };
  });
}

export function Timeline({ song, selected, onSelect, playing, bar }: Props) {
  const totalBeats = song.bars * song.meter;
  const headRef = useRef<HTMLDivElement | null>(null);
  const playRef = useRef(playing);
  playRef.current = playing;

  const layouts = useMemo(
    () => new Map(song.tracks.map((t) => [t.id, layoutTrack(t, totalBeats)])),
    [song, totalBeats],
  );

  // 播放头：rAF 直接改 DOM，避免每秒 30 次重渲染整条时间轴
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const el = headRef.current;
      if (el) {
        if (playRef.current) {
          const pos = getPlayer().getPosition();
          const beat = pos.bar * song.meter + Math.min(song.meter - 0.001, getPlayer().getBeatFraction());
          el.style.left = `${(beat / totalBeats) * 100}%`;
          el.classList.add('live');
        } else {
          el.style.left = `${((bar * song.meter) / totalBeats) * 100}%`;
          el.classList.remove('live');
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [song.meter, totalBeats, bar]);

  const barCells = Array.from({ length: song.bars }, (_, i) => i);

  return (
    <section className="timeline">
      <div className="tl-ruler">
        <div className="tl-ruler-cells">
          {barCells.map((b) => (
            <div key={b} className={`ruler-cell ${bar % song.bars === b ? 'now' : ''}`}>
              <span>{b + 1}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="tl-chords">
        <div className="tl-ruler-cells">
          {barCells.map((b) => {
            const ev = song.chords.find((c) => Math.floor(c.startBeat / song.meter) === b);
            return (
              <div key={b} className="chord-cell">
                {ev ? chordLabel(ev.chord) : '—'}
              </div>
            );
          })}
        </div>
      </div>

      <div className="tl-body">
        <div className="tl-lanes">
          <div className="section-strip">
            {song.sections.map((s) => (
              <div
                key={s.id}
                className="section-band"
                style={{
                  left: `${(s.startBar / song.bars) * 100}%`,
                  width: `${(s.bars / song.bars) * 100}%`,
                  opacity: 0.25 + s.energy * 0.45,
                }}
                title={`${s.name} · ${s.bars} 小节`}
              >
                <span>{s.name}</span>
              </div>
            ))}
          </div>

          {song.tracks.map((t) => (
            <div
              key={t.id}
              className={`lane ${selected === t.id ? 'sel' : ''} ${t.mute ? 'muted' : ''}`}
              onClick={() => onSelect(t.id)}
              title={`${t.name} · ${t.clips.reduce((a, c) => a + c.notes.length, 0)} 个音符`}
              role="presentation"
            >
              {layouts.get(t.id)?.map((n, i) => (
                <div
                  key={i}
                  className={`note kind-${t.kind}`}
                  style={{
                    left: `${n.left}%`,
                    width: `${n.width}%`,
                    bottom: `${n.bottom}%`,
                    height: n.height,
                    opacity: 0.45 + n.vel * 0.55,
                  }}
                />
              ))}
            </div>
          ))}

          <div ref={headRef} className="playhead" />
        </div>
      </div>

      <div className="tl-foot">
        <span className="tiny dim">
          {song.bars} 小节 · {song.meter}/4 · {Math.round((song.bars * 4 * 60) / song.tempo)} 秒 · 点击轨道高亮，左侧可静音/调音量
        </span>
        <span className="tiny dim">
          小节 {bar + 1} / {song.bars}
        </span>
      </div>
    </section>
  );
}

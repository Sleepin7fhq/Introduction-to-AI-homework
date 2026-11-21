import type { InstrumentKind, Song } from '../music/types';

export const KIND_LABEL: Record<InstrumentKind, string> = {
  drums: '鼓组',
  bass: '贝斯',
  keys: '和声',
  pad: '铺底',
  lead: '主音',
  guitar: '吉他',
};

interface Props {
  song: Song;
  selected: string | null;
  onSelect: (id: string) => void;
  onPatch: (id: string, patch: { mute?: boolean; gain?: number }) => void;
}

function noteCount(song: Song, id: string): number {
  const t = song.tracks.find((x) => x.id === id);
  if (!t) return 0;
  return t.clips.reduce((a, c) => a + c.notes.length, 0);
}

export function TrackList({ song, selected, onSelect, onPatch }: Props) {
  return (
    <aside className="tracklist">
      <div className="panel-head">
        <span>音轨</span>
        <span className="panel-count">{song.tracks.length}</span>
      </div>

      <div className="track-scroll">
        {song.tracks.map((t) => (
          <div
            key={t.id}
            className={`track-head ${selected === t.id ? 'sel' : ''} ${t.mute ? 'muted' : ''}`}
            onClick={() => onSelect(t.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') onSelect(t.id);
            }}
          >
            <div className="th-row">
              <span className={`kind-dot kind-${t.kind}`} />
              <span className="th-name">{t.name}</span>
              <span className="th-kind">{t.preset ?? KIND_LABEL[t.kind]}</span>
            </div>

            <div className="th-row th-meta">
              <span className="tiny">{noteCount(song, t.id)} notes</span>
              <span className="tiny dim">{KIND_LABEL[t.kind]}</span>
            </div>

            <div className="th-row">
              <button
                className={`mini-btn ${t.mute ? 'on' : ''}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onPatch(t.id, { mute: !t.mute });
                }}
                type="button"
              >
                {t.mute ? 'MUTE' : 'M'}
              </button>
              <input
                className="gain-slider"
                type="range"
                min={0}
                max={1.4}
                step={0.01}
                value={t.gain}
                onClick={(e) => e.stopPropagation()}
                onChange={(e) => onPatch(t.id, { gain: parseFloat(e.target.value) })}
                aria-label={`${t.name} 音量`}
              />
              <span className="tiny gain-val">{Math.round(t.gain * 100)}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="mix-tip">
        <span className="tiny dim">点击轨道查看 · 拖动推子调音量</span>
      </div>
    </aside>
  );
}

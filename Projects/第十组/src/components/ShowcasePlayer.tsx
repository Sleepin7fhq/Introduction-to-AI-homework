import { useEffect, useRef, useState } from 'react';

/**
 * 成品台：把事先用 Suno 做好的歌拖进来，在网页里直接播放。
 *
 * 课堂展示用——不复制、不跳转、不联网，波形和进度都在自己页面里。
 * 这一块不做任何生成，只负责"把自己做过的东西体面地放出来"。
 */

const WAVE_BARS = 120;

/** 上限 200MB */
const MAX_FILE_BYTES = 200 * 1024 * 1024;
/** 超过这个体积就跳过波形解码，只保证能播放——解码 200MB 的音频会吃掉几个 G 内存 */
const WAVE_DECODE_LIMIT = 80 * 1024 * 1024;

function peaksOf(buffer: AudioBuffer, count: number): number[] {
  const data = buffer.getChannelData(0);
  const step = Math.floor(data.length / count) || 1;
  const peaks: number[] = [];
  for (let i = 0; i < count; i++) {
    let peak = 0;
    const start = i * step;
    for (let j = 0; j < step; j += 4) {
      const v = Math.abs(data[start + j] ?? 0);
      if (v > peak) peak = v;
    }
    peaks.push(peak);
  }
  const max = Math.max(...peaks, 0.0001);
  return peaks.map((p) => p / max);
}

export function ShowcasePlayer({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState<string | null>(null);
  const [peaks, setPeaks] = useState<number[]>([]);
  const [url, setUrl] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [url]);

  async function load(file: File) {
    setError(null);
    if (file.size > MAX_FILE_BYTES) {
      setError('文件太大（>200MB），请换小一点的音频');
      return;
    }

    let pk: number[] = [];
    let bufDuration = 0;

    if (file.size <= WAVE_DECODE_LIMIT) {
      try {
        const ctx = new AudioContext();
        const buffer = await ctx.decodeAudioData(await file.arrayBuffer());
        pk = peaksOf(buffer, WAVE_BARS);
        bufDuration = buffer.duration;
        void ctx.close();
      } catch {
        // 解不开就没波形，但播放仍然可用（交给 <audio> 自己处理）
        pk = [];
      }
    }

    if (url) URL.revokeObjectURL(url);
    const objectUrl = URL.createObjectURL(file);
    setPeaks(pk);
    setUrl(objectUrl);
    setName(file.name.replace(/\.[^.]+$/, ''));
    setProgress(0);
    setPlaying(false);
    setDuration(bufDuration);
  }

  function toggle() {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
      setPlaying(false);
    } else {
      void el.play();
      setPlaying(true);
    }
  }

  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal showcase" onClick={(e) => e.stopPropagation()}>
        <header className="modal-head">
          <div>
            <h2>成品台</h2>
            <p>
              把用 Suno 做好的歌拖进来，在这个页面里直接播放。不联网、不跳转、不需要任何插件。
            </p>
          </div>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </header>

        <div className="modal-body">
          {!url && (
            <label
              className="drop-big"
              onDragOver={(e) => {
                e.preventDefault();
                e.currentTarget.classList.add('over');
              }}
              onDragLeave={(e) => e.currentTarget.classList.remove('over')}
              onDrop={(e) => {
                e.preventDefault();
                e.currentTarget.classList.remove('over');
                const f = e.dataTransfer.files?.[0];
                if (f) void load(f);
              }}
            >
              <input
                type="file"
                accept="audio/*"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void load(f);
                  e.target.value = '';
                }}
              />
              <strong>拖入你的成品</strong>
              <span>或者点击选择文件 · mp3 / m4a / wav</span>
            </label>
          )}

          {error && <p className="error">{error}</p>}

          {url && (
            <>
              <div className="showcase-head">
                <div>
                  <strong>{name}</strong>
                  <span>
                    {fmt(progress)} / {fmt(duration)}
                  </span>
                </div>
                <button className="play big" onClick={toggle} aria-label={playing ? '暂停' : '播放'}>
                  {playing ? '❚❚' : '▶'}
                </button>
              </div>

              {peaks.length > 0 ? (
                <div
                  className="wave-big"
                  onClick={(e) => {
                    const el = audioRef.current;
                    if (!el || !duration) return;
                    const rect = e.currentTarget.getBoundingClientRect();
                    const ratio = (e.clientX - rect.left) / rect.width;
                    el.currentTime = Math.max(0, Math.min(duration, ratio * duration));
                  }}
                >
                  {peaks.map((p, i) => {
                    const h = Math.max(4, p * 100);
                    const filled = i / peaks.length <= progress / (duration || 1);
                    return <span key={i} className={filled ? 'on' : ''} style={{ height: `${h}%` }} />;
                  })}
                </div>
              ) : (
                <div
                  className="wave-simple"
                  onClick={(e) => {
                    const el = audioRef.current;
                    if (!el || !duration) return;
                    const rect = e.currentTarget.getBoundingClientRect();
                    const ratio = (e.clientX - rect.left) / rect.width;
                    el.currentTime = Math.max(0, Math.min(duration, ratio * duration));
                  }}
                >
                  <span style={{ width: `${Math.min(100, (progress / (duration || 1)) * 100)}%` }} />
                </div>
              )}

              <div className="showcase-foot">
                <label className="ghost-btn tiny file-replace">
                  <input
                    type="file"
                    accept="audio/*"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) void load(f);
                      e.target.value = '';
                    }}
                  />
                  换一首
                </label>
                <span className="tool-meta">点击波形可以跳转</span>
              </div>

              <audio
                ref={audioRef}
                src={url}
                onLoadedMetadata={(e) => {
                  if (!duration && Number.isFinite(e.currentTarget.duration)) {
                    setDuration(e.currentTarget.duration);
                  }
                }}
                onTimeUpdate={(e) => setProgress(e.currentTarget.currentTime)}
                onEnded={() => setPlaying(false)}
                onPlay={() => setPlaying(true)}
                onPause={() => setPlaying(false)}
              />
            </>
          )}

          <p className="tool-note">
            成品需要在有网的环境里用 Suno 提前生成并下载。演示时只做播放，不会出现复制或跳转。
          </p>
        </div>
      </div>
    </div>
  );
}

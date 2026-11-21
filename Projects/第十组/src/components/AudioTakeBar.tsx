import type { AudioTake } from '../engine/backends';

interface Props {
  take: AudioTake;
  backendLabel: string;
}

/**
 * ACE-Step 生成的是音频，没有 MIDI 结构。
 * 这里就老老实实展示一段音频：不把它伪装成"可编辑的谱面"。
 */
export function AudioTakeBar({ take, backendLabel }: Props) {
  return (
    <div className="audio-take">
      <div className="at-head">
        <span className="at-badge">AI 音频</span>
        <span className="at-src">{backendLabel}</span>
        <span className="tiny dim">{take.durationSec}s · {take.mime}</span>
      </div>
      <audio className="at-player" controls src={take.url} preload="metadata" />
      <p className="tiny dim">
        本条由本机模型直接生成音频，没有对应的音符数据，因此时间轴不可编辑——这是真实限制，不做粉饰。
      </p>
    </div>
  );
}

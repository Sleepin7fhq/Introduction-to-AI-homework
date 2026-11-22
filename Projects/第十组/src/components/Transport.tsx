import { useEffect, useRef } from 'react';
import { getPlayer } from '../music/engine';
import { Scope } from './Scope';

interface Props {
  playing: boolean;
  bar: number;
  bpm: number;
  bars: number;
  onPlay: () => void;
  onStop: () => void;
  onBpm: (v: number) => void;
  hasSong: boolean;
  audioBlocked: boolean;
}

export function Transport({
  playing,
  bar,
  bpm,
  bars,
  onPlay,
  onStop,
  onBpm,
  hasSong,
  audioBlocked,
}: Props) {
  const meterRef = useRef<HTMLDivElement | null>(null);
  const barRef = useRef<HTMLSpanElement | null>(null);
  const beatRef = useRef<HTMLSpanElement | null>(null);
  const playRef = useRef(playing);
  playRef.current = playing;
  const barProp = useRef(bar);
  barProp.current = bar;

  // 一个 rAF 同时驱动：总表电量 + 位置读数（小节/拍）
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const meter = meterRef.current;
      const barEl = barRef.current;
      const beatEl = beatRef.current;

      if (playRef.current) {
        const p = getPlayer();
        const level = p.getLevel();
        if (meter) meter.style.transform = `scaleX(${Math.max(0.02, Math.min(1, level * 1.15))})`;
        const pos = p.getPosition();
        if (barEl) barEl.textContent = String(pos.bar + 1).padStart(2, '0');
        // 拍号按 1..4 滚动，而不是显示一个占位的圆点
        if (beatEl) beatEl.textContent = String(Math.floor(p.getBeatFraction()) + 1);
      } else {
        if (meter) meter.style.transform = 'scaleX(0.02)';
        if (barEl) barEl.textContent = String(barProp.current + 1).padStart(2, '0');
        if (beatEl) beatEl.textContent = '1';
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <footer className="transport">
      <div className="tp-group">
        <button
          className={`transport-btn play ${playing ? 'on' : ''}`}
          onClick={onPlay}
          disabled={!hasSong}
          type="button"
          title="播放 / 停止（循环）"
        >
          {playing ? '❚❚' : '▶'}
        </button>
        <button className="transport-btn stop" onClick={onStop} disabled={!hasSong} type="button" title="停止">
          ■
        </button>
      </div>

      <div className="tp-group tp-pos">
        <span className="tiny dim">位置</span>
        <span className="pos-readout">
          <span ref={barRef}>{String(bar + 1).padStart(2, '0')}</span>
          <span className="pos-sep">.</span>
          <span ref={beatRef}>1</span>
        </span>
        <span className="tiny dim">/ {bars}</span>
      </div>

      <div className="tp-group">
        <span className="tiny dim">BPM</span>
        <button className="step-btn" onClick={() => onBpm(Math.max(60, bpm - 1))} type="button">
          −
        </button>
        <span className="bpm-readout">{bpm}</span>
        <button className="step-btn" onClick={() => onBpm(Math.min(190, bpm + 1))} type="button">
          +
        </button>
      </div>

      <div className="tp-group">
        <span className="tiny dim">小节</span>
        <span className="bpm-readout small">{bars}</span>
      </div>

      <div className="tp-scope">
        <span className="scope-label">MASTER OUT · 实时波形</span>
        <Scope active={playing} />
      </div>

      <div className="tp-master">
        <span className="tiny dim">MASTER</span>
        <div className="meter">
          <div className="meter-fill" ref={meterRef} />
        </div>
      </div>

      {audioBlocked && <div className="tp-warn">浏览器要求先点一下页面才允许出声</div>}
    </footer>
  );
}

import { useEffect, useRef } from 'react';
import { getPlayer } from '../music/engine';

/**
 * 示波器。
 * 画的是 limiter 之后真正送往声卡的波形（Tone.Analyser 抽头），不是假动画。
 */
export function Scope({ active }: { active: boolean }) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const activeRef = useRef(active);
  activeRef.current = active;

  useEffect(() => {
    let raf = 0;
    const draw = () => {
      const canvas = ref.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        const cssW = canvas.clientWidth;
        const cssH = canvas.clientHeight;
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        if (ctx && cssW > 0 && cssH > 0) {
          if (canvas.width !== Math.round(cssW * dpr) || canvas.height !== Math.round(cssH * dpr)) {
            canvas.width = Math.round(cssW * dpr);
            canvas.height = Math.round(cssH * dpr);
          }
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
          ctx.clearRect(0, 0, cssW, cssH);

          // 中线
          ctx.strokeStyle = 'rgba(120, 160, 210, 0.16)';
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(0, cssH / 2);
          ctx.lineTo(cssW, cssH / 2);
          ctx.stroke();

          const data = activeRef.current ? getPlayer().getWaveform() : null;
          const n = data ? data.length : 0;

          if (data && n > 1) {
            let peak = 0;
            for (let i = 0; i < n; i++) peak = Math.max(peak, Math.abs(data[i]));

            const grad = ctx.createLinearGradient(0, 0, 0, cssH);
            grad.addColorStop(0, 'rgba(94, 234, 212, 0.95)');
            grad.addColorStop(0.5, 'rgba(56, 189, 248, 0.9)');
            grad.addColorStop(1, 'rgba(129, 140, 248, 0.9)');
            ctx.strokeStyle = grad;
            ctx.lineWidth = 1.6;
            ctx.beginPath();
            const step = Math.max(1, Math.floor(n / cssW));
            for (let x = 0; x < cssW; x++) {
              const i = Math.min(n - 1, Math.floor((x / cssW) * n) + step);
              const v = data[i] ?? 0;
              const y = cssH / 2 - v * (cssH / 2) * 0.92;
              if (x === 0) ctx.moveTo(x, y);
              else ctx.lineTo(x, y);
            }
            ctx.stroke();

            // 峰值刻度
            ctx.fillStyle = 'rgba(148, 163, 184, 0.55)';
            ctx.font = '9px ui-monospace, monospace';
            ctx.fillText(`${(20 * Math.log10(Math.max(peak, 1e-4))).toFixed(1)} dB`, 4, 11);
          } else {
            ctx.strokeStyle = 'rgba(94, 234, 212, 0.28)';
            ctx.lineWidth = 1.4;
            ctx.beginPath();
            for (let x = 0; x < cssW; x++) {
              const y = cssH / 2 + Math.sin(x * 0.06) * 1.2;
              if (x === 0) ctx.moveTo(x, y);
              else ctx.lineTo(x, y);
            }
            ctx.stroke();
          }
        }
      }
      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, []);

  return <canvas ref={ref} className="scope" aria-label="主输出波形" />;
}

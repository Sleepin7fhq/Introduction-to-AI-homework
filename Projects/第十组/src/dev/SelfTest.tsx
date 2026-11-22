import { useEffect, useState } from 'react';
import { analyzeFile } from '../audio/analyze';
import { getPlayer } from '../music/engine';
import { songToMidi } from '../music/export';
import { composeSong } from '../music/generate';

/**
 * 彩排自检页（?selftest=1）。
 * 把"不点一下根本不知道会不会坏"的链路都跑一遍：
 * 音频上下文、参考曲目解码分析、生成、MIDI 导出、播放引擎。
 */

interface Result {
  name: string;
  ok: boolean;
  detail: string;
}

/** 造一段已知内容的 WAV：A 小调三和弦 + 100 BPM 的打击点 */
function makeTestWav(sampleRate = 11025, seconds = 12): ArrayBuffer {
  const n = Math.floor(sampleRate * seconds);
  const data = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / sampleRate;
    data[i] =
      0.12 *
      (Math.sin(2 * Math.PI * 220 * t) +
        Math.sin(2 * Math.PI * 261.63 * t) +
        Math.sin(2 * Math.PI * 329.63 * t));
  }
  const step = 60 / 100;
  for (let k = 0; k * step < seconds; k++) {
    const start = Math.floor(k * step * sampleRate);
    for (let j = 0; j < 300 && start + j < n; j++) {
      data[start + j] += 0.5 * Math.exp(-j / 60) * (Math.random() * 2 - 1);
    }
  }

  const buffer = new ArrayBuffer(44 + n * 2);
  const view = new DataView(buffer);
  const writeStr = (off: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i));
  };
  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + n * 2, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, 'data');
  view.setUint32(40, n * 2, true);
  for (let i = 0; i < n; i++) {
    const v = Math.max(-1, Math.min(1, data[i]));
    view.setInt16(44 + i * 2, Math.round(v * 0x7fff), true);
  }
  return buffer;
}

export function SelfTest() {
  const [results, setResults] = useState<Result[]>([]);
  const [running, setRunning] = useState(true);

  async function run() {
    setRunning(true);
    const out: Result[] = [];

    const push = (name: string, ok: boolean, detail: string) => {
      out.push({ name, ok, detail });
      setResults([...out]);
    };

    // 1. 音频上下文
    try {
      const ctx = new AudioContext();
      push('音频上下文', true, `state=${ctx.state} rate=${ctx.sampleRate}`);
      void ctx.close();
    } catch (e) {
      push('音频上下文', false, String(e));
    }

    // 2. 参考曲目：合成 WAV → 解码 → 分析
    try {
      const wav = makeTestWav();
      const file = new File([wav], 'selftest.wav', { type: 'audio/wav' });
      const t0 = performance.now();
      const res = await analyzeFile(file);
      const ms = Math.round(performance.now() - t0);
      const bpmOk = Math.abs(res.core.bpm - 100) <= 4;
      const keyOk = res.core.key.tonic === 9 && res.core.key.mode === 'minor';
      push(
        '参考曲目分析',
        bpmOk && keyOk,
        `bpm=${res.core.bpm}${bpmOk ? '' : ' ✗期望100'} key=${res.core.key.tonic}${
          res.core.key.mode === 'minor' ? 'm' : ''
        }${keyOk ? '' : ' ✗期望A小调'} 耗时${ms}ms`,
      );
    } catch (e) {
      push('参考曲目分析', false, String(e));
    }

    // 3. 生成
    let song = null as ReturnType<typeof composeSong> | null;
    try {
      song = composeSong('下雨的深夜，一个人走在回家的路上');
      const notes = song.tracks.reduce(
        (a, t) => a + t.clips.reduce((b, c) => b + c.notes.length, 0),
        0,
      );
      push('文字生成', song.chords.length === 8 && notes > 40, `${song.tracks.length} 轨 / ${notes} 音符`);
    } catch (e) {
      push('文字生成', false, String(e));
    }

    // 4. MIDI 导出
    if (song) {
      try {
        const bytes = songToMidi(song);
        const head = String.fromCharCode(...bytes.slice(0, 4));
        push('MIDI 导出', head === 'MThd' && bytes.length > 200, `${bytes.length} 字节, 头=${head}`);
      } catch (e) {
        push('MIDI 导出', false, String(e));
      }
    }

    // 5. 播放引擎（需要音频权限，失败通常是因为没点过页面）
    try {
      const player = getPlayer();
      if (song) {
        player.setSong(song);
        await Promise.race([player.play(), new Promise((r) => setTimeout(r, 2000))]);
        await new Promise((r) => setTimeout(r, 600));
        const playing = player.isPlaying;
        const pos = player.getPosition();
        player.stop();
        push(
          '播放引擎',
          playing,
          playing
            ? `已开播，位置 bar=${pos.bar} step=${pos.step}`
            : '音频未启动：浏览器要求用户手势，先点一下页面再测',
        );
      }
    } catch (e) {
      push('播放引擎', false, String(e));
    }

    setRunning(false);
  }

  useEffect(() => {
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const allOk = results.length > 0 && results.every((r) => r.ok);

  return (
    <div className="selftest">
      <h1>彩排自检</h1>
      <p className="st-sub">把最容易在现场出问题的链路都跑一遍。全绿即可放心演示。</p>
      <ul>
        {results.map((r) => (
          <li key={r.name} className={r.ok ? 'ok' : 'bad'}>
            <span className="st-mark">{r.ok ? '✓' : '✗'}</span>
            <span className="st-name">{r.name}</span>
            <span className="st-detail">{r.detail}</span>
          </li>
        ))}
        {running && <li className="pending">运行中…</li>}
      </ul>
      <div className={`st-summary ${allOk ? 'ok' : 'bad'}`}>
        {running ? '检查中' : allOk ? 'ALL PASS' : 'FAIL'}
      </div>
      {results.some((r) => !r.ok && r.name === '播放引擎') && (
        <p className="st-hint">「播放引擎」没通过通常不是坏了——浏览器要求用户手势才允许出声，点一下下面的按钮再测一次。</p>
      )}
      <button onClick={() => void run()} disabled={running}>
        重新检查
      </button>
    </div>
  );
}

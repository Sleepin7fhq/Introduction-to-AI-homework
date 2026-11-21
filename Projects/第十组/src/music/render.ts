import * as Tone from 'tone';
import type { Song } from './types';
import { createVoice } from './engine';
import { ensureSamplesLoaded, getBank, setActiveKit } from '../audio/sampler';

/**
 * 离线渲染：把 Song 用同一套音色一次性渲染成 WAV。
 *
 * 复用 createVoice，所以导出的声音和实时播放一致——这是「改前/改后」对比的基础，
 * 也是生成试听样本的唯一途径（浏览器实时播放没法直接得到文件）。
 */
export async function renderSongToWav(song: Song): Promise<Blob> {
  const secPerBeat = 60 / song.tempo;
  const tail = 2.5;
  const duration = (song.bars * song.meter + 2) * secPerBeat + tail;
  const sampleRate = 48000;

  setActiveKit(song.soundKit as never);

  const rendered = await Tone.Offline(
    async () => {
      await ensureSamplesLoaded();
      await getBank().prepare(Tone.getContext().rawContext as unknown as BaseAudioContext);
      // 与实时引擎一致的主链路：总线 → 胶水压缩 → 限幅 → 输出
      const limiter = new Tone.Limiter(-1).toDestination();
      const comp = new Tone.Compressor({
        threshold: -18,
        ratio: 2.5,
        attack: 0.02,
        release: 0.25,
        knee: 12,
      }).connect(limiter);
      const eq = new Tone.EQ3({ low: 2, mid: 0, high: 1.5, lowFrequency: 200, highFrequency: 3200 }).connect(comp);
      const bus = new Tone.Gain(0.9).connect(eq);
      const reverb = new Tone.Reverb({ decay: 2.4, preDelay: 0.015, wet: 0.26 }).connect(comp);
      await reverb.generate();

      for (const track of song.tracks) {
        if (track.mute) continue;
        const voice = createVoice(track, bus, reverb);
        // 必须按时间升序触发：Tone 的合成器不接受回退的调度时间
        const events: Array<{ time: number; pitch: number; dur: number; vel: number }> = [];
        for (const clip of track.clips) {
          for (const n of clip.notes) {
            const time = (clip.startBeat + n.start) * secPerBeat;
            if (time > duration - 0.1) continue;
            events.push({ time, pitch: n.pitch, dur: Math.max(0.06, n.dur * secPerBeat), vel: n.vel });
          }
        }
        events.sort((a, b) => a.time - b.time);
        for (const e of events) voice.trigger(e.pitch, e.dur, e.time, e.vel);
      }
    },
    duration,
    2,
    sampleRate,
  );

  return audioBufferToWavBlob(rendered.get() as AudioBuffer);
}

/** Float32 AudioBuffer → 16bit PCM WAV */
export function audioBufferToWavBlob(buffer: AudioBuffer): Blob {
  const channels = Math.min(2, buffer.numberOfChannels);
  const frames = buffer.length;
  const bytesPerSample = 2;
  const blockAlign = channels * bytesPerSample;
  const dataSize = frames * blockAlign;
  const out = new ArrayBuffer(44 + dataSize);
  const view = new DataView(out);

  const writeStr = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i));
  };

  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, channels, true);
  view.setUint32(24, buffer.sampleRate, true);
  view.setUint32(28, buffer.sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true);
  writeStr(36, 'data');
  view.setUint32(40, dataSize, true);

  const chans: Float32Array[] = [];
  for (let c = 0; c < channels; c++) chans.push(buffer.getChannelData(c));

  let offset = 44;
  for (let i = 0; i < frames; i++) {
    for (let c = 0; c < channels; c++) {
      let s = chans[c][i];
      s = Math.max(-1, Math.min(1, s));
      // 轻微软削波，避免整数溢出时的硬爆音
      if (s > 0.98 || s < -0.98) s = Math.tanh(s * 1.4) * 0.98;
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      offset += 2;
    }
  }

  return new Blob([out], { type: 'audio/wav' });
}

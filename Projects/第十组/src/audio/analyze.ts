import type { Key, Mode, StyleProfile } from '../music/types';
import { NOTE_NAMES } from '../music/theory';

/**
 * 参考曲目的声学分析。
 *
 * 全部在浏览器里算，不上传、不联网。
 * 目标是给出「可读、可改、可复现」的风格参数，而不是黑箱 embedding。
 */

const TARGET_SR = 11025;
const MAX_SECONDS = 60;
const FRAME = 2048;
const HOP = 256;
const HALF = FRAME / 2;
const HANN = new Float32Array(FRAME).map((_, i) => 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (FRAME - 1)));

/** Krumhansl-Kessler 调性感知轮廓 */
const KK_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88];
const KK_MINOR = [6.33, 2.68, 3.52, 5.38, 2.6, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17];

function fftInPlace(re: Float32Array, im: Float32Array): void {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      const tr = re[i];
      re[i] = re[j];
      re[j] = tr;
      const ti = im[i];
      im[i] = im[j];
      im[j] = ti;
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len;
    const wr = Math.cos(ang);
    const wi = Math.sin(ang);
    const half = len >> 1;
    for (let i = 0; i < n; i += len) {
      let cr = 1;
      let ci = 0;
      for (let k = 0; k < half; k++) {
        const a = i + k;
        const b = a + half;
        const vr = re[b] * cr - im[b] * ci;
        const vi = re[b] * ci + im[b] * cr;
        const ur = re[a];
        const ui = im[a];
        re[a] = ur + vr;
        im[a] = ui + vi;
        re[b] = ur - vr;
        im[b] = ui - vi;
        const ncr = cr * wr - ci * wi;
        ci = cr * wi + ci * wr;
        cr = ncr;
      }
    }
  }
}

function pearson(a: number[], b: number[]): number {
  const n = a.length;
  let sa = 0;
  let sb = 0;
  for (let i = 0; i < n; i++) {
    sa += a[i];
    sb += b[i];
  }
  const ma = sa / n;
  const mb = sb / n;
  let num = 0;
  let da = 0;
  let db = 0;
  for (let i = 0; i < n; i++) {
    const x = a[i] - ma;
    const y = b[i] - mb;
    num += x * y;
    da += x * x;
    db += y * y;
  }
  if (da === 0 || db === 0) return 0;
  return num / Math.sqrt(da * db);
}

export interface CoreAnalysis {
  bpm: number;
  key: Key;
  brightness: number;
  density: number;
  groove: number;
  tension: number;
  dynamics: number;
  peaks: number[];
  duration: number;
}

export function analyzeSamples(data: Float32Array, sampleRate: number): CoreAnalysis {
  const nFrames = Math.max(1, Math.floor((data.length - FRAME) / HOP) + 1);
  const rms = new Float32Array(nFrames);
  const flux = new Float32Array(nFrames);
  const centroid = new Float32Array(nFrames);
  const chroma = new Array<number>(12).fill(0);
  let flatnessSum = 0;
  let centroidSum = 0;
  let centroidWeight = 0;

  const re = new Float32Array(FRAME);
  const im = new Float32Array(FRAME);
  const mag = new Float32Array(HALF);
  let prev = new Float32Array(HALF);

  const binHz = sampleRate / FRAME;

  for (let f = 0; f < nFrames; f++) {
    const off = f * HOP;
    let energy = 0;
    for (let i = 0; i < FRAME; i++) {
      const v = (data[off + i] ?? 0) * HANN[i];
      re[i] = v;
      im[i] = 0;
      energy += v * v;
    }
    rms[f] = Math.sqrt(energy / FRAME);
    fftInPlace(re, im);

    let magSum = 0;
    let fluxSum = 0;
    let centroidNum = 0;
    let logSum = 0;
    let flatCount = 0;

    for (let k = 1; k < HALF; k++) {
      const m = Math.sqrt(re[k] * re[k] + im[k] * im[k]);
      mag[k] = m;
      magSum += m;
      const d = m - prev[k];
      if (d > 0) fluxSum += d;
      centroidNum += m * k * binHz;
      if (m > 1e-6) {
        logSum += Math.log(m);
        flatCount++;
      }
    }
    prev.set(mag);

    flux[f] = fluxSum;
    centroid[f] = magSum > 1e-9 ? centroidNum / magSum : 0;
    if (magSum > 1e-6 && flatCount > 0) {
      flatnessSum += Math.exp(logSum / flatCount) / (magSum / HALF);
    }
    if (magSum > 1e-3) {
      centroidSum += centroid[f] * magSum;
      centroidWeight += magSum;
    }

    // 音级能量：只统计有能量的帧
    if (rms[f] > 0.004) {
      for (let k = 1; k < HALF; k++) {
        const m = mag[k];
        if (m < 1e-5) continue;
        const freq = k * binHz;
        if (freq < 55 || freq > 2200) continue;
        const midi = 69 + 12 * Math.log2(freq / 440);
        const pc = ((Math.round(midi) % 12) + 12) % 12;
        chroma[pc] += m;
      }
    }
  }

  const duration = data.length / sampleRate;
  const meanRms = rms.reduce((a, b) => a + b, 0) / nFrames;
  let varRms = 0;
  for (let i = 0; i < nFrames; i++) varRms += (rms[i] - meanRms) ** 2;
  const stdRms = Math.sqrt(varRms / nFrames);

  /* ---- 调性 ---- */
  let bestCorr = -Infinity;
  let bestKey: Key = { tonic: 0, mode: 'major' };
  for (const mode of ['major', 'minor'] as Mode[]) {
    const profile = mode === 'major' ? KK_MAJOR : KK_MINOR;
    for (let rot = 0; rot < 12; rot++) {
      const rotated: number[] = [];
      for (let i = 0; i < 12; i++) rotated.push(chroma[(i + rot) % 12]);
      const c = pearson(rotated, profile);
      if (c > bestCorr) {
        bestCorr = c;
        bestKey = { tonic: rot, mode };
      }
    }
  }

  /* ---- 速度 ---- */
  const framesPerSec = sampleRate / HOP;
  const onset = new Float32Array(nFrames);
  let onsetMean = 0;
  for (let i = 0; i < nFrames; i++) {
    onset[i] = Math.max(0, flux[i] - (i > 0 ? flux[i - 1] : 0));
    onsetMean += onset[i];
  }
  onsetMean /= nFrames;
  for (let i = 0; i < nFrames; i++) onset[i] = Math.max(0, onset[i] - onsetMean);

  const minLag = Math.max(4, Math.floor((framesPerSec * 60) / 190));
  const maxLag = Math.min(nFrames - 1, Math.ceil((framesPerSec * 60) / 55));
  const scores = new Float32Array(maxLag + 2);
  for (let lag = minLag; lag <= maxLag; lag++) {
    let s = 0;
    for (let i = 0; i + lag < nFrames; i++) s += onset[i] * onset[i + lag];
    scores[lag] = s;
  }

  let bestLag = minLag;
  let bestScore = -Infinity;
  for (let lag = minLag; lag <= maxLag; lag++) {
    const bpm = (framesPerSec * 60) / lag;
    // 偏好 75-150 的常见速度区间，避免被倍频带走
    const pref = Math.exp(-0.5 * (Math.log2(bpm / 105) / 0.75) ** 2);
    const score = scores[lag] * (0.55 + 0.45 * pref);
    if (score > bestScore) {
      bestScore = score;
      bestLag = lag;
    }
  }

  // 半速歧义：140 的曲子也强相关于 70 的周期，优先取听感上的基本拍
  let applied = bestLag;
  for (let guard = 0; guard < 2; guard++) {
    const bpmNow = (framesPerSec * 60) / applied;
    if (bpmNow >= 80) break;
    const fast = Math.round(applied / 2);
    if (fast < minLag || scores[fast] < 0.5 * scores[applied]) break;
    applied = fast;
  }

  // 抛物线插值细化
  let refined = applied;
  if (applied > minLag && applied < maxLag) {
    const y0 = scores[applied - 1];
    const y1 = scores[applied];
    const y2 = scores[applied + 1];
    const denom = 2 * (2 * y1 - y0 - y2);
    if (Math.abs(denom) > 1e-9) refined = applied + (y2 - y0) / denom;
  }
  const bpmRaw = (framesPerSec * 60) / refined;
  const bpm = Math.round(bpmRaw * 2) / 2;

  /* ---- 起音密度 ---- */
  const onsetStd = Math.sqrt(onset.reduce((a, b) => a + b * b, 0) / nFrames);
  const threshold = onsetMean + onsetStd * 0.7;
  let onsets = 0;
  let lastOnset = -10;
  for (let i = 0; i < nFrames; i++) {
    if (onset[i] > threshold && i - lastOnset > 3) {
      onsets++;
      lastOnset = i;
    }
  }
  const onsetRate = onsets / Math.max(1, duration);

  /* ---- 归一化到 0-1 ---- */
  const avgCentroid = centroidWeight > 0 ? centroidSum / centroidWeight : 1200;
  const brightness = Math.min(1, Math.max(0, avgCentroid / 2600));
  const density = Math.min(1, Math.max(0, onsetRate / 6.5));
  const groove = Math.min(1, Math.max(0, 0.25 + onsetStd / (onsetMean + 1e-6) / 6));
  const dynamics = Math.min(1, Math.max(0, (stdRms / (meanRms + 1e-6)) * 1.6));
  const flatness = flatnessSum / Math.max(1, nFrames);
  const tension = Math.min(
    1,
    Math.max(0, 0.18 + (bestKey.mode === 'minor' ? 0.16 : 0) + Math.min(0.5, flatness * 1.4)),
  );

  /* ---- 波形缩略 ---- */
  const buckets = 72;
  const peaks: number[] = [];
  const per = Math.floor(data.length / buckets) || 1;
  for (let b = 0; b < buckets; b++) {
    let peak = 0;
    for (let i = 0; i < per; i++) {
      const v = Math.abs(data[b * per + i] ?? 0);
      if (v > peak) peak = v;
    }
    peaks.push(peak);
  }

  return {
    bpm: Number.isFinite(bpm) && bpm > 0 ? bpm : 90,
    key: bestKey,
    brightness,
    density,
    groove,
    tension,
    dynamics,
    peaks,
    duration,
  };
}

/**
 * 受版权保护的加密容器。
 * 这些格式的音频被 DRM 加密，浏览器（以及任何播放器）在没有解密密钥时都无法解码。
 * 我们不做解密——那是绕过版权保护。这里只负责给出明确的提示，而不是一句"解不开"。
 */
const DRM_EXTENSIONS: Record<string, string> = {
  ncm: '网易云音乐',
  qmc: 'QQ音乐',
  mflac: 'QQ音乐',
  mgg: 'QQ音乐',
  kgm: '酷狗音乐',
  kwm: '酷我音乐',
};

function drmHint(file: File): string | null {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
  const vendor = DRM_EXTENSIONS[ext];
  if (!vendor) return null;
  return `这是${vendor}会员下载的加密格式（.${ext}），受版权保护，网页端无法解析。请换成未加密的 mp3 / flac / wav。`;
}

export interface ReferenceResult {
  core: CoreAnalysis;
  profile: StyleProfile;
}

function describe(core: CoreAnalysis): string[] {
  const tags: string[] = [];
  tags.push(`${core.bpm} BPM`);
  tags.push(`${NOTE_NAMES[core.key.tonic]} ${core.key.mode === 'major' ? '大调' : '小调'}`);
  if (core.brightness > 0.62) tags.push('明亮');
  else if (core.brightness < 0.38) tags.push('暗色');
  if (core.density > 0.62) tags.push('编曲密');
  else if (core.density < 0.34) tags.push('留白多');
  if (core.groove > 0.66) tags.push('律动强');
  return tags;
}

const MAX_FILE_BYTES = 200 * 1024 * 1024;

export async function analyzeFile(file: File): Promise<ReferenceResult> {
  if (file.size > MAX_FILE_BYTES) throw new Error('文件太大，请换 200MB 以内的音频');

  const blocked = drmHint(file);
  if (blocked) throw new Error(blocked);

  const buf = await file.arrayBuffer();
  // 改了扩展名的加密文件也拦一下：NCM 的魔数是 CTENFDAM
  const head = new Uint8Array(buf.slice(0, 8));
  if (String.fromCharCode(...head) === 'CTENFDAM') {
    throw new Error('这是加密格式（.ncm），受版权保护，网页端无法解析。请换成未加密的 mp3 / flac / wav。');
  }

  const ctx = new AudioContext();
  let decoded: AudioBuffer;
  try {
    decoded = await ctx.decodeAudioData(buf);
  } catch {
    void ctx.close();
    throw new Error('这个文件解不开：可能是加密格式或文件损坏。支持 mp3 / flac / wav / m4a / ogg。');
  }
  void ctx.close();

  const seconds = Math.min(decoded.duration, MAX_SECONDS);
  const offline = new OfflineAudioContext(1, Math.ceil(seconds * TARGET_SR), TARGET_SR);
  const src = offline.createBufferSource();
  src.buffer = decoded;
  src.connect(offline.destination);
  src.start(0);
  const rendered = await offline.startRendering();
  const data = rendered.getChannelData(0);

  const core = analyzeSamples(data, TARGET_SR);
  core.duration = decoded.duration;

  const profile: StyleProfile = {
    name: file.name.replace(/\.[^.]+$/, '').slice(0, 18) || '参考曲目',
    brightness: core.brightness,
    density: core.density,
    groove: core.groove,
    tension: core.tension,
    dynamics: core.dynamics,
    bpm: core.bpm,
    tags: describe(core),
  };

  return { core, profile };
}

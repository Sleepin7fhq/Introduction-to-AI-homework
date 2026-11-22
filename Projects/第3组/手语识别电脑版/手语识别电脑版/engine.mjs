/**
 * engine.mjs — 特征提取 + K 近邻判别
 * 纯计算模块，不依赖 DOM。采样与实时识别必须共用这里的同一套特征处理。
 */

// ---------- 可调参数（可在网页面板里修改，会保存到 localStorage） ----------
export const DEFAULT_PARAMS = Object.freeze({
  k: 3, // 每类取最近的 k 个样本求平均距离
  rejectThreshold: 0.45, // 候选类的平均距离超过该值 → 未识别（越大越宽松）
  marginRatio: 1.12, // 前两类平均距离之比小于该值 → 太接近 → 未识别（越大越严格）
  stableFrames: 3, // 连续 N 帧结果一致才更新显示（减少抖动）
  minSamplesPerClass: 3, // 每类至少多少样本才开始识别
});

export const STATE = Object.freeze({
  WAITING: '等待样本',
  NO_HAND: '未检测到手',
  UNKNOWN: '未识别',
});

/** 手腕索引在 MediaPipe 21 点中是 0；用 0→9（中指 MCP）的距离作尺度基准 */
const WRIST = 0;
const SCALE_REF = 9;
const EPS = 1e-6;

/**
 * 从 21 个关键点提取 42 维特征。
 * @param {Array<{x:number,y:number,z?:number}>} landmarks
 * @returns {number[]|null} 42 维向量；无效输入返回 null
 */
export function extractFeature(landmarks) {
  if (!Array.isArray(landmarks) || landmarks.length < 21) return null;
  for (let i = 0; i < 21; i++) {
    const p = landmarks[i];
    if (!p || !Number.isFinite(p.x) || !Number.isFinite(p.y)) return null;
  }
  const wrist = landmarks[WRIST];
  const ref = landmarks[SCALE_REF];
  const dx = ref.x - wrist.x;
  const dy = ref.y - wrist.y;
  const scale = Math.sqrt(dx * dx + dy * dy);
  if (scale < EPS) return null; // 手太小/退化，避免除零

  const feat = new Array(42);
  for (let i = 0; i < 21; i++) {
    feat[i * 2] = (landmarks[i].x - wrist.x) / scale;
    feat[i * 2 + 1] = (landmarks[i].y - wrist.y) / scale;
  }
  // 防 NaN
  for (let i = 0; i < 42; i++) if (!Number.isFinite(feat[i])) return null;
  return feat;
}

/** 欧氏距离 */
export function distance(a, b) {
  if (!a || !b || a.length !== b.length) return Infinity;
  let s = 0;
  for (let i = 0; i < a.length; i++) {
    const d = a[i] - b[i];
    s += d * d;
  }
  return Math.sqrt(s);
}

/**
 * 判断样本库是否已就绪：至少两类、且每类样本数 >= minSamplesPerClass。
 * 规格要求“每类至少采集 3 个样本后自动开始识别”，三类都达标才就绪。
 */
export function isReady(classes, params) {
  if (!Array.isArray(classes) || classes.length < 3) return false;
  const min = params.minSamplesPerClass ?? DEFAULT_PARAMS.minSamplesPerClass;
  return classes.slice(0, 3).every((c) => Array.isArray(c.samples) && c.samples.length >= min);
}

/**
 * 分类。
 * @param {number[]} feature 当前 42 维特征
 * @param {Array<{name:string,samples:number[][]}>} classes
 * @param {object} params
 * @returns {{state:string,label:string|null,scores:Array<{name:string,avg:number}>,bestAvg:number,ratio:number}}
 */
export function classify(feature, classes, params = DEFAULT_PARAMS) {
  const p = { ...DEFAULT_PARAMS, ...params };
  const scores = [];
  const valid = (classes || []).filter((c) => c && Array.isArray(c.samples) && c.samples.length > 0);
  for (const c of valid) {
    const dists = c.samples
      .map((s) => distance(feature, s))
      .filter((d) => Number.isFinite(d))
      .sort((a, b) => a - b);
    if (!dists.length) continue;
    const take = dists.slice(0, Math.max(1, p.k));
    const avg = take.reduce((s, d) => s + d, 0) / take.length;
    scores.push({ name: c.name || '未命名', avg });
  }
  scores.sort((a, b) => a.avg - b.avg);

  if (scores.length < 2) {
    return { state: STATE.UNKNOWN, label: null, scores, bestAvg: Infinity, ratio: Infinity };
  }

  const best = scores[0];
  const second = scores[1];
  const bestAvg = best.avg;
  const ratio = bestAvg > EPS ? second.avg / bestAvg : Infinity;

  // 拒识：绝对距离过大，或前两类距离太接近
  if (bestAvg > p.rejectThreshold || ratio < p.marginRatio) {
    return { state: STATE.UNKNOWN, label: null, scores, bestAvg, ratio };
  }
  return { state: 'ok', label: best.name, scores, bestAvg, ratio };
}

/**
 * 时序平滑器：连续 stableFrames 帧结果一致才输出，否则保持上一次稳定值。
 */
export class Stabilizer {
  constructor(frames = DEFAULT_PARAMS.stableFrames) {
    this.frames = Math.max(1, frames | 0);
    this.candidate = null;
    this.count = 0;
    this.output = null;
  }
  setFrames(n) {
    this.frames = Math.max(1, n | 0);
    this.reset();
  }
  reset() {
    this.candidate = null;
    this.count = 0;
    this.output = null;
  }
  /** @returns {string|null} 稳定后的结果标签（可能为 STATE.UNKNOWN） */
  push(label) {
    if (label !== this.candidate) {
      this.candidate = label;
      this.count = 1;
    } else {
      this.count++;
    }
    if (this.count >= this.frames) this.output = label;
    return this.output;
  }
}

/** 样本库结构校验（导入时用） */
export function validateLibrary(obj) {
  if (!obj || typeof obj !== 'object') return null;
  const classes = obj.classes;
  if (!Array.isArray(classes) || classes.length !== 3) return null;
  const clean = classes.map((c, i) => {
    const name = typeof c.name === 'string' && c.name.trim() ? c.name.trim() : `手势 ${i + 1}`;
    const samples = Array.isArray(c.samples)
      ? c.samples.filter((s) => Array.isArray(s) && s.length === 42 && s.every((v) => Number.isFinite(v)))
      : [];
    return { name, samples };
  });
  return { version: 1, classes: clean };
}

export function emptyLibrary() {
  return {
    version: 1,
    classes: [
      { name: '手势 1', samples: [] },
      { name: '手势 2', samples: [] },
      { name: '手势 3', samples: [] },
    ],
  };
}

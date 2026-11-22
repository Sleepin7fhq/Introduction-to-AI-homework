/**
 * sequence_engine.mjs — 手语骨架序列采集引擎
 *
 * 与 engine.mjs（单帧静态手势 KNN）互补：本模块面向「时序手语动作」，
 * 采集连续帧的手部 21 点关键点，形成「骨架序列」，作为时序模型的训练样本。
 *
 * 样本结构：
 *   {
 *     label: string,          // 手语词标签（如「你好」「感谢」）
 *     signer: string,         // 采集者标识（可选，用于按人划分训练/测试）
 *     view: 'front',          // 视角（默认 front）
 *     frames: number,         // 帧数
 *     sequence: number[][],   // 每帧 42 维特征 [x0,y0,x1,y1,...,x20,y20]（归一化后）
 *   }
 *
 * 归一化与 engine.mjs 的 extractFeature 保持一致：手腕为原点，除以手腕→中指根距离。
 * 这样静态手势样本与序列帧特征同源，后续可混合使用。
 */

// ---------- 常量 ----------
const WRIST = 0;
const SCALE_REF = 9;
const EPS = 1e-6;

/** 默认采集参数 */
export const SEQ_DEFAULT = Object.freeze({
  seqLen: 30,        // 期望序列帧数（不足补齐，超出截断）
  minFrames: 5,      // 最少帧数，低于此值不保存
  sampleRate: 30,    // 目标采样率（fps），实际按真实帧间隔
});

/**
 * 单帧关键点 -> 42 维归一化特征（与 engine.mjs extractFeature 完全一致）。
 * @param {Array<{x,y,z?}>} landmarks MediaPipe 21 点
 * @returns {number[]|null}
 */
export function frameFeature(landmarks) {
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
  if (scale < EPS) return null;

  const feat = new Array(42);
  for (let i = 0; i < 21; i++) {
    feat[i * 2] = (landmarks[i].x - wrist.x) / scale;
    feat[i * 2 + 1] = (landmarks[i].y - wrist.y) / scale;
  }
  for (let i = 0; i < 42; i++) if (!Number.isFinite(feat[i])) return null;
  return feat;
}

/**
 * 序列缓冲器：录制时逐帧追加特征，结束时产出规范化的定长序列。
 */
export class SequenceRecorder {
  constructor(seqLen = SEQ_DEFAULT.seqLen) {
    this.seqLen = seqLen;
    this.buffer = [];
    this.recording = false;
  }
  start() {
    this.buffer = [];
    this.recording = true;
  }
  /** 录制中追加一帧特征；无效帧忽略 */
  push(feature) {
    if (!this.recording || !feature) return;
    this.buffer.push(feature);
  }
  stop() {
    this.recording = false;
    return this.finish();
  }
  cancel() {
    this.recording = false;
    this.buffer = [];
  }
  get count() {
    return this.buffer.length;
  }
  /**
   * 归一化到定长 seqLen：
   *  - 帧数不足：重复最后一帧补齐
   *  - 帧数超出：均匀采样截断
   */
  finish() {
    const seq = this.buffer;
    if (seq.length < SEQ_DEFAULT.minFrames) return null;
    const out = [];
    if (seq.length >= this.seqLen) {
      // 均匀采样
      for (let i = 0; i < this.seqLen; i++) {
        const idx = Math.floor((i * (seq.length - 1)) / (this.seqLen - 1));
        out.push(seq[idx].slice());
      }
    } else {
      for (let i = 0; i < seq.length; i++) out.push(seq[i].slice());
      const last = seq[seq.length - 1];
      while (out.length < this.seqLen) out.push(last.slice());
    }
    return out;
  }
}

/**
 * 构建一条完整样本。
 */
export function buildSample(label, sequence, extra = {}) {
  return {
    label,
    signer: extra.signer || 'unknown',
    view: extra.view || 'front',
    frames: sequence.length,
    sequence,
  };
}

/**
 * 校验导入的序列样本库。
 * @param {object} obj
 * @returns {object|null}
 */
export function validateSeqLibrary(obj) {
  if (!obj || typeof obj !== 'object') return null;
  const samples = obj.samples;
  if (!Array.isArray(samples)) return null;
  const clean = [];
  for (const s of samples) {
    if (!s || typeof s.label !== 'string' || !s.label.trim()) continue;
    const seq = Array.isArray(s.sequence)
      ? s.sequence.filter((f) => Array.isArray(f) && f.length === 42 && f.every((v) => Number.isFinite(v)))
      : [];
    if (seq.length < SEQ_DEFAULT.minFrames) continue;
    clean.push({
      label: s.label.trim(),
      signer: typeof s.signer === 'string' ? s.signer : 'unknown',
      view: typeof s.view === 'string' ? s.view : 'front',
      frames: seq.length,
      sequence: seq,
    });
  }
  return { version: 1, samples: clean };
}

export function emptySeqLibrary() {
  return { version: 1, samples: [] };
}

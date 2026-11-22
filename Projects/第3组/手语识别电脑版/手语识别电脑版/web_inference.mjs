/**
 * web_inference.mjs — 网页端手语识别推理引擎（纯 JS，零依赖）
 *
 * 加载 scripts/export_web.py 导出的 sign_model_web.json（TCN V1，已做 BN 融合），
 * 在浏览器本地完成「骨架序列 -> 203 词概率」的前向推理。
 *
 * 模型结构：输入 (42, 30) = 21 关键点 × (x,y) × 30 帧
 *   -> 3 层 TemporalBlock(Conv1d + ReLU + Conv1d + 残差 + ReLU, dilation 1/2/4)
 *   -> 时间维全局平均池化 -> Linear(128 -> 203)
 *
 * 特征归一化与 sequence_engine.mjs 的 frameFeature 完全一致：
 *   手腕(0)为原点，除以手腕→中指MCP(9)距离。
 */

const IN_CH = 42;   // 21 点 × 2 坐标
const SEQ_LEN = 30;

let model = null;   // 已解析的模型对象（Float32Array 权重）

/** 加载模型 JSON（fetch），并预转换为 Float32Array 以便快速推理 */
export async function loadModel(url = './sign_model_web.json') {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error('模型文件加载失败: ' + resp.status);
  const raw = await resp.json();
  model = {
    labels: raw.labels,
    seqLen: raw.seq_len,
    layers: raw.layers.map((l) => ({
      dilation: l.dilation,
      conv1_w: toF32(l.conv1_w), conv1_b: toF32(l.conv1_b),
      conv2_w: toF32(l.conv2_w), conv2_b: toF32(l.conv2_b),
      down_w: l.down_w ? toF32(l.down_w) : null,
      down_b: l.down_b ? toF32(l.down_b) : null,
    })),
    fc_w: toF32(raw.fc_w),
    fc_b: toF32(raw.fc_b),
  };
  return model;
}

function toF32(arr) {
  // 递归展平任意维度数组（权重可能是三维 [outC][inC][K] 或二维/一维）
  const flat = [];
  (function walk(a) {
    if (Array.isArray(a)) { for (const v of a) walk(v); }
    else flat.push(a);
  })(arr);
  return new Float32Array(flat);
}

export function isLoaded() { return !!model; }
export function getLabels() { return model ? model.labels : []; }

/**
 * 从 21 个 MediaPipe 关键点提取 42 维归一化特征。
 * @param {Array<{x:number,y:number}>} landmarks
 * @returns {Float32Array|null} 42 维特征
 */
export function landmarksToFeature(landmarks) {
  if (!landmarks || landmarks.length < 21) return null;
  const wrist = landmarks[0];
  const ref = landmarks[9];
  const dx = ref.x - wrist.x, dy = ref.y - wrist.y;
  const scale = Math.sqrt(dx * dx + dy * dy);
  if (scale < 1e-6) return null;
  const feat = new Float32Array(42);
  for (let i = 0; i < 21; i++) {
    feat[i * 2] = (landmarks[i].x - wrist.x) / scale;
    feat[i * 2 + 1] = (landmarks[i].y - wrist.y) / scale;
  }
  return feat;
}

/** 一维卷积（zero padding），x 为 (C_in × T) 平铺 */
function conv1d(x, w, b, outC, inC, T, dilation, K = 3) {
  const pad = ((K - 1) * dilation) >> 1;
  const out = new Float32Array(outC * T);
  for (let o = 0; o < outC; o++) {
    const bias = b[o];
    const wBase = o * inC * K;
    for (let t = 0; t < T; t++) {
      let s = bias;
      for (let ci = 0; ci < inC; ci++) {
        const xBase = ci * T;
        const wRow = wBase + ci * K;
        for (let k = 0; k < K; k++) {
          const xi = t + (k - 1) * dilation; // 卷积核中心对齐（k=1 对应当前 t）
          if (xi >= 0 && xi < T) {
            s += w[wRow + k] * x[xBase + xi];
          }
        }
      }
      out[o * T + t] = s;
    }
  }
  return out;
}

/** 逐元素 ReLU（原地） */
function reluInPlace(a) {
  for (let i = 0; i < a.length; i++) if (a[i] < 0) a[i] = 0;
  return a;
}

/**
 * 前向推理：骨架序列 -> 各类别 logits（未归一化）。
 * @param {Float32Array} seq 42×30 平铺（或 42×N，N 任意，内部按 SEQ_LEN 采样）
 * @returns {Float32Array} 203 维 logits
 */
export function infer(seq) {
  if (!model) throw new Error('模型未加载');
  // 若帧数不等于 30，做均匀采样/补齐（与训练一致）
  let x = resampleToSeqLen(seq);

  for (const layer of model.layers) {
    const d = layer.dilation;
    // 第一层 in=42（有 downsample），其余 in=128
    const isFirst = layer.down_w !== null;
    const curInC = isFirst ? 42 : 128;

    const o1 = reluInPlace(conv1d(x, layer.conv1_w, layer.conv1_b, 128, curInC, SEQ_LEN, d));
    const o2 = conv1d(o1, layer.conv2_w, layer.conv2_b, 128, 128, SEQ_LEN, d);
    const res = isFirst
      ? conv1d(x, layer.down_w, layer.down_b, 128, 42, SEQ_LEN, 1, 1)  // downsample 是 1×1 卷积
      : x;
    for (let i = 0; i < o2.length; i++) o2[i] += res[i];
    x = reluInPlace(o2);
  }

  // 全局平均池化（时间维）：每通道 30 个值取平均 -> 128
  const pooled = new Float32Array(128);
  for (let c = 0; c < 128; c++) {
    let s = 0;
    const base = c * SEQ_LEN;
    for (let t = 0; t < SEQ_LEN; t++) s += x[base + t];
    pooled[c] = s / SEQ_LEN;
  }

  // Linear: fc_w (203 × 128)
  const numClasses = model.fc_b.length;
  const logits = new Float32Array(numClasses);
  for (let o = 0; o < numClasses; o++) {
    let s = model.fc_b[o];
    const wBase = o * 128;
    for (let i = 0; i < 128; i++) s += model.fc_w[wBase + i] * pooled[i];
    logits[o] = s;
  }
  return logits;
}

/** 把任意长度序列 (42×N 平铺) 均匀采样/补齐到 42×30 */
function resampleToSeqLen(seq) {
  // seq 平铺格式：42 通道 × N 帧
  const ch = 42;
  const N = seq.length / ch;
  if (N === SEQ_LEN) return new Float32Array(seq);
  const out = new Float32Array(ch * SEQ_LEN);
  for (let c = 0; c < ch; c++) {
    const srcBase = c * N;
    const dstBase = c * SEQ_LEN;
    for (let t = 0; t < SEQ_LEN; t++) {
      const idx = Math.min(N - 1, Math.floor((t * (N - 1)) / (SEQ_LEN - 1)));
      out[dstBase + t] = seq[srcBase + idx];
    }
  }
  return out;
}

/** softmax */
export function softmax(logits) {
  let mx = -Infinity;
  for (let i = 0; i < logits.length; i++) if (logits[i] > mx) mx = logits[i];
  const exp = new Float32Array(logits.length);
  let sum = 0;
  for (let i = 0; i < logits.length; i++) { exp[i] = Math.exp(logits[i] - mx); sum += exp[i]; }
  for (let i = 0; i < logits.length; i++) exp[i] /= sum;
  return exp;
}

/**
 * 把一条序列样本（sequence: 每帧 42 维数组）转成平铺 Float32Array (42×N)。
 * 供直接对「采集器导出的样本」做推理。
 */
export function sequenceToFlat(sequence) {
  const N = sequence.length;
  const flat = new Float32Array(42 * N);
  for (let t = 0; t < N; t++) {
    const frame = sequence[t];
    for (let c = 0; c < 42; c++) flat[c * N + t] = frame[c];
  }
  return flat;
}

/**
 * 便捷：对一条样本预测 Top-K 词。
 * @returns {Array<{label:string, prob:number}>}
 */
export function predictTopK(sequence, k = 5) {
  const flat = sequenceToFlat(sequence);
  const logits = infer(flat);
  const probs = softmax(logits);
  const idx = Array.from(probs.keys()).sort((a, b) => probs[b] - probs[a]).slice(0, k);
  return idx.map((i) => ({ label: model.labels[i], prob: probs[i] }));
}

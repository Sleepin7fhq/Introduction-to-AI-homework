import { FilesetResolver, HandLandmarker } from './vendor/vision_bundle.mjs';
import {
  DEFAULT_PARAMS, STATE, extractFeature, isReady, classify,
  Stabilizer, validateLibrary, emptyLibrary,
} from './engine.mjs';

// ---------------- DOM ----------------
const $ = (id) => document.getElementById(id);
const video = $('video');
const overlay = $('overlay');
const ctx = overlay.getContext('2d');
const placeholder = $('videoPlaceholder');
const seek = $('seek');
const camHint = $('camHint');
const resultEl = $('result');
const readyBadge = $('readyBadge');
const handBadge = $('handBadge');
const diagEl = $('diag');
const modelStatus = $('modelStatus');

let handLandmarker = null;
let stream = null;
let library = emptyLibrary();
let params = { ...DEFAULT_PARAMS };
let stabilizer = new Stabilizer(params.stableFrames);
let lastVideoTime = -1;
let lastResultLabel = null;
let mediaSource = 'none'; // 'camera' | 'file' | 'none'
let fileObjectUrl = null;

// 手掌骨架连线（MediaPipe 标准 21 点连接）
const CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,4],
  [0,5],[5,6],[6,7],[7,8],
  [5,9],[9,10],[10,11],[11,12],
  [9,13],[13,14],[14,15],[15,16],
  [13,17],[17,18],[18,19],[19,20],[0,17],
];

// ---------------- 持久化 ----------------
const LS_LIBRARY = 'handshape-lab.library.v1';
const LS_PARAMS = 'handshape-lab.params.v1';

function loadLocal() {
  try {
    const libRaw = localStorage.getItem(LS_LIBRARY);
    if (libRaw) {
      const parsed = validateLibrary(JSON.parse(libRaw));
      if (parsed) library = parsed;
    }
    const pRaw = localStorage.getItem(LS_PARAMS);
    if (pRaw) {
      const p = JSON.parse(pRaw);
      params = { ...DEFAULT_PARAMS, ...sanitizeParams(p) };
    }
  } catch (e) { console.warn('读取本地数据失败', e); }
}
function saveLibrary() {
  try { localStorage.setItem(LS_LIBRARY, JSON.stringify(library)); } catch (e) {}
}
function saveParams() {
  try { localStorage.setItem(LS_PARAMS, JSON.stringify(params)); } catch (e) {}
}
function sanitizeParams(p) {
  return {
    k: clampInt(p.k, 1, 10, DEFAULT_PARAMS.k),
    rejectThreshold: clampNum(p.rejectThreshold, 0.05, 2, DEFAULT_PARAMS.rejectThreshold),
    marginRatio: clampNum(p.marginRatio, 1, 3, DEFAULT_PARAMS.marginRatio),
    stableFrames: clampInt(p.stableFrames, 1, 15, DEFAULT_PARAMS.stableFrames),
    minSamplesPerClass: DEFAULT_PARAMS.minSamplesPerClass,
  };
}
const clampNum = (v, a, b, d) => (Number.isFinite(+v) ? Math.min(b, Math.max(a, +v)) : d);
const clampInt = (v, a, b, d) => Math.round(clampNum(v, a, b, d));

// ---------------- 模型加载 ----------------
async function initModel() {
  try {
    modelStatus.textContent = '模型加载中…';
    modelStatus.className = 'status-pill status-loading';
    const vision = await FilesetResolver.forVisionTasks('./vendor/wasm');
    handLandmarker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: { modelAssetPath: './vendor/hand_landmarker.task', delegate: 'GPU' },
      runningMode: 'VIDEO',
      numHands: 1,
    });
    modelStatus.textContent = '模型就绪';
    modelStatus.className = 'status-pill status-ready';
  } catch (e) {
    console.error(e);
    // GPU 失败时回退 CPU
    try {
      const vision = await FilesetResolver.forVisionTasks('./vendor/wasm');
      handLandmarker = await HandLandmarker.createFromOptions(vision, {
        baseOptions: { modelAssetPath: './vendor/hand_landmarker.task', delegate: 'CPU' },
        runningMode: 'VIDEO', numHands: 1,
      });
      modelStatus.textContent = '模型就绪(CPU)';
      modelStatus.className = 'status-pill status-ready';
    } catch (e2) {
      console.error(e2);
      modelStatus.textContent = '模型加载失败';
      modelStatus.className = 'status-pill status-error';
      camHint.hidden = false;
      camHint.textContent = '模型加载失败，请确认通过本地服务器（http://localhost）或 HTTPS 打开页面，且 vendor/ 目录完整。';
    }
  }
}

// ---------------- 摄像头 / 视频 ----------------
async function startCamera() {
  camHint.hidden = true;
  if (!navigator.mediaDevices?.getUserMedia) {
    showCamError('当前环境不支持摄像头，请改用「打开视频」演示，或确认用 HTTPS / localhost 打开。');
    return;
  }
  try {
    stopAllMedia();
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 960 } },
      audio: false,
    });
    mediaSource = 'camera';
    video.controls = false;
    seek.hidden = true;
    video.srcObject = stream;
    video.hidden = false;
    placeholder.hidden = true;
    await video.play();
  } catch (e) {
    console.warn(e);
    showCamError('无法访问摄像头：可能被拒绝授权或设备被占用。请在浏览器地址栏允许摄像头权限；若仍不行，请点「打开视频」用本地视频继续演示。');
  }
}

function showCamError(msg) {
  camHint.hidden = false;
  camHint.textContent = msg;
  placeholder.hidden = false;
  resultEl.textContent = STATE.NO_HAND;
  resultEl.className = 'result result-no-hand';
}

function stopAllMedia() {
  if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
  try { video.pause(); } catch (e) {}
  video.srcObject = null;
  if (fileObjectUrl) { URL.revokeObjectURL(fileObjectUrl); fileObjectUrl = null; }
  video.removeAttribute('src');
  video.load();
  seek.hidden = true;
  lastVideoTime = -1;
  mediaSource = 'none';
  clearOverlay();
  stabilizer.reset();
  lastResultLabel = null;
  setResult(STATE.NO_HAND);
}

function openVideoFile(file) {
  if (!file) return;
  stopAllMedia();
  mediaSource = 'file';
  fileObjectUrl = URL.createObjectURL(file);
  video.srcObject = null;
  video.src = fileObjectUrl;
  video.controls = true;      // 原生控制条：可拖动、暂停
  seek.hidden = false;        // 自定义进度条同步显示
  video.hidden = false;
  placeholder.hidden = true;
  camHint.hidden = true;
  video.onloadedmetadata = () => {
    seek.max = 1000;
    seek.value = 0;
    video.currentTime = 0;
    video.play().then(() => video.pause()).catch(() => {}); // 停在第一帧便于取样
  };
}

seek.addEventListener('input', () => {
  if (mediaSource === 'file' && video.duration) {
    video.currentTime = (seek.value / 1000) * video.duration;
  }
});
video.addEventListener('timeupdate', () => {
  if (mediaSource === 'file' && video.duration) {
    seek.value = Math.round((video.currentTime / video.duration) * 1000);
  }
});

// ---------------- 检测循环 ----------------
function loop() {
  requestAnimationFrame(loop);
  if (!handLandmarker) return;
  const src = video;
  if (!src || src.readyState < 2 || !src.videoWidth) return;

  let landmarks = null;
  try {
    // 仅在画面前进时检测，避免对同一帧重复推理
    if (src.currentTime !== lastVideoTime) {
      lastVideoTime = src.currentTime;
      const res = handLandmarker.detectForVideo(src, performance.now());
      landmarks = res?.landmarks?.[0] || null;
    } else {
      // 同一帧：沿用上一次的关键点来维持显示
      landmarks = lastLandmarks;
    }
  } catch (e) {
    // detectForVideo 在视频暂停时偶发报错，忽略
  }

  lastLandmarks = landmarks;
  drawOverlay(src, landmarks);

  if (!landmarks || landmarks.length < 21) {
    handBadge.textContent = '未检测到手';
    handBadge.className = 'mini-badge';
    if (lastResultLabel !== STATE.NO_HAND) {
      lastResultLabel = STATE.NO_HAND;
      stabilizer.reset();
      setResult(STATE.NO_HAND);
    }
    diagEl.textContent = '—';
    return;
  }

  handBadge.textContent = '检测到手';
  handBadge.className = 'mini-badge mini-ok';

  const feat = extractFeature(landmarks);
  if (!feat) return;

  if (!isReady(library.classes, params)) {
    if (lastResultLabel !== STATE.WAITING) {
      lastResultLabel = STATE.WAITING;
      stabilizer.reset();
      setResult(STATE.WAITING);
    }
    diagEl.textContent = describeSamples();
    return;
  }

  const out = classify(feat, library.classes, params);
  const stable = stabilizer.push(out.state === 'ok' ? out.label : STATE.UNKNOWN);
  if (stable && stable !== lastResultLabel) {
    lastResultLabel = stable;
    setResult(stable === STATE.UNKNOWN ? STATE.UNKNOWN : stable);
  }
  diagEl.textContent =
    describeScores(out) + '\n' +
    `候选距离=${out.bestAvg.toFixed(3)}  类间比=${out.ratio.toFixed(3)}\n` +
    `拒识阈值=${params.rejectThreshold}  区分比=${params.marginRatio}`;
}
let lastLandmarks = null;

function setResult(label) {
  resultEl.textContent = label;
  if (label === STATE.WAITING || label === STATE.NO_HAND) resultEl.className = 'result result-idle' + (label === STATE.NO_HAND ? ' result-no-hand' : '');
  else if (label === STATE.UNKNOWN) resultEl.className = 'result result-unknown';
  else resultEl.className = 'result result-ok';
}
function describeScores(out) {
  if (!out.scores?.length) return '—';
  return out.scores.map((s) => `${s.name}: ${s.avg.toFixed(3)}`).join('\n');
}
function describeSamples() {
  return library.classes.map((c) => `${c.name}: ${c.samples.length} 个样本`).join('\n');
}

// ---------------- 叠加绘制 ----------------
function drawOverlay(src, landmarks) {
  const w = overlay.clientWidth || src.clientWidth;
  const h = overlay.clientHeight || src.clientHeight;
  if (overlay.width !== w || overlay.height !== h) {
    overlay.width = w; overlay.height = h;
  }
  ctx.clearRect(0, 0, w, h);
  if (!landmarks) return;

  // object-fit: contain 下，视频画面在显示框内居中缩放，需按真实绘制矩形映射关键点
  const vw = src.videoWidth, vh = src.videoHeight;
  const scale = Math.min(w / vw, h / vh);
  const dw = vw * scale, dh = vh * scale;
  const ox = (w - dw) / 2, oy = (h - dh) / 2;
  const px = (p) => ox + p.x * dw;
  const py = (p) => oy + p.y * dh;

  ctx.strokeStyle = 'rgba(168,230,163,0.9)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (const [a, b] of CONNECTIONS) {
    const p1 = landmarks[a], p2 = landmarks[b];
    if (!p1 || !p2) continue;
    ctx.moveTo(px(p1), py(p1));
    ctx.lineTo(px(p2), py(p2));
  }
  ctx.stroke();
  ctx.fillStyle = '#a8e6a3';
  for (const p of landmarks) {
    ctx.beginPath();
    ctx.arc(px(p), py(p), 3, 0, Math.PI * 2);
    ctx.fill();
  }
}
function clearOverlay() {
  ctx.clearRect(0, 0, overlay.width, overlay.height);
}

// ---------------- 采样控件 ----------------
function renderClassRows() {
  const wrap = $('classRows');
  wrap.innerHTML = '';
  library.classes.forEach((c, i) => {
    const row = document.createElement('div');
    row.className = 'class-row';
    row.innerHTML = `
      <input class="class-name" data-i="${i}" value="${escapeAttr(c.name)}" aria-label="类别 ${i + 1} 名称" />
      <span class="count-badge" data-count="${i}">${c.samples.length} 个</span>
      <button class="btn row-btn" data-act="collect" data-i="${i}">采集</button>
      <button class="btn btn-ghost row-btn" data-act="clear" data-i="${i}">清空</button>
    `;
    wrap.appendChild(row);
  });

  wrap.querySelectorAll('.class-name').forEach((inp) => {
    inp.addEventListener('change', (e) => {
      const i = +e.target.dataset.i;
      library.classes[i].name = e.target.value.trim() || `手势 ${i + 1}`;
      e.target.value = library.classes[i].name;
      saveLibrary();
      refreshReady();
    });
  });
  wrap.querySelectorAll('button[data-act]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const i = +btn.dataset.i;
      if (btn.dataset.act === 'collect') collect(i);
      else clearClass(i);
    });
  });
}

function escapeAttr(s) {
  return String(s).replace(/"/g, '&quot;').replace(/</g, '&lt;');
}

function collect(i) {
  const lm = lastLandmarks;
  if (!lm || lm.length < 21) {
    alert('未检测到完整手部关键点，未保存样本。请让手完整出现在画面中再采集。');
    return;
  }
  const feat = extractFeature(lm);
  if (!feat) {
    alert('当前手势无法提取有效特征，未保存。请调整手势或光照后重试。');
    return;
  }
  library.classes[i].samples.push(feat);
  saveLibrary();
  refreshCounts();
  refreshReady();
  flashButton(i);
}

function clearClass(i) {
  library.classes[i].samples = [];
  saveLibrary();
  refreshCounts();
  refreshReady();
  stabilizer.reset();
  lastResultLabel = null;
  setResult(isReady(library.classes, params) ? lastResultLabel || STATE.UNKNOWN : STATE.WAITING);
}

function refreshCounts() {
  library.classes.forEach((c, i) => {
    const el = document.querySelector(`[data-count="${i}"]`);
    if (el) el.textContent = `${c.samples.length} 个`;
  });
  diagEl.textContent = describeSamples();
}
function refreshReady() {
  const ready = isReady(library.classes, params);
  readyBadge.textContent = ready ? '已就绪' : '未就绪';
  readyBadge.className = 'mini-badge' + (ready ? ' mini-ok' : ' mini-idle');
  if (!ready && lastResultLabel !== STATE.WAITING && lastResultLabel !== STATE.NO_HAND) {
    lastResultLabel = STATE.WAITING;
    stabilizer.reset();
    setResult(STATE.WAITING);
  }
}
function flashButton(i) {
  const btn = document.querySelector(`button[data-act="collect"][data-i="${i}"]`);
  if (!btn) return;
  const old = btn.textContent;
  btn.textContent = '已保存 ✓';
  btn.style.borderColor = 'var(--accent)';
  setTimeout(() => { btn.textContent = old; btn.style.borderColor = ''; }, 700);
}

// ---------------- 导入 / 导出 ----------------
function exportSamples() {
  const data = JSON.stringify(library, null, 2);
  const blob = new Blob([data], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const stamp = new Date().toISOString().slice(0, 10);
  a.href = url;
  a.download = `samples-${stamp}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function importSamples(file) {
  if (!file) return;
  try {
    const text = await file.text();
    const parsed = validateLibrary(JSON.parse(text));
    if (!parsed) throw new Error('格式不符');
    library = parsed;
    saveLibrary();
    renderClassRows();
    refreshCounts();
    refreshReady();
    stabilizer.reset();
    lastResultLabel = null;
    alert(`导入成功：${library.classes.map((c) => `${c.name} ${c.samples.length}个`).join('，')}`);
  } catch (e) {
    alert('导入失败：JSON 格式不符合样本库要求（需含 classes，每类 name 与 42 维 samples）。');
  }
}

// ---------------- 参数面板 ----------------
function bindParams() {
  $('paramK').value = params.k;
  $('paramReject').value = params.rejectThreshold;
  $('paramMargin').value = params.marginRatio;
  $('paramStable').value = params.stableFrames;

  const onChange = () => {
    params = sanitizeParams({
      k: $('paramK').value,
      rejectThreshold: $('paramReject').value,
      marginRatio: $('paramMargin').value,
      stableFrames: $('paramStable').value,
    });
    stabilizer.setFrames(params.stableFrames);
    saveParams();
    refreshReady();
  };
  ['paramK', 'paramReject', 'paramMargin', 'paramStable'].forEach((id) => {
    $(id).addEventListener('change', onChange);
  });
  $('btnParamReset').addEventListener('click', () => {
    params = { ...DEFAULT_PARAMS };
    saveParams();
    bindParams();
    stabilizer.setFrames(params.stableFrames);
  });
}

// ---------------- 事件绑定 ----------------
$('btnStartCam').addEventListener('click', startCamera);
$('btnStopCam').addEventListener('click', () => {
  stopAllMedia();
  placeholder.hidden = false;
  resultEl.textContent = STATE.WAITING;
  resultEl.className = 'result result-idle';
});
$('fileVideo').addEventListener('change', (e) => { openVideoFile(e.target.files[0]); e.target.value = ''; });
// 统一用 JS 显式触发文件选择，避免 label/for + hidden input 在个别环境的兼容问题
document.querySelectorAll('label[for]').forEach((lbl) => {
  const target = $(lbl.getAttribute('for'));
  if (!target || target.type !== 'file') return;
  lbl.addEventListener('click', (e) => {
    e.preventDefault();
    target.click();
  });
});
$('btnExport').addEventListener('click', exportSamples);
$('fileImport').addEventListener('change', (e) => {
  importSamples(e.target.files[0]);
  e.target.value = '';
});
$('btnReset').addEventListener('click', () => {
  if (!confirm('确定清空全部三个类别的样本？此操作不可撤销。')) return;
  library = emptyLibrary();
  saveLibrary();
  renderClassRows();
  refreshCounts();
  refreshReady();
});

// ---------------- 启动 ----------------
loadLocal();
renderClassRows();
refreshCounts();
refreshReady();
bindParams();
setResult(isReady(library.classes, params) ? STATE.NO_HAND : STATE.WAITING);
initModel();
requestAnimationFrame(loop);

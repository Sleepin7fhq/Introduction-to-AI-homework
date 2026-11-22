import { FilesetResolver, HandLandmarker } from './vendor/vision_bundle.mjs';
import {
  SEQ_DEFAULT, frameFeature, SequenceRecorder, buildSample,
  validateSeqLibrary, emptySeqLibrary,
} from './sequence_engine.mjs';

// ---------------- DOM ----------------
const $ = (id) => document.getElementById(id);
const video = $('video');
const overlay = $('overlay');
const ctx = overlay.getContext('2d');
const placeholder = $('videoPlaceholder');
const camHint = $('camHint');
const modelStatus = $('modelStatus');
const recordBtn = $('btnRecord');
const recordStatus = $('recordStatus');
const recordFrames = $('recordFrames');
const wordSelect = $('wordSelect');
const wordList = $('wordList');
const signerInput = $('signerInput');
const seqLenInput = $('seqLenInput');
const sampleSummary = $('sampleSummary');
const sampleList = $('sampleList');
const vocabStatus = $('vocabStatus');

// ---------------- 状态 ----------------
let handLandmarker = null;
let stream = null;
let mediaSource = 'none';
let fileObjectUrl = null;
let lastVideoTime = -1;
let lastLandmarks = null;
let library = emptySeqLibrary();
let recorder = new SequenceRecorder(SEQ_DEFAULT.seqLen);
let wordSet = new Set(); // 词表（从 label_map.json 加载）

// 手掌骨架连线
const CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,4],
  [0,5],[5,6],[6,7],[7,8],
  [5,9],[9,10],[10,11],[11,12],
  [9,13],[13,14],[14,15],[15,16],
  [13,17],[17,18],[18,19],[19,20],[0,17],
];

// ---------------- 持久化 ----------------
const LS_SEQ = 'csl-collector.library.v1';

function loadLocal() {
  try {
    const raw = localStorage.getItem(LS_SEQ);
    if (raw) {
      const parsed = validateSeqLibrary(JSON.parse(raw));
      if (parsed) library = parsed;
    }
  } catch (e) { console.warn('读取本地样本失败', e); }
}
function saveLibrary() {
  try { localStorage.setItem(LS_SEQ, JSON.stringify(library)); } catch (e) {}
}

// ---------------- 模型加载 ----------------
async function initModel() {
  try {
    modelStatus.textContent = '模型加载中…';
    modelStatus.className = 'status-pill status-loading';
    const vision = await FilesetResolver.forVisionTasks('./vendor/wasm');
    handLandmarker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: { modelAssetPath: './vendor/hand_landmarker.task', delegate: 'GPU' },
      runningMode: 'VIDEO', numHands: 1,
    });
    modelStatus.textContent = '模型就绪';
    modelStatus.className = 'status-pill status-ready';
  } catch (e) {
    console.error(e);
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
      camHint.textContent = '模型加载失败，请通过本地服务器（http://localhost）打开，且 vendor/ 目录完整。';
    }
  }
}

// ---------------- 摄像头 / 视频 ----------------
async function startCamera() {
  camHint.hidden = true;
  if (!navigator.mediaDevices?.getUserMedia) {
    showCamError('当前环境不支持摄像头，请改用「打开视频」，或确认用 HTTPS / localhost 打开。');
    return;
  }
  try {
    stopAllMedia();
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 960 } }, audio: false,
    });
    mediaSource = 'camera';
    video.srcObject = stream;
    video.hidden = false;
    placeholder.hidden = true;
    await video.play();
  } catch (e) {
    showCamError('无法访问摄像头：可能被拒绝授权。请允许权限，或点「打开视频」用本地视频演示。');
  }
}
function showCamError(msg) {
  camHint.hidden = false;
  camHint.textContent = msg;
  placeholder.hidden = false;
}
function stopAllMedia() {
  if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
  try { video.pause(); } catch (e) {}
  video.srcObject = null;
  if (fileObjectUrl) { URL.revokeObjectURL(fileObjectUrl); fileObjectUrl = null; }
  video.removeAttribute('src');
  video.load();
  lastVideoTime = -1;
  mediaSource = 'none';
  clearOverlay();
  stopRecording();
}
function openVideoFile(file) {
  if (!file) return;
  stopAllMedia();
  mediaSource = 'file';
  fileObjectUrl = URL.createObjectURL(file);
  video.srcObject = null;
  video.src = fileObjectUrl;
  video.controls = true;
  video.loop = true;          // 循环播放，方便反复观察动作
  video.hidden = false;
  placeholder.hidden = true;
  camHint.hidden = true;
  video.onloadedmetadata = () => {
    video.currentTime = 0;
    // 加载完成后自动播放，驱动检测循环逐帧推理
    video.play().catch((err) => {
      console.warn('自动播放被拦截，请点击画面播放按钮', err);
      camHint.hidden = false;
      camHint.textContent = '视频已载入，请点击画面上的播放按钮开始识别。';
    });
  };
  video.onerror = () => {
    showCamError('视频加载失败：该格式可能不被浏览器支持（建议使用 H.264 编码的 .mp4）。请换一个视频文件重试。');
  };
}

// ---------------- 录制控制 ----------------
function startRecording() {
  const w = wordSelect.value.trim();
  if (!w) { alert('请先输入或选择一个手语词作为标签。'); return; }
  recorder = new SequenceRecorder(parseInt(seqLenInput.value, 10) || SEQ_DEFAULT.seqLen);
  recorder.start();
  recordBtn.textContent = '■ 停止录制';
  recordBtn.classList.add('recording');
  recordStatus.textContent = '录制中… 做完动作后点「停止录制」';
  recordStatus.className = 'record-status recording';
}
function stopRecording() {
  if (!recorder.recording) return;
  const seq = recorder.stop();
  recordBtn.textContent = '● 开始录制';
  recordBtn.classList.remove('recording');
  recordFrames.textContent = '0 帧';

  if (!seq) {
    recordStatus.textContent = '未保存：帧数不足（需≥' + SEQ_DEFAULT.minFrames + ' 帧）';
    recordStatus.className = 'record-status';
    return;
  }
  const label = wordSelect.value.trim() || '未命名';
  const signer = signerInput.value.trim() || 'unknown';
  const sample = buildSample(label, seq, { signer });
  library.samples.push(sample);
  saveLibrary();
  renderSampleList();
  recordStatus.textContent = '已保存：' + label + '（' + seq.length + ' 帧）';
  recordStatus.className = 'record-status saved';
}
recordBtn.addEventListener('click', () => {
  if (recorder.recording) stopRecording();
  else startRecording();
});

// ---------------- 检测循环 ----------------
function loop() {
  requestAnimationFrame(loop);
  if (!handLandmarker) return;
  const src = video;
  if (!src || src.readyState < 2 || !src.videoWidth) return;

  let landmarks = null;
  try {
    if (src.currentTime !== lastVideoTime) {
      lastVideoTime = src.currentTime;
      const res = handLandmarker.detectForVideo(src, performance.now());
      landmarks = res?.landmarks?.[0] || null;
    } else {
      landmarks = lastLandmarks;
    }
  } catch (e) {}

  lastLandmarks = landmarks;
  drawOverlay(src, landmarks);

  if (!landmarks || landmarks.length < 21) return;

  // 录制中逐帧提取特征
  if (recorder.recording) {
    const feat = frameFeature(landmarks);
    if (feat) {
      recorder.push(feat);
      recordFrames.textContent = recorder.count + ' 帧';
    }
  }
}

// ---------------- 叠加绘制 ----------------
function drawOverlay(src, landmarks) {
  const w = overlay.clientWidth || src.clientWidth;
  const h = overlay.clientHeight || src.clientHeight;
  if (overlay.width !== w || overlay.height !== h) { overlay.width = w; overlay.height = h; }
  ctx.clearRect(0, 0, w, h);
  if (!landmarks) return;
  const vw = src.videoWidth, vh = src.videoHeight;
  const scale = Math.min(w / vw, h / vh);
  const dw = vw * scale, dh = vh * scale;
  const ox = (w - dw) / 2, oy = (h - dh) / 2;
  const px = (p) => ox + p.x * dw;
  const py = (p) => oy + p.y * dh;

  // 录制中用红色高亮骨架，非录制用绿色
  const color = recorder.recording ? 'rgba(255,120,120,0.95)' : 'rgba(168,230,163,0.9)';
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (const [a, b] of CONNECTIONS) {
    const p1 = landmarks[a], p2 = landmarks[b];
    if (!p1 || !p2) continue;
    ctx.moveTo(px(p1), py(p1));
    ctx.lineTo(px(p2), py(p2));
  }
  ctx.stroke();
  ctx.fillStyle = color;
  for (const p of landmarks) {
    ctx.beginPath(); ctx.arc(px(p), py(p), 3, 0, Math.PI * 2); ctx.fill();
  }
}
function clearOverlay() { ctx.clearRect(0, 0, overlay.width, overlay.height); }

// ---------------- 样本列表（支持单条查看/删除，便于纠错反馈） ----------------
function renderSampleList() {
  const n = library.samples.length;
  sampleSummary.textContent = n + ' 条';
  if (!n) { sampleList.textContent = '暂无样本'; return; }

  sampleList.innerHTML = '';
  // 倒序显示（最新的在前）
  for (let i = n - 1; i >= 0; i--) {
    const s = library.samples[i];
    const item = document.createElement('div');
    item.className = 'sample-item';

    const info = document.createElement('div');
    info.className = 's-info';
    const label = document.createElement('div');
    label.className = 's-label';
    label.textContent = '#' + (i + 1) + '  ' + s.label;
    const meta = document.createElement('div');
    meta.className = 's-meta';
    meta.textContent = `${s.frames} 帧 · ${s.signer} · ${s.view}`;
    info.appendChild(label);
    info.appendChild(meta);

    const del = document.createElement('button');
    del.className = 's-del';
    del.textContent = '删除';
    del.title = '删除这条样本';
    del.addEventListener('click', () => {
      if (!confirm(`删除样本 #${i + 1}（${s.label}，${s.frames} 帧）？`)) return;
      library.samples.splice(i, 1);
      saveLibrary();
      renderSampleList();
    });

    item.appendChild(info);
    item.appendChild(del);
    sampleList.appendChild(item);
  }
}

// ---------------- 导出 / 导入 ----------------
function exportSamples() {
  const data = JSON.stringify(library, null, 2);
  const blob = new Blob([data], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const stamp = new Date().toISOString().slice(0, 10);
  a.href = url;
  a.download = `csl-sequences-${stamp}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function importSamples(file) {
  if (!file) return;
  try {
    const text = await file.text();
    const parsed = validateSeqLibrary(JSON.parse(text));
    if (!parsed) throw new Error('格式不符');
    library = parsed;
    saveLibrary();
    renderSampleList();
    alert(`导入成功：共 ${library.samples.length} 条序列样本`);
  } catch (e) {
    alert('导入失败：JSON 格式不符合序列样本库要求（需含 samples，每条有 label 与 sequence）。');
  }
}

// ---------------- 词表加载 ----------------
function loadVocab(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const data = JSON.parse(reader.result);
      const labels = data.labels;
      if (!labels || typeof labels !== 'object') throw new Error('无 labels');
      wordSet = new Set(Object.values(labels).filter((v) => typeof v === 'string'));
      wordList.innerHTML = '';
      for (const w of wordSet) {
        const opt = document.createElement('option');
        opt.value = w;
        wordList.appendChild(opt);
      }
      vocabStatus.textContent = '已加载词表：' + wordSet.size + ' 个词。';
      vocabStatus.classList.add('loaded');
    } catch (e) {
      vocabStatus.textContent = '词表加载失败：请确认是 label_map.json（含 labels 字段）。';
      vocabStatus.classList.remove('loaded');
    }
  };
  reader.readAsText(file);
}

// ---------------- 事件绑定 ----------------
$('btnStartCam').addEventListener('click', startCamera);
$('btnStopCam').addEventListener('click', () => {
  stopAllMedia();
  placeholder.hidden = false;
});
$('fileVideo').addEventListener('change', (e) => { openVideoFile(e.target.files[0]); e.target.value = ''; });
// 统一用 JS 显式触发文件选择，避免 label/for + hidden input 在个别环境的兼容问题
document.querySelectorAll('label[for]').forEach((lbl) => {
  const target = $(lbl.getAttribute('for'));
  if (!target || target.type !== 'file') return;
  lbl.addEventListener('click', (e) => {
    e.preventDefault();   // 阻止默认的 for 触发，避免二次弹窗
    target.click();       // 手动触发文件选择框
  });
});
$('btnExport').addEventListener('click', exportSamples);
$('fileImport').addEventListener('change', (e) => { importSamples(e.target.files[0]); e.target.value = ''; });
$('btnReset').addEventListener('click', () => {
  if (!confirm('确定清空全部序列样本？此操作不可撤销。')) return;
  library = emptySeqLibrary();
  saveLibrary();
  renderSampleList();
});
$('fileVocab').addEventListener('change', (e) => { loadVocab(e.target.files[0]); e.target.value = ''; });

// ---------------- 启动 ----------------
loadLocal();
renderSampleList();
initModel();
requestAnimationFrame(loop);

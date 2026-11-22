import { FilesetResolver, HandLandmarker } from './vendor/vision_bundle.mjs';
import {
  loadModel, isLoaded, landmarksToFeature,
  infer, softmax, getLabels,
} from './web_inference.mjs';

// ---------------- DOM ----------------
const $ = (id) => document.getElementById(id);
const video = $('video');
const overlay = $('overlay');
const ctx = overlay.getContext('2d');
const placeholder = $('videoPlaceholder');
const camHint = $('camHint');
const modelStatus = $('modelStatus');
const resultEl = $('result');
const handBadge = $('handBadge');
const frameBadge = $('frameBadge');
const topkList = $('topkList');
const diagEl = $('diag');

// ---------------- 状态 ----------------
const SEQ_LEN = 30;       // 与训练一致的序列帧数
const STRIDE = 10;        // 滑动窗口步长：每 10 帧识别一次（约 3 次/秒）
let handLandmarker = null;
let stream = null;
let mediaSource = 'none';
let fileObjectUrl = null;
let lastVideoTime = -1;
let lastLandmarks = null;

// 帧缓冲：持续累积归一化特征，凑满 30 帧做一次识别
let frameBuffer = [];      // 每项是 42 维 Float32Array

// 手掌骨架连线
const CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,4],
  [0,5],[5,6],[6,7],[7,8],
  [5,9],[9,10],[10,11],[11,12],
  [9,13],[13,14],[14,15],[15,16],
  [13,17],[17,18],[18,19],[19,20],[0,17],
];

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
    await loadModel('./sign_model_web.json');
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
      await loadModel('./sign_model_web.json');
      modelStatus.textContent = '模型就绪(CPU)';
      modelStatus.className = 'status-pill status-ready';
    } catch (e2) {
      console.error(e2);
      modelStatus.textContent = '模型加载失败';
      modelStatus.className = 'status-pill status-error';
      camHint.hidden = false;
      camHint.textContent = '模型加载失败，请通过本地服务器（http://localhost）打开，且 vendor/ 与 sign_model_web.json 完整。';
    }
  }
}

// ---------------- 摄像头 / 视频 ----------------
async function startCamera() {
  camHint.hidden = true;
  if (!navigator.mediaDevices?.getUserMedia) {
    showError('当前环境不支持摄像头，请改用「上传视频」，或确认用 HTTPS / localhost 打开。');
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
    showError('无法访问摄像头：可能被拒绝授权。请允许权限，或点「上传视频」用本地视频演示。');
  }
}
function showError(msg) {
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
  resetBuffer();
}
function openVideoFile(file) {
  if (!file) return;
  stopAllMedia();
  mediaSource = 'file';
  fileObjectUrl = URL.createObjectURL(file);
  video.srcObject = null;
  video.src = fileObjectUrl;
  video.controls = true;
  video.loop = true;
  video.hidden = false;
  placeholder.hidden = true;
  camHint.hidden = true;
  video.onloadedmetadata = () => {
    video.currentTime = 0;
    video.play().catch(() => {
      camHint.hidden = false;
      camHint.textContent = '视频已载入，请点击画面上的播放按钮开始识别。';
    });
  };
  video.onerror = () => {
    showError('视频加载失败：该格式可能不被浏览器支持（建议 H.264 编码的 .mp4）。请换一个视频重试。');
  };
}

// ---------------- 帧缓冲 ----------------
function resetBuffer() {
  frameBuffer = [];
  frameBadge.textContent = '0/' + SEQ_LEN + ' 帧';
}
function pushFrame(feat) {
  frameBuffer.push(feat);
  if (frameBuffer.length > SEQ_LEN) {
    frameBuffer = frameBuffer.slice(-SEQ_LEN);  // 只保留最近 30 帧
  }
  frameBadge.textContent = frameBuffer.length + '/' + SEQ_LEN + ' 帧';
  if (frameBuffer.length === SEQ_LEN) {
    runRecognition(frameBuffer);
    frameBuffer = frameBuffer.slice(STRIDE);   // 滑动窗口，前移 STRIDE 帧
  }
}

// ---------------- 识别 ----------------
function runRecognition(frames) {
  if (!isLoaded()) return;
  // frames: 30 个 42 维特征 -> 平铺 (42 × 30)
  const flat = new Float32Array(42 * SEQ_LEN);
  for (let t = 0; t < SEQ_LEN; t++) {
    const f = frames[t];
    for (let c = 0; c < 42; c++) flat[c * SEQ_LEN + t] = f[c];
  }
  const logits = infer(flat);
  const probs = softmax(logits);
  const labels = getLabels();
  const sorted = Array.from(probs)
    .map((p, i) => ({ idx: i, p }))
    .sort((a, b) => b.p - a.p)
    .slice(0, 5);

  // 更新主结果
  const top = sorted[0];
  resultEl.textContent = labels[top.idx];
  resultEl.className = 'result result-ok';

  // 更新 Top-5 列表
  topkList.innerHTML = '';
  sorted.forEach((s, rank) => {
    const item = document.createElement('div');
    item.className = 'topk-item' + (rank === 0 ? ' top1' : '');
    item.innerHTML = `
      <span class="topk-rank">${rank + 1}</span>
      <span class="topk-label">${escapeHtml(labels[s.idx])}</span>
      <span class="topk-bar-wrap">
        <span class="topk-bar"><span class="topk-bar-fill" style="width:${(s.p * 100).toFixed(1)}%"></span></span>
        <span class="topk-prob">${(s.p * 100).toFixed(1)}%</span>
      </span>
    `;
    topkList.appendChild(item);
  });

  diagEl.textContent = sorted.map((s, r) =>
    `#${r + 1} ${labels[s.idx]}: ${(s.p * 100).toFixed(2)}%`).join('\n');
}

function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

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

  if (!landmarks || landmarks.length < 21) {
    handBadge.textContent = '未检测到手';
    handBadge.className = 'mini-badge';
    resetBuffer();
    return;
  }

  handBadge.textContent = '检测到手';
  handBadge.className = 'mini-badge mini-ok';

  const feat = landmarksToFeature(landmarks);
  if (feat) pushFrame(feat);
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

  const color = 'rgba(110, 231, 183, 0.9)';
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

// ---------------- 事件绑定 ----------------
$('btnStartCam').addEventListener('click', startCamera);
$('btnStopCam').addEventListener('click', () => {
  stopAllMedia();
  placeholder.hidden = false;
});
$('fileVideo').addEventListener('change', (e) => { openVideoFile(e.target.files[0]); e.target.value = ''; });
// 统一用 JS 显式触发文件选择
document.querySelectorAll('label[for]').forEach((lbl) => {
  const target = $(lbl.getAttribute('for'));
  if (!target || target.type !== 'file') return;
  lbl.addEventListener('click', (e) => { e.preventDefault(); target.click(); });
});

// ---------------- 启动 ----------------
initModel();
requestAnimationFrame(loop);

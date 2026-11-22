/**
 * 端侧图像质量评估。
 * 目的：在调用云端模型之前，先在手机上判断"这张照片糊不糊"。
 * 好处有两点：
 *   1. 模糊照片不产生模型调用费用（一次调用约 0.05 元，量大很可观）
 *   2. 反馈更快——本地算完立刻能播报，用户不用等网络往返
 *
 * 算法：缩小到 240px 以内 → 转灰度 → 四邻域拉普拉斯卷积 → 取方差。
 * 方差越小说明边缘越少、画面越平滑，即越可能失焦。
 */
const MAX_EDGE = 240;

function laplacianVariance(pixels, w, h) {
  const gray = new Float32Array(w * h);
  for (let i = 0, p = 0; i < pixels.length; i += 4, p++) {
    // 亮度加权，符合人眼感知
    gray[p] = 0.299 * pixels[i] + 0.587 * pixels[i + 1] + 0.114 * pixels[i + 2];
  }

  let sum = 0;
  let sumSq = 0;
  let n = 0;
  for (let y = 1; y < h - 1; y++) {
    for (let x = 1; x < w - 1; x++) {
      const c = y * w + x;
      const lap = gray[c - 1] + gray[c + 1] + gray[c - w] + gray[c + w] - 4 * gray[c];
      sum += lap;
      sumSq += lap * lap;
      n++;
    }
  }
  if (!n) return 0;
  const mean = sum / n;
  return sumSq / n - mean * mean;
}

/**
 * @param {string} path 本地图片路径
 * @returns {Promise<number>} 清晰度分数，越大越清晰；经验阈值约 30
 *
 * 可靠性设计：本地检测只是"预筛"，任何失败（超时/画布异常/图片损坏）
 * 都返回 999 直接放行，由云端的质量判断兜底——绝不允许本地检测卡死主流程。
 */
const DETECT_TIMEOUT = 3000; // 毫秒；真机上画布回调偶发不触发，必须有超时

function sharpness(path) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (score, why) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (why) console.warn('[quality] 检测放行:', why);
      resolve(score);
    };
    // 超时保护：回调不触发时 3 秒后放行，避免整个拍照流程挂起
    const timer = setTimeout(() => finish(999, '超时'), DETECT_TIMEOUT);

    if (!wx.getImageInfo || !wx.createOffscreenCanvas) {
      // 基础库过低时不做本地判断，放行由云端兜底
      finish(999, '基础库不支持');
      return;
    }

    try {
      wx.getImageInfo({
        src: path,
        success: (info) => {
          try {
            const edge = Math.max(info.width, info.height);
            const scale = edge > MAX_EDGE ? MAX_EDGE / edge : 1;
            const w = Math.max(8, Math.round(info.width * scale));
            const h = Math.max(8, Math.round(info.height * scale));

            const canvas = wx.createOffscreenCanvas({ type: '2d', width: w, height: h });
            const ctx = canvas.getContext('2d');
            const img = canvas.createImage();

            img.onload = () => {
              try {
                ctx.drawImage(img, 0, 0, w, h);
                const { data } = ctx.getImageData(0, 0, w, h);
                finish(laplacianVariance(data, w, h));
              } catch (e) {
                finish(999, '像素读取失败 ' + (e && e.message));
              }
            };
            img.onerror = () => finish(999, '图片加载失败');
            img.src = path;
          } catch (e) {
            finish(999, '画布创建失败 ' + (e && e.message));
          }
        },
        fail: () => finish(999, '图片信息读取失败')
      });
    } catch (e) {
      finish(999, '检测异常 ' + (e && e.message));
    }
  });
}

module.exports = { sharpness, laplacianVariance };

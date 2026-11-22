const tts = require('../../utils/tts');
const quality = require('../../utils/quality');

// 清晰度阈值（拉普拉斯方差）。低于此值判定为失焦，本地直接要求重拍，不调模型。
const SHARP_THRESHOLD = 30;
// 连拍帧数：一次快门后连拍多帧，选最清晰的一帧送模型
const SHOT_COUNT = 3;

const STATE = {
  IDLE: 'idle',
  SHOOTING: 'shooting',
  ANALYZING: 'analyzing',
  WAIT_RETAKE: 'wait_retake'
};

Page({
  data: {
    cameraReady: false,
    statusText: '轻点拍照，长按说话',
    hintText: ''
  },

  ctx: null,
  recorder: null,
  sttManager: null,
  state: STATE.IDLE,
  lastTouchAt: 0,
  question: '',

  onLoad() {
    this.ctx = wx.createCameraContext();
    this.initRecorder();
    this.setData({ cameraReady: true });
    // 进入即播报，让用户知道自己在哪里；同一会话只播一次（页面偶发重载不重复打扰）
    const app = getApp();
    if (!app.globalData.readyAnnounced) {
      app.globalData.readyAnnounced = true;
      tts.speak('随手拍助手已就绪。轻点屏幕下方拍照，长按可以说话提问。', { effect: 'ok' });
    }
  },

  onUnload() {
    tts.stop();
  },

  onCameraError(e) {
    console.error('[camera] error', e);
    tts.speak('相机打开失败，请检查是否允许了相机权限。', { effect: 'retry' });
    this.setData({ cameraReady: false });
  },

  /** 触达即反馈：任何触摸先给震动 + 音效，确认"我点到了东西" */
  onButtonTouch() {
    wx.vibrateShort({ type: 'light' });
    tts.playEffect('tick');
    const now = Date.now();
    if (now - this.lastTouchAt > 4000) {
      tts.speak('拍摄键。轻点拍照，长按说话。');
      this.lastTouchAt = now;
    }
  },

  onTapHelp() {
    tts.speak(
      '使用方法：轻点屏幕下方任意位置拍照，我会告诉您拍到了什么。如果照片不清楚，我会提示您怎么调整。长按可以说话，问我想知道的事情。'
    );
  },

  /** 轻点：连拍 → 端侧择优 → 清晰度闸门 → 上传分析（每个阶段都在屏幕可见，便于诊断） */
  async onTapShoot() {
    if (this.state === STATE.ANALYZING) {
      tts.speak('正在识别，请稍等。');
      return;
    }
    this.state = STATE.SHOOTING;
    this.setData({ statusText: '正在拍照…', hintText: '' });
    tts.speak('好，正在拍照。', { effect: 'tick' });

    try {
      const paths = await this.takeShots(SHOT_COUNT);
      if (!paths.length) throw new Error('3 帧连拍全部失败');

      this.setData({ statusText: '正在检查画面…' });
      tts.speak('正在检查画面。');
      const best = await this.pickSharpest(paths);

      // 本地闸门：模糊照片直接要求重拍，不产生模型调用
      if (best.score < SHARP_THRESHOLD) {
        console.log('[shoot] 本地判定模糊，score=', Math.round(best.score));
        this.retakeGuide('照片有点模糊，请把手机拿稳，停一秒再拍一次。');
        return;
      }

      await this.analyse(best.path);
    } catch (err) {
      console.error('[shoot] fail', err);
      this.state = STATE.IDLE;
      this.setData({ statusText: '拍照失败', hintText: String((err && err.message) || err) });
      tts.speak('拍照没有成功，请再试一次。', { effect: 'retry' });
    }
  },

  /** 连拍：逐帧触发，单帧失败不影响其余帧；帧间隔留 300ms，真机连拍过快易失败 */
  async takeShots(count) {
    const paths = [];
    for (let i = 0; i < count; i++) {
      try {
        const p = await this.takePhoto();
        paths.push(p);
      } catch (e) {
        console.warn('[shoot] 第', i + 1, '帧失败', e);
      }
      if (i < count - 1) {
        await new Promise((r) => setTimeout(r, 300));
      }
    }
    return paths;
  },

  /** 逐帧算清晰度，取最高的一帧（检测失败按 999 放行，由云端兜底） */
  async pickSharpest(paths) {
    const scored = [];
    for (const p of paths) {
      const score = await quality.sharpness(p);
      scored.push({ path: p, score });
    }
    scored.sort((a, b) => b.score - a.score);
    console.log('[quality] 各帧清晰度', scored.map((s) => Math.round(s.score)));
    return scored[0];
  },

  takePhoto() {
    return new Promise((resolve, reject) => {
      this.ctx.takePhoto({
        quality: 'high',
        success: (res) => resolve(res.tempImagePath),
        fail: reject
      });
    });
  },

  /** 上传到云存储 → 调云函数做质量判断 + 生成回答 */
  async analyse(filePath) {
    this.state = STATE.ANALYZING;
    this.setData({ statusText: '正在识别…' });

    try {
      // 高清原图动辄 2-3MB，下载/转码/传给模型都很慢，是"服务未响应"超时的主因；
      // 先压缩到几百 KB，全链路提速数倍（压缩失败不阻塞，退回原图）
      const smallPath = await this.compressShot(filePath);
      const cloudPath = `shots/${Date.now()}.jpg`;
      const up = await wx.cloud.uploadFile({ cloudPath, filePath: smallPath });
      const r = await this.callVqa(up.fileID);

      getApp().globalData.session = r.session || getApp().globalData.session;
      this.handleResult(r);
    } catch (err) {
      console.error('[analyse] fail', err);
      this.state = STATE.IDLE;
      this.setData({ statusText: '轻点拍照，长按说话' });
      tts.speak('识别服务没有响应，请检查网络后再试一次。', { effect: 'retry' });
    }
  },

  /** 压缩照片：视觉模型不需要原始分辨率，压缩后识别速度大幅提升 */
  compressShot(filePath) {
    return new Promise((resolve) => {
      if (!wx.compressImage) return resolve(filePath);
      wx.compressImage({
        src: filePath,
        quality: 45,
        success: (res) => resolve(res.tempFilePath || filePath),
        fail: () => resolve(filePath)
      });
    });
  },

  /** 调用 vqa 云函数：默认 15 秒超时太短，拉到 60 秒；偶发失败自动重试一次，用户无感知 */
  callVqa(fileId) {
    const app = getApp();
    const attempt = () =>
      wx.cloud
        .callFunction({
          name: 'vqa',
          data: {
            fileId,
            question: this.question || '',
            session: app.globalData.session
          },
          config: { timeout: 60000 }
        })
        .then((res) => {
          const r = (res && res.result) || null;
          if (!r) throw new Error('云端返回为空');
          return r;
        });

    return attempt().catch((err) => {
      console.warn('[analyse] 首次调用失败，2 秒后自动重试', (err && err.errMsg) || err);
      return new Promise((resolve) => setTimeout(resolve, 2000)).then(attempt);
    });
  },

  /**
   * 三态处理：
   * 1) ok=true  → 播报答案，可以继续追问
   * 2) ok=false 且带部分结论 → 先说已知的，再引导补拍，避免用户重复劳动
   * 3) ok=false 且无结论 → 只播报具体调整指令（偏斜/太远/太近/缺反面）
   */
  handleResult(r) {
    console.log('[analyse] 云端返回', JSON.stringify(r).slice(0, 400));
    if (r.ok) {
      this.state = STATE.IDLE;
      this.setData({ statusText: '轻点拍照，长按说话', hintText: '' });
      this.question = '';
      tts.speak(r.answer || '识别完成。', { effect: 'ok' });
      return;
    }

    const hint = r.hint || '照片不够清楚，请把手机对准物体，靠近一点再拍一次。';

    if (r.answer) {
      this.state = STATE.WAIT_RETAKE;
      this.setData({ statusText: '需要补充拍摄', hintText: hint });
      tts.speak(`${r.answer}。还差一点：${hint}`, { effect: 'retry' });
      wx.vibrateShort({ type: 'medium' });
      return;
    }

    this.retakeGuide(hint);
  },

  /** 统一的"需要重拍"反馈：状态位、界面文案、语音、震动四件事一次做完 */
  retakeGuide(hint) {
    this.state = STATE.WAIT_RETAKE;
    this.setData({ statusText: '需要重新拍摄', hintText: hint || '' });
    tts.speak(hint, { effect: 'retry' });
    wx.vibrateShort({ type: 'heavy' });
  },

  /** 通用按键触达反馈：任何按键按下先给震动+音效，再报按键名 */
  onKeyTouch(e) {
    const label = (e && e.currentTarget && e.currentTarget.dataset.label) || '';
    wx.vibrateShort({ type: 'light' });
    tts.playEffect('tick');
    if (label) tts.speak(label);
  },

  /** 长按说话：语音提问（插件优先，个人主体不可用时走云函数识别） */
  onLongPressTalk() {
    if (!this.sttManager) {
      tts.speak('语音提问暂不可用，请直接拍照，我会给出通用解读。');
      return;
    }
    tts.playEffect('tick');
    wx.vibrateShort({ type: 'medium' });
    tts.speak('请说话。');
    this.sttManager.start({ duration: 10000, lang: 'zh_CN' });
  },

  /** 听到问题后的统一处理：识别文本 → 确认 → 引导拍照 */
  handleQuestion(text) {
    if (!text) {
      tts.speak('没有听清，请再说一次，或者直接拍照。');
      return;
    }
    this.question = text;
    tts.speak(`您问的是：${text}。现在请轻点拍照。`);
  },

  initRecorder() {
    // 通道 1：同声传译插件（若小程序后台已添加则自动启用）
    try {
      const plugin = requirePlugin('WechatSI');
      const mgr = plugin.getRecordRecognitionManager();
      mgr.onStop = (res) => this.handleQuestion(res && res.result);
      mgr.onError = (err) => {
        console.warn('[stt] plugin error', err);
        tts.speak('语音识别失败，请直接拍照。');
      };
      this.sttManager = mgr;
      return;
    } catch (e) {
      console.warn('[stt] 插件不可用，启用云端识别通道');
    }

    // 通道 2：RecorderManager 录音 → 云存储 → speech 云函数（腾讯云一句话识别）
    const rm = wx.getRecorderManager();
    rm.onStop((res) => {
      if (!res || !res.tempFilePath) {
        tts.speak('没有听清，请再说一次，或者直接拍照。');
        return;
      }
      wx.cloud.uploadFile({
        cloudPath: `stt/q-${Date.now()}.mp3`,
        filePath: res.tempFilePath
      })
        .then((up) => wx.cloud.callFunction({
          name: 'speech',
          data: { action: 'asr', fileID: up.fileID }
        }))
        .then((r) => {
          const result = (r && r.result) || {};
          if (result.code !== 'OK') {
            console.warn('[stt] cloud asr fail', result.code, result.message);
            tts.speak('语音识别服务暂时不可用，请直接拍照。');
            return;
          }
          this.handleQuestion(result.text);
        })
        .catch((err) => {
          console.warn('[stt] cloud asr error', err);
          tts.speak('语音识别失败，请直接拍照。');
        });
    });
    rm.onError((err) => {
      console.warn('[stt] recorder error', err);
      tts.speak('录音失败，请直接拍照。');
    });
    this.sttManager = {
      start: () => rm.start({
        format: 'mp3',
        duration: 10000,
        sampleRate: 16000,
        numberOfChannels: 1,
        encodeBitRate: 48000
      })
    };
  }
});

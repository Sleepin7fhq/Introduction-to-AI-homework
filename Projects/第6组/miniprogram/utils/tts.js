/**
 * 语音播报适配层（三通道）：
 * 1) 微信「同声传译」插件（WechatSI）——零成本首选（个人主体当前不可添加，保留自动探测）
 * 2) 云函数 speech（腾讯云基础语音合成）——插件不可用时的兜底，返回 mp3 base64 本地播放
 * 3) 震动 + 音效——云语音也不可用时的最低保底，保证核心交互不中断
 */
const plugin = requirePlugin ? safeRequirePlugin('WechatSI') : null;

function safeRequirePlugin(name) {
  try {
    return requirePlugin(name);
  } catch (e) {
    console.warn('[tts] 插件不可用，语音播报走云端兜底', e && e.message);
    return null;
  }
}

const audioCtx = wx.createInnerAudioContext();
audioCtx.obeyMuteSwitch = false; // 静音键下仍需播报

let speaking = false;
let currentPlayer = null; // 全局唯一播放器：新播报打断旧的，避免多句重叠
let pendingSeq = 0;       // 请求序号：过期的云端合成结果直接丢弃

function playEffect(name) {
  try {
    audioCtx.stop();
    audioCtx.src = `/assets/${name}.wav`;
    audioCtx.play();
  } catch (e) {
    /* 音效失败不影响主流程 */
  }
}

function vibrateFallback() {
  wx.vibrateShort({ type: 'medium' });
}

/** 打断并销毁当前播放（新播报前调用，杜绝多句语音叠音） */
function stopCurrent() {
  if (currentPlayer) {
    try {
      currentPlayer.stop();
      currentPlayer.destroy();
    } catch (e) { /* ignore */ }
    currentPlayer = null;
  }
  speaking = false;
}

/** 云端 TTS：调云函数 speech 合成 mp3，写入本地临时文件后播放 */
function cloudSpeak(text) {
  const seq = ++pendingSeq;
  wx.cloud.callFunction({ name: 'speech', data: { action: 'tts', text } })
    .then((res) => {
      const r = (res && res.result) || {};
      if (seq !== pendingSeq) return; // 已有更新的播报，丢弃过期结果
      if (r.code !== 'OK' || !r.audioBase64) {
        console.warn('[tts] 云端合成不可用', r.code, r.message);
        vibrateFallback();
        return;
      }
      const fs = wx.getFileSystemManager();
      const path = `${wx.env.USER_DATA_PATH}/tts_reply_${seq}.mp3`;
      fs.writeFile({
        filePath: path,
        data: r.audioBase64,
        encoding: 'base64',
        success: () => {
          if (seq !== pendingSeq) return;
          playFile(path);
        },
        fail: (e) => {
          console.warn('[tts] 音频落盘失败', e);
          vibrateFallback();
        }
      });
    })
    .catch((e) => {
      console.warn('[tts] 云函数调用失败', e);
      if (seq === pendingSeq) vibrateFallback();
    });
}

function playFile(path) {
  stopCurrent();
  const inner = wx.createInnerAudioContext();
  currentPlayer = inner;
  inner.obeyMuteSwitch = false;
  inner.src = path;
  inner.onEnded(() => {
    speaking = false;
    inner.destroy();
    if (currentPlayer === inner) currentPlayer = null;
  });
  inner.onError(() => {
    speaking = false;
    inner.destroy();
    if (currentPlayer === inner) currentPlayer = null;
    vibrateFallback();
  });
  inner.play();
}

/**
 * @param {string} text 要播报的内容
 * @param {object} opt  { interrupt: 是否打断当前播报, effect: 附带音效名 }
 */
function speak(text, opt = {}) {
  const { interrupt = true, effect } = opt;
  if (effect) playEffect(effect);
  if (!text) return;

  if (!plugin || !plugin.textToSpeech) {
    // 无插件：走云端合成
    cloudSpeak(text);
    return;
  }

  if (interrupt && speaking) {
    try {
      plugin.textToSpeech({ tts: true, lang: 'zh_CN', content: '', success() {}, fail() {} });
    } catch (e) {
      /* ignore */
    }
  }

  speaking = true;
  plugin.textToSpeech({
    lang: 'zh_CN',
    tts: true,
    content: text,
    success: (res) => {
      if (!res.filename) {
        speaking = false;
        cloudSpeak(text); // 插件异常时兜底
        return;
      }
      playFile(res.filename);
    },
    fail: (err) => {
      speaking = false;
      console.warn('[tts] 插件合成失败，转云端', err);
      cloudSpeak(text);
    }
  });
}

function stop() {
  try {
    audioCtx.stop();
  } catch (e) {
    /* ignore */
  }
  stopCurrent();
}

module.exports = { speak, stop, playEffect };

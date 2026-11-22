/**
 * 云函数 speech：语音双能力（无第三方 npm 依赖，纯原生 https + TC3 签名）。
 *
 *   action = 'asr'  语音转文字：一句话识别 SentenceRecognition（≤60s，≤1MB）
 *   action = 'tts'  文字转语音：基础语音合成 TextToVoice，返回 mp3 base64
 *
 * 用途：个人主体小程序无法添加「同声传译」插件（WechatSI）时的替代语音链路。
 * 若日后插件可用，小程序端会自动优先走插件，本函数仍作为兜底。
 *
 * 环境变量（云开发控制台配置，切勿写进代码）：
 *   TENCENT_SECRET_ID   腾讯云 API 密钥 ID（console.cloud.tencent.com/cam/capi）
 *   TENCENT_SECRET_KEY  腾讯云 API 密钥 Key
 *   ASR_ENG_TYPE        可选，默认 16k_zh（中文普通话）
 *   TTS_VOICE_TYPE      可选，默认 101001（女声），换音色改此值
 */
const cloud = require('wx-server-sdk');
const https = require('https');
const crypto = require('crypto');

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

/* ---------------- TC3-HMAC-SHA256 签名调用 ---------------- */

function sha256hex(data) {
  return crypto.createHash('sha256').update(data, 'utf8').digest('hex');
}

function hmac(key, data) {
  return crypto.createHmac('sha256', key).update(data, 'utf8').digest();
}

function callTencentCloud(service, host, action, version, params, secretId, secretKey) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(params);
    const ts = Math.floor(Date.now() / 1000);
    // TC3 规范：签名凭证中的日期必须是 UTC 日期（不是东八区），
    // 否则北京时间 0 点后与 UTC 日期分叉，导致签名验证失败
    const date = new Date(ts * 1000).toISOString().slice(0, 10);

    const canonicalHeaders = `content-type:application/json; charset=utf-8\nhost:${host}\n`;
    const signedHeaders = 'content-type;host';
    const canonicalRequest = [
      'POST', '/', '', canonicalHeaders, signedHeaders, sha256hex(body)
    ].join('\n');

    const scope = `${date}/${service}/tc3_request`;
    const stringToSign = [
      'TC3-HMAC-SHA256', String(ts), scope, sha256hex(canonicalRequest)
    ].join('\n');

    const kDate = hmac(`TC3${secretKey}`, date);
    const kService = hmac(kDate, service);
    const kSigning = hmac(kService, 'tc3_request');
    const signature = crypto.createHmac('sha256', kSigning)
      .update(stringToSign, 'utf8').digest('hex');

    const auth = `TC3-HMAC-SHA256 Credential=${secretId}/${scope}, ` +
      `SignedHeaders=${signedHeaders}, Signature=${signature}`;

    const req = https.request({
      host,
      path: '/',
      method: 'POST',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        Host: host,
        'X-TC-Action': action,
        'X-TC-Version': version,
        'X-TC-Timestamp': String(ts),
        'X-TC-Language': 'zh-CN',
        Authorization: auth,
        'Content-Length': Buffer.byteLength(body)
      }
    }, (res) => {
      let buf = '';
      res.on('data', (c) => (buf += c));
      res.on('end', () => {
        try {
          const json = JSON.parse(buf);
          if (json.Response && json.Response.Error) {
            return reject(new Error(`${json.Response.Error.Code}: ${json.Response.Error.Message}`));
          }
          resolve(json.Response);
        } catch (e) {
          reject(new Error('非 JSON 响应: ' + buf.slice(0, 200)));
        }
      });
    });
    req.on('timeout', () => req.destroy(new Error('timeout')));
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

/* ---------------- 入口 ---------------- */

exports.main = async (event) => {
  const { action } = event;
  const secretId = process.env.TENCENT_SECRET_ID;
  const secretKey = process.env.TENCENT_SECRET_KEY;

  if (!secretId || !secretKey) {
    return { code: 'NO_KEY', message: '语音服务密钥未配置，请告知开发者。' };
  }

  try {
    /* ---- 语音转文字 ---- */
    if (action === 'asr') {
      const { fileID } = event;
      if (!fileID) return { code: 'NO_FILE', message: '没有收到录音文件。' };

      const dl = await cloud.downloadFile({ fileID });
      const audioBase64 = dl.fileContent.toString('base64');
      if (audioBase64.length > 1.35e6) {
        return { code: 'TOO_LONG', message: '说话时间太长了，请控制在 30 秒以内。' };
      }

      const resp = await callTencentCloud(
        'asr', 'asr.tencentcloudapi.com', 'SentenceRecognition', '2019-06-14',
        {
          ProjectId: 0,
          SubServiceType: 2,
          EngServiceType: process.env.ASR_ENG_TYPE || '16k_zh',
          VoiceFormat: 'mp3',
          UsrAudioKey: 'vqa-question',
          Audio: audioBase64
        },
        secretId, secretKey
      );
      return { code: 'OK', text: (resp.Result || '').trim() };
    }

    /* ---- 文字转语音 ---- */
    if (action === 'tts') {
      const { text } = event;
      if (!text) return { code: 'NO_TEXT', message: '没有要播报的内容。' };
      if (text.length > 600) {
        return { code: 'TOO_LONG', message: '播报内容过长。' };
      }

      const resp = await callTencentCloud(
        'tts', 'tts.tencentcloudapi.com', 'TextToVoice', '2019-08-23',
        {
          Text: text,
          SessionId: crypto.randomBytes(8).toString('hex'),
          Volume: 0,
          Speed: 0,
          ModelType: 1,
          PrimaryLanguage: 1,
          SampleRate: 16000,
          Codec: 'mp3',
          VoiceType: Number(process.env.TTS_VOICE_TYPE || 101001)
        },
        secretId, secretKey
      );
      return { code: 'OK', audioBase64: resp.Audio };
    }

    return { code: 'BAD_ACTION', message: '未知操作类型。' };
  } catch (e) {
    console.error('[speech]', e);
    return { code: 'API_ERROR', message: String(e.message || e).slice(0, 200) };
  }
};

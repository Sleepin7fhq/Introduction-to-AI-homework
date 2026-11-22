/**
 * 云函数 vqa：接收图片 fileID + 用户问题 + 会话上下文，
 * 调用智谱 GLM-5.3-Flash（原生多模态，支持图像输入）完成「质量判断 + 任务型回答」。
 *
 * 环境变量（必须在云开发控制台配置，切勿写在代码里）：
 *   GLM_API_KEY    智谱开放平台（bigmodel.cn / Z.ai）API Key
 *   GLM_MODEL      默认 glm-5.3-flash
 */
const cloud = require('wx-server-sdk');
const https = require('https');
const { SCENES, SYSTEM_PROMPT } = require('./templates');

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const API_HOST = 'open.bigmodel.cn';
const API_PATH = '/api/paas/v4/chat/completions';

exports.main = async (event) => {
  const { fileId, question = '', session = {} } = event;

  if (!fileId) {
    return { ok: false, hint: '没有收到照片，请重新拍摄。', session };
  }

  const apiKey = process.env.GLM_API_KEY;
  if (!apiKey) {
    return { ok: false, hint: '服务端尚未配置模型密钥，请联系开发者。', session };
  }

  let base64;
  try {
    const dl = await cloud.downloadFile({ fileID: fileId });
    base64 = dl.fileContent.toString('base64');
  } catch (e) {
    console.error('[vqa] download fail', e);
    return { ok: false, hint: '照片读取失败，请再拍一次。', session };
  }

  const nextSession = {
    scene: session.scene || null,
    collected: { ...(session.collected || {}) },
    missing: session.missing || [],
    turns: (session.turns || 0) + 1
  };

  // 多轮上下文：把上一轮已确认的信息带给模型，避免重复追问
  const contextNote = nextSession.turns > 1
    ? `这是同一目标的第 ${nextSession.turns} 次拍摄。上一轮已知信息：${JSON.stringify(nextSession.collected)}；上一轮缺失项：${JSON.stringify(nextSession.missing)}。请优先检查这些缺失项是否已补全。`
    : '';

  const scene = SCENES[nextSession.scene] || null;
  const sceneNote = scene ? `用户当前场景可能是「${scene.label}」，该场景必须采集的信息包括：${scene.required.join('、')}。` : '';

  const userText = [question, contextNote, sceneNote].filter(Boolean).join('\n') || '请告诉我这张照片里有什么值得注意的信息。';

  const body = {
    model: process.env.GLM_MODEL || 'glm-5.3-flash',
    temperature: 0.2,
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      {
        role: 'user',
        content: [
          { type: 'image_url', image_url: { url: `data:image/jpeg;base64,${base64}` } },
          { type: 'text', text: userText }
        ]
      }
    ]
  };

  // 模型调用最多尝试 2 次（网络抖动 / 服务偶发 5xx 时自动重试，提升可用性）
  let raw = null;
  let lastErr = null;
  for (let i = 0; i < 2; i++) {
    try {
      raw = await postJson(body, apiKey);
      lastErr = null;
      break;
    } catch (e) {
      lastErr = e;
      console.error(`[vqa] model call attempt ${i + 1} fail`, (e && e.message) || e);
    }
  }
  if (lastErr) {
    return { ok: false, hint: '识别服务暂时不可用，请稍后再试。', session: nextSession };
  }

  const parsed = parseModelJson(raw);
  const result = normalize(parsed, nextSession);

  // 更新会话：记录场景与缺失项，供下一轮判断
  nextSession.scene = result.scene || nextSession.scene;
  if (result.ok) {
    nextSession.missing = [];
  } else {
    nextSession.missing = result.missing || [];
  }

  return {
    ok: result.ok,
    scene: result.scene,
    hint: result.hint,
    answer: result.answer,
    evidence: result.evidence,
    quality: result.quality,
    session: nextSession
  };
};

function postJson(payload, apiKey) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(payload);
    const req = https.request(
      {
        host: API_HOST,
        path: API_PATH,
        method: 'POST',
        timeout: 25000,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
          'Content-Length': Buffer.byteLength(data)
        }
      },
      (res) => {
        let buf = '';
        res.on('data', (c) => (buf += c));
        res.on('end', () => {
          if (res.statusCode < 200 || res.statusCode >= 300) {
            return reject(new Error(`HTTP ${res.statusCode}: ${buf.slice(0, 300)}`));
          }
          try {
            const json = JSON.parse(buf);
            const content = json.choices && json.choices[0] && json.choices[0].message && json.choices[0].message.content;
            resolve(content || '');
          } catch (e) {
            reject(new Error('模型返回非 JSON：' + buf.slice(0, 200)));
          }
        });
      }
    );
    req.on('timeout', () => req.destroy(new Error('timeout')));
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

/** 模型可能返回 ```json 包裹的内容，做一次宽松解析 */
function parseModelJson(text) {
  if (!text) return null;
  const cleaned = String(text).replace(/```json/gi, '').replace(/```/g, '').trim();
  try {
    return JSON.parse(cleaned);
  } catch (e) {
    const m = cleaned.match(/\{[\s\S]*\}/);
    if (m) {
      try {
        return JSON.parse(m[0]);
      } catch (e2) {
        /* fallthrough */
      }
    }
    console.warn('[vqa] unparsable model output', cleaned.slice(0, 300));
    return null;
  }
}

function normalize(r, session) {
  if (!r || typeof r.ok !== 'boolean') {
    // 解析失败时保守处理：当作需要重拍，绝不返回可能编造的内容
    return {
      ok: false,
      scene: session.scene || 'unknown',
      hint: '这张照片我没能看清，请把手机拿稳，靠近一点再拍一次。',
      answer: '',
      evidence: '',
      quality: {},
      missing: []
    };
  }
  return {
    ok: r.ok,
    scene: r.scene || session.scene || 'unknown',
    hint: r.hint || '',
    answer: r.answer || '',
    evidence: r.evidence || '',
    quality: r.quality || {},
    missing: Array.isArray(r.missing) ? r.missing : []
  };
}

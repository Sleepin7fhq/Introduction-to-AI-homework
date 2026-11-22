/**
 * ACE-Step 真实音频端到端验收。
 * 用法: node scripts/e2e-ace.mjs <cdpPort> <baseUrl> <outDir> <happy|fallback>
 */
import fs from 'node:fs';
import path from 'node:path';

const port = process.argv[2] ?? '9226';
const baseUrl = process.argv[3] ?? 'http://127.0.0.1:5173/';
const outDir = process.argv[4] ?? '.shots';
const mode = process.argv[5] ?? 'happy';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const page = targets.find((t) => t.type === 'page');
if (!page) {
  console.error('no page target');
  process.exit(1);
}
const ws = new WebSocket(page.webSocketDebuggerUrl);
let seq = 0;
const pending = new Map();
const events = [];
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) {
    pending.get(m.id)(m);
    pending.delete(m.id);
  } else if (m.method) events.push(m);
});
await new Promise((res, rej) => {
  ws.addEventListener('open', res);
  ws.addEventListener('error', rej);
});
const send = (method, params = {}) =>
  new Promise((resolve) => {
    const id = ++seq;
    pending.set(id, resolve);
    ws.send(JSON.stringify({ id, method, params }));
  });
async function evaluate(expression) {
  const res = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (res.result?.exceptionDetails) return { error: res.result.exceptionDetails.exception?.description };
  return { value: res.result?.result?.value };
}
async function shot(name) {
  const res = await send('Page.captureScreenshot', { format: 'png' });
  const file = path.join(outDir, name);
  fs.writeFileSync(file, Buffer.from(res.result.data, 'base64'));
  return file;
}
const results = [];
function check(name, ok, detail = '') {
  results.push({ name, ok, detail });
  console.log(`${ok ? '  ✓' : '  ✗'} ${name}${detail ? '  ' + detail : ''}`);
}

await send('Runtime.enable');
await send('Page.enable');
await send('Log.enable');
await send('Page.navigate', { url: baseUrl });
await sleep(3200);

const engines = await evaluate(`JSON.stringify([...document.querySelectorAll('.engine-chip')].map(c => ({
  text: c.textContent.replace(/\\s+/g,' ').trim(),
  up: c.classList.contains('up'),
  active: c.classList.contains('active')
})))`);
const list = engines.value ? JSON.parse(engines.value) : [];
const ace = list.find((e) => e.text.includes('ACE-Step'));
console.log(`\n[引擎探测] ${list.map((e) => `${e.text}${e.up ? '✓' : '✗'}`).join(' | ')}`);

if (mode === 'happy') {
  console.log('\n[1. ACE-Step 就绪并自动选中]');
  check('ACE-Step 显示可用', !!ace && ace.up === true, ace ? ace.text : '未找到');
  check('ACE-Step 被自动选中', !!ace && ace.active === true);

  console.log('\n[2. 发起真实生成任务]');
  // 8 小节 → 时长约 15 秒，避免测试等太久
  await evaluate(`(() => {
    const el = document.querySelector('#bars');
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(el, '8');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  })()`);
  await sleep(300);
  await evaluate(`document.querySelector('.primary-btn.wide').click()`);
  await sleep(600);
  const during = await evaluate(`JSON.stringify({
    btn: document.querySelector('.primary-btn.wide') ? document.querySelector('.primary-btn.wide').textContent.trim() : '',
    task: document.querySelector('.task-head') ? document.querySelector('.task-head').textContent.trim() : ''
  })`);
  const d = during.value ? JSON.parse(during.value) : {};
  check('生成中按钮进入进行态', /生成中/.test(d.btn), d.btn);
  check('显示任务状态', (d.task || '').length > 0, d.task);

  // 等音频出现（模型推理 + 裁剪）
  let audioInfo = null;
  for (let i = 0; i < 40; i++) {
    await sleep(1500);
    const r = await evaluate(`(() => {
      const el = document.querySelector('.at-player');
      if (!el) return null;
      return JSON.stringify({ src: el.currentSrc || el.src, ready: el.readyState, dur: el.duration, err: el.error ? el.error.code : null });
    })()`);
    if (r.value) {
      audioInfo = JSON.parse(r.value);
      break;
    }
  }
  check('前端收到真实音频元素', !!audioInfo, audioInfo ? audioInfo.src : '超时未出现');
  if (audioInfo) {
    check('音频来自本机 ACE-Step 服务', String(audioInfo.src).startsWith('http://127.0.0.1:8000/audio/'), audioInfo.src);
    check('浏览器已解码到可播放数据', audioInfo.ready >= 2, `readyState=${audioInfo.ready}`);
    check('时长在合理范围', audioInfo.dur > 5 && audioInfo.dur < 35, `${audioInfo.dur}s`);
    check('无解码错误', audioInfo.err === null, `error=${audioInfo.err}`);
  }

  console.log('\n[3. 实际播放]');
  const playRes = await evaluate(`(async () => {
    const el = document.querySelector('.at-player');
    if (!el) return JSON.stringify({ ok: false });
    try {
      el.muted = false;
      el.currentTime = 0;
      await el.play();
      await new Promise(r => setTimeout(r, 1600));
      return JSON.stringify({ ok: !el.paused, t: el.currentTime, dur: el.duration });
    } catch (e) { return JSON.stringify({ ok: false, err: String(e) }); }
  })()`);
  const pr = playRes.value ? JSON.parse(playRes.value) : { ok: false };
  check('音频真实播放（非暂停且时间在走）', pr.ok === true && pr.t > 0.3, `currentTime=${pr.t}`);

  const msgText = await evaluate(`JSON.stringify([...document.querySelectorAll('.msg-text')].map(e => e.textContent))`);
  const msgs = msgText.value ? JSON.parse(msgText.value) : [];
  check('回执明确说明是音频而非谱面', msgs.some((m) => m.includes('音频')), (msgs[msgs.length - 1] || '').slice(0, 40));

  const file = await shot('e2e-ace-audio.png');
  console.log(`  截图: ${file}`);
} else {
  console.log('\n[4. 服务不可用时的回退]');
  check('ACE-Step 显示不可用', !!ace && ace.up === false, ace ? ace.text : '未找到');
  const local = list.find((e) => e.text.includes('本地符号引擎'));
  check('本地符号引擎仍可用且被选中', !!local && local.up === true && local.active === true);

  await evaluate(`document.querySelector('.primary-btn.wide').click()`);
  let notes = 0;
  for (let i = 0; i < 20; i++) {
    await sleep(800);
    const r = await evaluate(`document.querySelectorAll('.note').length`);
    notes = r.value ?? 0;
    if (notes > 50) break;
  }
  check('回退后仍生成出可播放工程', notes > 50, `${notes} 个音符`);
  const hasAudio = await evaluate(`!!document.querySelector('.at-player')`);
  check('没有伪造 AI 音频', hasAudio.value === false);
  const file = await shot('e2e-fallback-local.png');
  console.log(`  截图: ${file}`);

  console.log('\n[5. 备用真实音频素材]');
  const clicked = await evaluate(`(() => {
    const b = document.querySelector('.backup-item');
    if (!b) return false;
    b.click();
    return true;
  })()`);
  check('存在备用素材入口', clicked.value === true);
  await sleep(1500);
  const bk = await evaluate(`(() => {
    const el = document.querySelector('.at-player');
    if (!el) return null;
    return JSON.stringify({ src: el.currentSrc || el.src, ready: el.readyState, dur: el.duration, err: el.error ? el.error.code : null });
  })()`);
  const b = bk.value ? JSON.parse(bk.value) : null;
  check('备用素材是真实 WAV', !!b && /\/demo\/acestep-.*\.wav$/.test(String(b.src)), b ? b.src : '无');
  check('备用素材可解码', !!b && b.ready >= 2 && !b.err, b ? `readyState=${b.ready} err=${b.err} dur=${b.dur}` : '');
  const bplay = await evaluate(`(async () => {
    const el = document.querySelector('.at-player');
    if (!el) return JSON.stringify({ ok: false });
    try { el.currentTime = 0; await el.play(); await new Promise(r => setTimeout(r, 1200));
      return JSON.stringify({ ok: !el.paused, t: el.currentTime }); }
    catch (e) { return JSON.stringify({ ok: false, err: String(e) }); }
  })()`);
  const bp = bplay.value ? JSON.parse(bplay.value) : { ok: false };
  check('备用素材真实播放', bp.ok === true && bp.t > 0.2, `currentTime=${bp.t}`);
}

console.log('\n[控制台]');
const errors = events.filter(
  (e) =>
    e.method === 'Runtime.exceptionThrown' ||
    (e.method === 'Log.entryAdded' && e.params?.entry?.level === 'error'),
);
const real = errors.filter((e) => {
  const t = JSON.stringify(e);
  if (t.includes('favicon')) return false;
  if (mode === 'fallback' && t.includes('8000')) return false;
  return true;
});
check('无未捕获异常', real.length === 0, `${real.length} 条`);
if (real.length) real.slice(0, 3).forEach((e) => console.log('   ', JSON.stringify(e).slice(0, 260)));

const failed = results.filter((r) => !r.ok);
console.log('\n' + '='.repeat(56));
console.log(`ACE E2E (${mode}) ${failed.length === 0 ? 'ALL PASS' : 'FAIL'} — ${results.length - failed.length}/${results.length}`);
if (failed.length) {
  console.log(failed.map((f) => '  ✗ ' + f.name + (f.detail ? ' → ' + f.detail : '')).join('\n'));
  process.exitCode = 1;
}
ws.close();

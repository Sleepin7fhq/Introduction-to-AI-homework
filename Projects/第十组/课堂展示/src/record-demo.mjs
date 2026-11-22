/**
 * 真实操作录屏（完整版）：
 *   1) Meme-to-Rave：输入梗 → 找 → 选卡 → 生成 → 播放 AI 音频
 *   2) 切本地符号引擎 → 生成 → 时间轴播放（播放头在走）
 * 输出原始帧 + 精确时间戳，剪辑交给 assemble_gif.py。
 */
import fs from 'node:fs';
import path from 'node:path';

const port = process.argv[2] ?? '9230';
const outDir = process.argv[3] ?? 'frames';
fs.mkdirSync(outDir, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const page = targets.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pend = new Map();
const frames = [];
let lastSaved = 0;
let t0 = 0;
const marks = {};

ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) {
    pend.get(m.id)(m);
    pend.delete(m.id);
    return;
  }
  if (m.method === 'Page.screencastFrame') {
    const now = Date.now();
    if (now - lastSaved >= 80) {
      const file = path.join(outDir, `f${String(frames.length).padStart(4, '0')}.jpg`);
      fs.writeFileSync(file, Buffer.from(m.params.data, 'base64'));
      frames.push({ file, t: now - t0 });
      lastSaved = now;
    }
    ws.send(
      JSON.stringify({ id: ++id, method: 'Page.screencastFrameAck', params: { sessionId: m.params.sessionId } }),
    );
  }
});

await new Promise((r) => ws.addEventListener('open', r));
const send = (method, params = {}) =>
  new Promise((res) => {
    const i = ++id;
    pend.set(i, res);
    ws.send(JSON.stringify({ id: i, method, params }));
  });
const evaluate = async (expr) => {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  return r.result?.result?.value;
};
const mark = (k) => {
  marks[k] = Date.now() - t0;
};

await send('Page.enable');
await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 810, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: 'http://127.0.0.1:5173/' });
await sleep(2800);

t0 = Date.now();
await send('Page.startScreencast', { format: 'jpeg', quality: 82, maxWidth: 1440, maxHeight: 810, everyNthFrame: 1 });
await sleep(500);

// ---- 1) Meme-to-Rave ----
await evaluate(`(()=>{const t=[...document.querySelectorAll('.mode-tab')].find(e=>e.textContent.includes('Meme'));t&&t.click();})()`);
await sleep(800);
mark('memeTab');

await evaluate(`(() => {
  const el = document.querySelector('.meme-input');
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(el, '老板画的饼');
  el.dispatchEvent(new Event('input', { bubbles: true }));
})()`);
await sleep(650);
mark('typed');

await evaluate(`document.querySelector('.meme-input-row .ghost-btn').click()`);
await sleep(950);
mark('found');

await evaluate(`(() => { const c = document.querySelector('.meme-card'); c && c.click(); })()`);
await sleep(850);
mark('picked');

mark('genClick');
await evaluate(`document.querySelector('.primary-btn.wide').click()`);
let audioAt = 0;
for (let i = 0; i < 90; i++) {
  await sleep(400);
  if (await evaluate(`!!document.querySelector('.at-player')`)) {
    audioAt = Date.now() - t0;
    break;
  }
}
mark('audioReady');

await sleep(600);
await evaluate(`(async () => { const el = document.querySelector('.at-player');
  if (el) { el.currentTime = 0; try { await el.play(); } catch(e){} } })()`);
await sleep(4200);
mark('audioPlayed');

// ---- 2) 切本地符号引擎，看时间轴 ----
await evaluate(`(() => {
  const t = [...document.querySelectorAll('.mode-tab')].find(e => e.textContent.includes('创作'));
  t && t.click();
})()`);
await sleep(500);
await evaluate(`(() => {
  const sel = document.querySelector('#engine');
  const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
  setter.call(sel, 'local-symbolic');
  sel.dispatchEvent(new Event('change', { bubbles: true }));
})()`);
await sleep(400);
// 改成 8 小节，生成更快
await evaluate(`(() => {
  const el = document.querySelector('#bars');
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(el, '8');
  el.dispatchEvent(new Event('input', { bubbles: true }));
})()`);
await sleep(300);
mark('localGenClick');
await evaluate(`document.querySelector('.primary-btn.wide').click()`);
await sleep(1400);
mark('timelineReady');

// 播放时间轴
await evaluate(`document.querySelector('.transport-btn.play').click()`);
await sleep(5200);
mark('timelinePlayed');
await evaluate(`document.querySelector('.transport-btn.stop')?.click()`);
await sleep(400);

await send('Page.stopScreencast');
fs.writeFileSync(
  path.join(outDir, 'timeline.json'),
  JSON.stringify({ frames, marks, audioAt }, null, 2),
);
console.log('frames=%d audioAt=%d marks=%s', frames.length, audioAt, JSON.stringify(marks));
ws.close();

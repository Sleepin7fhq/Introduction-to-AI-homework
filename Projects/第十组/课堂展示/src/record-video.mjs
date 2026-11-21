/**
 * 录制 MP4 素材：Meme-to-Rave 全流程 + 播放 AI 音频。
 * 同时抓取页面正在播放的音频 URL，供后续直接作为音轨（真实声音，不配音）。
 *
 * 用法: node src/record-video.mjs <cdpPort> <framesDir>
 */
import fs from 'node:fs';
import path from 'node:path';

const port = process.argv[2] ?? '9231';
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
let audioUrl = '';

ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) {
    pend.get(m.id)(m);
    pend.delete(m.id);
    return;
  }
  if (m.method === 'Page.screencastFrame') {
    const now = Date.now();
    if (now - lastSaved >= 32) {
      const file = path.join(outDir, `f${String(frames.length).padStart(5, '0')}.jpg`);
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
await sleep(3000);

t0 = Date.now();
await send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 1440, maxHeight: 810, everyNthFrame: 1 });
await sleep(600);

await evaluate(`(()=>{const t=[...document.querySelectorAll('.mode-tab')].find(e=>e.textContent.includes('Meme'));t&&t.click();})()`);
await sleep(900);
mark('memeTab');

await evaluate(`(() => {
  const el = document.querySelector('.meme-input');
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(el, '老板画的饼');
  el.dispatchEvent(new Event('input', { bubbles: true }));
})()`);
await sleep(900);
mark('typed');

await evaluate(`document.querySelector('.meme-input-row .ghost-btn').click()`);
await sleep(1200);
mark('found');

await evaluate(`(() => { const c = document.querySelector('.meme-card'); c && c.click(); })()`);
await sleep(1100);
mark('picked');

mark('genClick');
await evaluate(`document.querySelector('.primary-btn.wide').click()`);
let audioAt = 0;
for (let i = 0; i < 100; i++) {
  await sleep(350);
  if (await evaluate(`!!document.querySelector('.at-player')`)) {
    audioAt = Date.now() - t0;
    break;
  }
}
mark('audioReady');

await sleep(900);
// 抓取真实音频地址（页面播放的就是这条）
audioUrl = (await evaluate(`(() => { const el = document.querySelector('.at-player'); return el ? (el.currentSrc || el.src) : ''; })()`)) || '';
mark('beforePlay');
await evaluate(`(async () => { const el = document.querySelector('.at-player');
  if (el) { el.currentTime = 0; try { await el.play(); } catch(e){} } })()`);
mark('playStart');

// 让音乐放一段（这段是真实声音）
await sleep(13000);
mark('playEnd');
await evaluate(`(() => { const el = document.querySelector('.at-player'); if (el) el.pause(); })()`);
await sleep(700);
mark('done');

await send('Page.stopScreencast');
fs.writeFileSync(
  path.join(outDir, 'timeline.json'),
  JSON.stringify({ frames, marks, audioAt, audioUrl }, null, 2),
);
console.log('frames=%d audioAt=%d audioUrl=%s', frames.length, audioAt, audioUrl);
console.log('marks', JSON.stringify(marks));
ws.close();

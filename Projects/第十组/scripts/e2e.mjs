/**
 * 端到端验收：用 Chrome DevTools Protocol 驱动真实浏览器。
 * 不是截图看看而已 —— 要点按钮、等生成、数音符、确认播放头真的在走。
 *
 * 用法: node scripts/e2e.mjs <cdpPort> <baseUrl> <outDir>
 */
import fs from 'node:fs';
import path from 'node:path';

const port = process.argv[2] ?? '9223';
const baseUrl = process.argv[3] ?? 'http://127.0.0.1:5173/';
const outDir = process.argv[4] ?? '.shots';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const page = targets.find((t) => t.type === 'page');
if (!page) {
  console.error('no page target found');
  process.exit(1);
}

const ws = new WebSocket(page.webSocketDebuggerUrl);
let seq = 0;
const pending = new Map();
const events = [];

ws.addEventListener('message', (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  } else if (msg.method) {
    events.push(msg);
  }
});

await new Promise((resolve, reject) => {
  ws.addEventListener('open', resolve);
  ws.addEventListener('error', reject);
});

function send(method, params = {}) {
  return new Promise((resolve) => {
    const id = ++seq;
    pending.set(id, resolve);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const res = await send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (res.result?.exceptionDetails) {
    return { error: res.result.exceptionDetails.exception?.description ?? 'eval error' };
  }
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
await sleep(2600);
// 测试固定用本地符号引擎：ACE 服务在线时页面会自动切到神经网络引擎，
// 那条路径需要 10-30 秒推理，属于 e2e-ace.mjs 的职责。
await evaluate(
  "(() => {" +
    "const c = [...document.querySelectorAll('.engine-chip')].find(x => x.textContent.includes('本地符号'));" +
    "if (c && !c.classList.contains('active')) c.click();" +
    "})()",
);
await sleep(400);

// ---------- 1. 首屏 ----------
const boot = await evaluate(`JSON.stringify({
  root: !!document.querySelector('.app'),
  hero: !!document.querySelector('.hero-title'),
  chips: document.querySelectorAll('.engine-chip').length,
  bootErr: !!document.getElementById('boot-error'),
  title: document.title
})`);
const b = boot.value ? JSON.parse(boot.value) : {};
console.log('\n[1. 首屏]');
check('App 挂载', b.root === true);
check('未触发启动期错误横幅', b.bootErr === false);
check('引擎状态徽章已探测', b.chips >= 3, `${b.chips} 个`);
check('标题正确', String(b.title).includes('DSH Studio 2.0'), b.title);

// ---------- 2. 点示例生成 Meme Rave ----------
console.log('\n[2. Meme-to-Rave 生成（点第三个示例）]');
await evaluate(`(() => {
  const btns = [...document.querySelectorAll('.example-btn')];
  const target = btns.find(b => b.textContent.includes('Meme')) || btns[btns.length - 1];
  target.click();
  return true;
})()`);
await sleep(2600);

const gen = await evaluate(`JSON.stringify({
  notes: document.querySelectorAll('.note').length,
  lanes: document.querySelectorAll('.lane').length,
  tracks: document.querySelectorAll('.track-head').length,
  sections: [...document.querySelectorAll('.section-band')].map(e => e.textContent),
  msgs: [...document.querySelectorAll('.msg-text')].map(e => e.textContent),
  proj: document.querySelector('#project-name') ? document.querySelector('#project-name').value : '',
  chords: [...document.querySelectorAll('.chord-cell')].map(e => e.textContent).slice(0, 8),
  heroGone: !document.querySelector('.hero-title'),
  err: !!document.getElementById('boot-error')
})`);
const g = gen.value ? JSON.parse(gen.value) : {};
check('时间轴已替换首屏', g.heroGone === true);
check('渲染出音符块', g.notes > 150, `${g.notes} 个`);
check('音轨轨头已生成', g.tracks >= 4, `${g.tracks} 轨`);
check('段落带已渲染', (g.sections || []).length >= 4, (g.sections || []).join('→'));
check('和弦轨有内容', (g.chords || []).some((c) => c && c !== '—'), (g.chords || []).join(' '));
check('Producer 回执消息', (g.msgs || []).length >= 2, `${(g.msgs || []).length} 条`);
check('工程名已自动命名', !!g.proj && g.proj !== '未命名工程', g.proj);
check('无启动错误', g.err === false);
const shotA = await shot('e2e-01-rave.png');
console.log(`  截图: ${shotA}`);

// ---------- 3. 播放 ----------
console.log('\n[3. 播放控制]');
const before = (await evaluate(`document.querySelector('.pos-readout').textContent.trim()`)).value;
await evaluate(`document.querySelector('.transport-btn.play').click()`);
await sleep(1800);
const playing = await evaluate(`JSON.stringify({
  pos: document.querySelector('.pos-readout').textContent.trim(),
  cls: document.querySelector('.transport-btn.play').className,
  err: !!document.getElementById('boot-error')
})`);
const p = playing.value ? JSON.parse(playing.value) : {};
check('播放按钮进入播放态', String(p.cls).includes('on'), p.cls);
check('播放位置在推进', p.pos !== before, `${before} → ${p.pos}`);
check('播放无崩溃', p.err === false);
const shotB = await shot('e2e-02-playing.png');
console.log(`  截图: ${shotB}`);

await evaluate(`document.querySelector('.transport-btn.stop').click()`);
await sleep(400);

// ---------- 4. 创作模式直接生成 ----------
console.log('\n[4. 创作模式生成（改 BPM + 再生成）]');
await evaluate(`(() => {
  const tab = [...document.querySelectorAll('.mode-tab')].find(t => t.textContent.includes('创作'));
  if (tab) tab.click();
  return true;
})()`);
await sleep(300);
await evaluate(`(() => {
  const bpm = document.querySelector('#bpm');
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(bpm, '150');
  bpm.dispatchEvent(new Event('input', { bubbles: true }));
  return true;
})()`);
await sleep(200);
await evaluate(`document.querySelector('.primary-btn.wide').click()`);
await sleep(2200);
const second = await evaluate(`JSON.stringify({
  bpm: [...document.querySelectorAll('.chip')].find(c => c.textContent.includes('BPM'))?.textContent,
  transportBpm: document.querySelectorAll('.bpm-readout')[0].textContent,
  notes: document.querySelectorAll('.note').length,
  lanes: document.querySelectorAll('.lane').length
})`);
const s = second.value ? JSON.parse(second.value) : {};
check('第二次生成成功', s.notes > 100, `${s.notes} notes / ${s.lanes} lanes`);
check('BPM 覆盖生效', String(s.transportBpm).trim() === '150', `${s.transportBpm} / ${s.bpm}`);
const shotC = await shot('e2e-03-compose.png');
console.log(`  截图: ${shotC}`);

// ---------- 5. 交互：静音 + 选中 ----------
console.log('\n[5. 音轨交互]');
const mute = await evaluate(`(() => {
  const btn = document.querySelector('.track-head .mini-btn');
  if (!btn) return JSON.stringify({ ok: false });
  btn.click();
  return new Promise(r => setTimeout(() => r(JSON.stringify({
    ok: true,
    muted: !!document.querySelector('.track-head.muted'),
    label: btn.textContent.trim()
  })), 200));
})()`);
const m = mute.value ? JSON.parse(mute.value) : {};
check('静音按钮可切换', m.ok === true && (m.muted === true || m.label === 'MUTE'), `${m.label}`);

// ---------- 6. 彩排自检页 ----------
console.log('\n[6. 彩排自检页 ?selftest=1]');
await send('Page.navigate', { url: baseUrl.replace(/\/$/, '') + '/?selftest=1' });
await sleep(4500);
const st = await evaluate(`JSON.stringify({
  rows: document.querySelectorAll('.selftest li').length,
  bad: [...document.querySelectorAll('.selftest li.bad .st-name')].map(e => e.textContent),
  summary: document.querySelector('.st-summary') ? document.querySelector('.st-summary').textContent.trim() : '',
  bootErr: !!document.getElementById('boot-error')
})`);
const t = st.value ? JSON.parse(st.value) : {};
check('自检页渲染', (t.rows || 0) >= 4, `${t.rows} 项`);
check('自检页无启动错误', t.bootErr === false);
check('自检全部通过', (t.bad || []).length === 0, t.summary + ((t.bad || []).length ? ' 失败:' + t.bad.join(',') : ''));
const shotD = await shot('e2e-04-selftest.png');
console.log(`  截图: ${shotD}`);

// ---------- 7. 控制台异常 ----------
console.log('\n[7. 控制台]');
const errors = events.filter(
  (e) =>
    e.method === 'Runtime.exceptionThrown' ||
    (e.method === 'Log.entryAdded' && e.params?.entry?.level === 'error'),
);
// 过滤掉探测失败产生的噪音（fetch 127.0.0.1:8000 被拒绝是预期行为）
const real = errors.filter((e) => {
  const text = JSON.stringify(e);
  return !(text.includes('8000') || text.includes('ERR_CONNECTION_REFUSED'));
});
check('无未捕获异常', real.length === 0, `${real.length} 条`);
if (real.length) {
  for (const e of real.slice(0, 3)) console.log('   ', JSON.stringify(e).slice(0, 300));
}

const failed = results.filter((r) => !r.ok);
console.log('\n' + '='.repeat(56));
console.log(`E2E ${failed.length === 0 ? 'ALL PASS' : 'FAIL'} — ${results.length - failed.length}/${results.length}`);
if (failed.length) {
  console.log(failed.map((f) => '  ✗ ' + f.name + (f.detail ? ' → ' + f.detail : '')).join('\n'));
  process.exitCode = 1;
}
ws.close();

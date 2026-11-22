/**
 * 用应用内的离线渲染钩子生成 WAV 样本。
 * 用法: node scripts/render-samples.mjs <port> <downloadDir> <presetJsonFile>
 *
 * presetJsonFile: [{ "label": "...", "style": "house", "prompt": "...", "bars": 8 }, ...]
 */
import fs from 'node:fs';
import path from 'node:path';

const port = process.argv[2] ?? '9232';
const outDir = process.argv[3] ?? 'samples';
const presetFile = process.argv[4];

fs.mkdirSync(outDir, { recursive: true });
const presets = JSON.parse(fs.readFileSync(presetFile, 'utf8'));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const page = targets.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pend = new Map();
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) {
    pend.get(m.id)(m);
    pend.delete(m.id);
  }
});
await new Promise((r) => ws.addEventListener('open', r));
const send = (method, params = {}) =>
  new Promise((res) => {
    const i = ++id;
    pend.set(i, res);
    ws.send(JSON.stringify({ id: i, method, params }));
  });
const evaluate = async (expr, timeout = 180000) => {
  const r = await send('Runtime.evaluate', {
    expression: expr,
    returnByValue: true,
    awaitPromise: true,
    timeout,
  });
  if (r.result?.exceptionDetails) {
    return { error: r.result.exceptionDetails.exception?.description ?? 'eval error' };
  }
  return { value: r.result?.result?.value };
};

await send('Page.enable');
await send('Runtime.enable');
await send('Page.setDownloadBehavior', { behavior: 'allow', downloadPath: path.resolve(outDir) });
await send('Page.navigate', { url: 'http://127.0.0.1:5173/' });
await sleep(3200);

const ready = await evaluate(`typeof window.__dshRender === 'function'`);
if (!ready.value) {
  console.error('离线渲染钩子未就绪');
  process.exit(1);
}
console.log('hook ready');

for (const p of presets) {
  const expr = `window.__dshRender(${JSON.stringify(p.prompt)}, ${JSON.stringify(p.style)}, ${p.bars ?? 8})`;
  const t0 = Date.now();
  const res = await evaluate(expr);
  const ms = Date.now() - t0;
  if (res.error) {
    console.error(`  ✗ ${p.label}: ${String(res.error).slice(0, 200)}`);
    continue;
  }
  const info = res.value;
  console.log(`  ✓ ${p.label}  ${(info.bytes / 1e6).toFixed(2)} MB  ${(ms / 1000).toFixed(1)}s  tempo=${info.tempo}  tracks=${info.tracks}  file=${info.name}`);
  await sleep(600);
}

await sleep(2500);
console.log('\n下载目录内容:');
for (const f of fs.readdirSync(outDir)) {
  const st = fs.statSync(path.join(outDir, f));
  console.log(`  ${f}  ${(st.size / 1e6).toFixed(2)} MB`);
}
ws.close();

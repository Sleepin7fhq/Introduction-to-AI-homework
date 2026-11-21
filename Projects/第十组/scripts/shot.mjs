import fs from 'node:fs';

const port = process.argv[2] ?? '9224';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const t = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const page = t.find((x) => x.type === 'page');
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

await send('Page.enable');
await send('Runtime.enable');
await send('Page.navigate', { url: 'http://127.0.0.1:5173/' });
await sleep(2600);
await send('Runtime.evaluate', {
  expression:
    "(()=>{const b=[...document.querySelectorAll('.example-btn')].find(x=>x.textContent.includes('Meme'));if(b)b.click();return 1})()",
});
await sleep(2600);
const shot = await send('Page.captureScreenshot', { format: 'png' });
fs.writeFileSync('D:/AI/aihw/.shots/studio-1920.png', Buffer.from(shot.result.data, 'base64'));
const lay = await send('Runtime.evaluate', {
  expression: `JSON.stringify({
    w: innerWidth, h: innerHeight,
    docH: document.documentElement.scrollHeight,
    bodyOverflow: getComputedStyle(document.body).overflow,
    tlW: document.querySelector('.tl-lanes') ? document.querySelector('.tl-lanes').clientWidth : 0,
    producerW: document.querySelector('.producer') ? document.querySelector('.producer').clientWidth : 0,
    tracklistW: document.querySelector('.tracklist') ? document.querySelector('.tracklist').clientWidth : 0,
    notes: document.querySelectorAll('.note').length
  })`,
  returnByValue: true,
});
console.log(lay.result.result.value);
ws.close();

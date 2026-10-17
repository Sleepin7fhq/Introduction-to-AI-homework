const fs = require('fs');
const path = require('path');
const {mathjax} = require('mathjax-full/js/mathjax.js');
const {TeX} = require('mathjax-full/js/input/tex.js');
const {SVG} = require('mathjax-full/js/output/svg.js');
const {liteAdaptor} = require('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler} = require('mathjax-full/js/handlers/html.js');
const {AllPackages} = require('mathjax-full/js/input/tex/AllPackages.js');
const {Resvg} = require('@resvg/resvg-js');

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const tex = new TeX({packages: AllPackages});
const svg = new SVG({fontCache: 'none'});
const doc = mathjax.document('', {InputJax: tex, OutputJax: svg});

const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const outDir = process.argv[3];
fs.mkdirSync(outDir, {recursive: true});
const meta = [];
for (const j of jobs) {
  const node = doc.convert(j.tex, {display: true, containerWidth: 100000});
  let s = adaptor.innerHTML(node);
  const m = /viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"/.exec(s);
  if (!m) throw new Error('no viewBox for ' + j.id);
  const w = parseFloat(m[3]), h = parseFloat(m[4]);
  const F = j.size || 28;
  const W = w / 1000 * F, H = h / 1000 * F;
  s = s.replace(/width="[^"]*"/, `width="${W}"`)
       .replace(/height="[^"]*"/, `height="${H}"`)
       .replace(/style="[^"]*"/, '')
       .replace(/currentColor/g, j.color || '#14202E');
  const png = new Resvg(s, {fitTo: {mode: 'zoom', value: j.zoom || 4},
                            background: 'rgba(0,0,0,0)'}).render().asPng();
  fs.writeFileSync(path.join(outDir, j.id + '.png'), png);
  meta.push({id: j.id, w: W, h: H, tex: j.tex, size: F});
}
fs.writeFileSync(path.join(outDir, 'meta.json'), JSON.stringify(meta, null, 1));
console.log('rendered', meta.length);

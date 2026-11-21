/**
 * 组件树真渲染测试：用 react-dom/server 把 <App /> 真正渲染成 HTML。
 * 目的不是截图，而是确认「渲染阶段不抛错」+「关键控件真的出现在 DOM 里」。
 * 交互逻辑由 core.test.ts 覆盖，这里专门抓白屏类事故。
 */
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import App from '../src/App';
import { ProducerPanel } from '../src/components/ProducerPanel';
import { TrackList } from '../src/components/TrackList';
import { Timeline } from '../src/components/Timeline';
import { Transport } from '../src/components/Transport';
import { MemeRave } from '../src/components/MemeRave';
import { composeSongEx } from '../src/music/generate';
import { arrangeSong, planRave } from '../src/music/arrange';
import { findMemes } from '../src/producer/meme';
import { parsePrompt } from '../src/producer/parse';

let passed = 0;
const failures: string[] = [];

function ok(name: string, cond: boolean, detail = ''): void {
  if (cond) {
    passed += 1;
    console.log(`  ✓ ${name}${detail ? '  ' + detail : ''}`);
  } else {
    failures.push(name);
    console.log(`  ✗ ${name}${detail ? '  → ' + detail : ''}`);
  }
}

function has(html: string, needle: string): boolean {
  return html.includes(needle);
}

console.log('\n[7. React 组件树渲染]');

// 1) 整页首屏
let appHtml = '';
try {
  appHtml = renderToString(createElement(App));
  ok('App 渲染不抛错', appHtml.length > 2000, `${appHtml.length} 字符`);
  ok('顶栏存在', has(appHtml, 'DSH STUDIO'));
  ok('工程名输入框存在', has(appHtml, 'project-input'));
  ok('首屏标题存在', has(appHtml, '一句话，做一首能蹦的歌'));
  ok('示例按钮存在', has(appHtml, 'techno · 凌晨改代码'));
  ok('AI Producer 面板存在', has(appHtml, 'AI Producer'));
  ok('创作输入框存在', has(appHtml, 'prompt-box'));
  ok('风格选择存在', has(appHtml, 'id="style"'));
  ok('情绪选择存在', has(appHtml, 'id="mood"'));
  ok('BPM 控件存在', has(appHtml, 'id="bpm"'));
  ok('播放控制存在', has(appHtml, 'transport-btn play'));
  ok('导出按钮存在', has(appHtml, '导出 MIDI'));
  ok('波形画布存在', has(appHtml, 'class="scope"'));
  ok('模式切换存在', has(appHtml, 'Meme-to-Rave'));
} catch (err) {
  ok('App 渲染不抛错', false, String(err));
  console.log(err);
}

// 2) 有歌状态下的时间轴 / 音轨 / 传输条
const song = arrangeSong(composeSongEx('techno 凌晨 128bpm', { bars: 16, tempo: 128 }), planRave(16, 0.9));
try {
  const tl = renderToString(
    createElement(Timeline, { song, selected: song.tracks[0].id, onSelect: () => {}, playing: false, bar: 3 }),
  );
  ok('Timeline 渲染不抛错', tl.length > 1000, `${tl.length} 字符`);
  ok('小节尺存在', has(tl, 'ruler-cell'));
  ok('和弦轨存在', has(tl, 'chord-cell'));
  ok('音符块已渲染', (tl.match(/class="note/g) ?? []).length > 100, `${(tl.match(/class="note/g) ?? []).length} 个`);
  ok('段落带存在', has(tl, 'section-band') && has(tl, 'Drop'));
  ok('播放头存在', has(tl, 'playhead'));

  const tl2 = renderToString(createElement(TrackList, { song, selected: null, onSelect: () => {}, onPatch: () => {} }));
  ok('TrackList 渲染不抛错', tl2.length > 500);
  ok('推子存在', has(tl2, 'gain-slider'));

  const tp = renderToString(
    createElement(Transport, {
      playing: true,
      bar: 4,
      bpm: 128,
      bars: 16,
      onPlay: () => {},
      onStop: () => {},
      onBpm: () => {},
      hasSong: true,
      audioBlocked: false,
    }),
  );
  ok('Transport 渲染不抛错', has(tp, 'transport') && has(tp, '128'));
} catch (err) {
  ok('有歌状态渲染', false, String(err));
  console.log(err);
}

// 3) Producer 面板（含解析结果与消息）
try {
  const intent = parsePrompt('techno 128bpm 16小节，凌晨改代码，很燥');
  const panel = renderToString(
    createElement(ProducerPanel, {
      mode: 'song',
      onMode: () => {},
      prompt: 'techno 128bpm',
      onPrompt: () => {},
      styleId: 'auto',
      onStyleId: () => {},
      moodId: 'auto',
      onMoodId: () => {},
      bpmOverride: 'auto',
      onBpmOverride: () => {},
      barsOverride: 'auto',
      onBarsOverride: () => {},
      energy: 0.7,
      onEnergy: () => {},
      intent,
      statuses: [
        { id: 'local-symbolic', label: '本地符号引擎', kind: 'local', available: true, detail: '离线', probeMs: 0 },
      ],
      backend: 'local-symbolic',
      onBackend: () => {},
      generating: false,
      task: { running: false, label: '本地符号引擎 · 3ms', stages: [{ label: '受约束作曲', ms: 2 }] },
      messages: [{ id: 1, role: 'producer', text: '做好了', bullets: ['共 5 轨'], meta: 'local · 3ms' }],
      onGenerate: () => {},
      onFollowUp: () => {},
      meme: { query: '', onQuery: () => {}, hits: [], pick: null, onPick: () => {}, onGenerate: () => {}, onFind: () => {} },
      bars: 16,
    }),
  );
  ok('ProducerPanel 渲染不抛错', panel.length > 1500);
  ok('解析 chips 渲染', has(panel, 'Techno') && has(panel, '128'));
  ok('阶段耗时渲染', has(panel, '受约束作曲') && has(panel, 'st-ms') && /2(<!-- -->)?ms/.test(panel));
  ok('消息渲染', has(panel, '做好了'));
} catch (err) {
  ok('ProducerPanel 渲染', false, String(err));
  console.log(err);
}

// 4) Meme-to-Rave 面板
try {
  const card = findMemes('早八打工人', 1)[0];
  const memeHtml = renderToString(
    createElement(MemeRave, {
      query: '早八',
      onQuery: () => {},
      hits: [card],
      pick: card,
      onPick: () => {},
      onGenerate: () => {},
      generating: false,
      bars: 16,
      onFind: () => {},
    }),
  );
  ok('MemeRave 渲染不抛错', memeHtml.length > 800);
  ok('梗卡渲染', has(memeHtml, card.name) && has(memeHtml, String(card.bpm)));
  ok('演示剧本渲染', has(memeHtml, 'Drop') && has(memeHtml, '演示剧本'));
  ok('生成按钮文案正确', has(memeHtml, 'Rave'));
} catch (err) {
  ok('MemeRave 渲染', false, String(err));
  console.log(err);
}

console.log(`\n${'='.repeat(52)}`);
if (failures.length === 0) {
  console.log(`ALL PASS — ${passed} 项断言全绿`);
} else {
  console.log(`FAIL — ${passed} 通过 / ${failures.length} 失败`);
  for (const f of failures) console.log('  ✗ ' + f);
  process.exitCode = 1;
}

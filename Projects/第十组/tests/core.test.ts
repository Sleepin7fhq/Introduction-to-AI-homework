/**
 * 无浏览器核心测试：用 esbuild 打成 IIFE 后由 node 直接跑。
 * 覆盖解析 → 生成 → 编曲 → MIDI → 后端适配 这条主链路。
 */

import { parsePrompt, applyOverrides, keyName } from '../src/producer/parse';
import { findMemes, fallbackCard, memeToPrompt, raveScript } from '../src/producer/meme';
import { composeSongEx } from '../src/music/generate';
import { arrangeSong, planRave, phaseAt, energyAtBar } from '../src/music/arrange';
import { songToMidi } from '../src/music/export';
import { localBackend } from '../src/engine/backends';

let passed = 0;
const failures: string[] = [];

function ok(name: string, cond: boolean, detail = ''): void {
  if (cond) {
    passed += 1;
    console.log(`  ✓ ${name}${detail ? '  ' + detail : ''}`);
  } else {
    failures.push(`${name}${detail ? '  → ' + detail : ''}`);
    console.log(`  ✗ ${name}${detail ? '  → ' + detail : ''}`);
  }
}

function section(title: string): void {
  console.log(`\n[${title}]`);
}

async function main(): Promise<void> {
  section('1. 自然语言解析');
  {
    const p = parsePrompt('做一个 techno，126bpm，16 小节，凌晨的地下室，很燥');
    ok('流派命中 techno', p.genre.id === 'techno', p.genre.name);
    ok('BPM 显式 126', p.bpm === 126, String(p.bpm));
    ok('小节数显式 16', p.bars === 16, String(p.bars));
    ok('置信度 > 0.6', p.confidence > 0.6, p.confidence.toFixed(2));
    ok('有可解释推理', p.reasoning.length >= 2, `${p.reasoning.length} 条`);
    ok('时长换算合理', Math.abs(p.durationSec - (16 * 4 * 60) / 126) < 2, `${p.durationSec}s`);
  }
  {
    const p = parsePrompt('下雨的深夜，一个人在窗边');
    ok('未点名流派时自动推断', p.genreExplicit === false, p.genre.name);
    ok('BPM 落在合理区间', p.bpm >= 60 && p.bpm <= 110, String(p.bpm));
    ok('识别为小调情绪', p.mode === 'minor', p.mode);
  }
  {
    const p = parsePrompt('来一段 2 分钟的 house');
    ok('按秒数折算小节', p.bars >= 8 && p.bars <= 64, `${p.bars} 小节`);
    ok('折算后时长回到 120 秒', Math.abs(p.durationSec - 120) <= 3, `${p.durationSec}s`);
  }
  {
    const p = parsePrompt('C 小调的电影感配乐');
    ok('解析出调性', p.mode === 'minor' && keyName(0, p.mode).includes('C'), keyName(0, p.mode));
  }
  {
    const base = parsePrompt('随便来点');
    const over = applyOverrides(base, { styleId: 'dnb', bpm: 175, bars: 24, energy: 0.9 });
    ok('手动覆盖流派生效', over.genre.id === 'dnb', over.genre.name);
    ok('手动覆盖 BPM 生效', over.bpm === 175, String(over.bpm));
    ok('手动覆盖小节生效', over.bars === 24, String(over.bars));
  }

  section('2. Meme-to-Rave 梗库');
  {
    const hits = findMemes('早八起不来，地铁上挤成照片');
    ok('命中「早八打工人」', hits.length > 0 && hits[0].id === 'zaoba', hits[0]?.name ?? '无');
    const card = hits[0];
    ok('给出的 BPM 合理', card.bpm >= 90 && card.bpm <= 190, String(card.bpm));
    const prompt = memeToPrompt(card);
    ok('梗可翻译成引擎提示词', prompt.length > 10 && prompt.includes('techno'), prompt.slice(0, 40) + '…');
    const steps = raveScript(card, 16);
    ok('演示剧本覆盖 Drop', steps.some((s) => s.label === 'Drop'), `${steps.length} 步`);
  }
  {
    const a = fallbackCard('我家猫把键盘踩出了和弦');
    const b = fallbackCard('我家猫把键盘踩出了和弦');
    ok('兜底卡片确定性', a.id === b.id && a.bpm === b.bpm, a.id);
    ok('兜底也有完整方案', a.why.length > 10 && a.tags.length >= 3, a.tags.join('/'));
  }
  {
    const hits = findMemes('整顿职场，老板画的饼我不吃了');
    ok('多关键词排序', hits[0]?.id === 'zhengdun', hits[0]?.name ?? '无');
  }

  section('3. 受约束作曲');
  {
    const song = composeSongEx('techno 深夜 128bpm', { bars: 16, tempo: 128 });
    ok('小节数正确', song.chords.length === 16, String(song.chords.length));
    ok('BPM 覆盖生效', song.tempo === 128, String(song.tempo));
    const notes = song.tracks.reduce((a, t) => a + t.clips.reduce((b, c) => b + c.notes.length, 0), 0);
    ok('音符数量充足', notes > 100, `${notes} notes`);
    ok('鼓/贝斯/和声三件套齐全', ['drums', 'bass', 'keys'].every((k) => song.tracks.some((t) => t.kind === k)));
    const pitches = song.tracks.flatMap((t) => t.clips.flatMap((c) => c.notes.map((n) => n.pitch)));
    ok('音高在合法 MIDI 范围', pitches.every((p) => p >= 0 && p <= 127), `${Math.min(...pitches)}–${Math.max(...pitches)}`);
  }
  {
    const a = composeSongEx('house 122bpm 快乐', { bars: 8, tempo: 122, salt: 'x' });
    const b = composeSongEx('house 122bpm 快乐', { bars: 8, tempo: 122, salt: 'x' });
    const sig = (s: typeof a) =>
      JSON.stringify(s.tracks.map((t) => t.clips[0].notes.map((n) => [n.pitch, n.start, n.vel])));
    ok('同种子可复现', sig(a) === sig(b));
  }

  section('4. 段落编排');
  {
    const raw = composeSongEx('techno 高能 128bpm', { bars: 16, tempo: 128 });
    const plan = planRave(16, 0.9);
    const arranged = arrangeSong(raw, plan);
    ok('段落划分完整', arranged.sections.length >= 4, arranged.sections.map((s) => s.name).join('→'));
    ok('阶段判定正确', phaseAt(plan, 0) === 'intro' && phaseAt(plan, 8) === 'drop');
    ok('能量曲线有起伏', energyAtBar(plan, 0) < energyAtBar(plan, 8), `${energyAtBar(plan, 0)} → ${energyAtBar(plan, 8)}`);

    const drums = arranged.tracks.find((t) => t.kind === 'drums')!;
    const introNotes = drums.clips[0].notes.filter((n) => n.start < 4 * 4);
    const introHats = introNotes.filter((n) => n.pitch === 42 || n.pitch === 46);
    ok('前奏只留底鼓（无踩镲）', introHats.length === 0, `${introNotes.length} notes`);

    const dropNotes = drums.clips[0].notes.filter((n) => n.start >= 8 * 4 && n.start < 12 * 4);
    ok('Drop 段鼓组饱满', dropNotes.length > 30, `${dropNotes.length} notes`);

    const all = arranged.tracks.flatMap((t) => t.clips[0].notes.map((n) => ({ t: t.kind, s: n.start })));
    const vacuum = all.filter((n) => n.s >= 7 * 4 + 3 && n.s < 8 * 4);
    ok('Drop 前最后一拍真空', vacuum.length === 0, `${vacuum.length} notes`);
    ok('存在 riser 轨', arranged.tracks.some((t) => t.id === 't-riser'));

    const lead = arranged.tracks.find((t) => t.kind === 'lead');
    ok('主旋律 Drop 才进', !!lead && lead.clips[0].notes.every((n) => n.start >= 8 * 4), lead ? `${lead.clips[0].notes.length} notes` : '无 lead');
  }

  section('5. MIDI 导出');
  {
    const song = composeSongEx('trap 140bpm', { bars: 8, tempo: 140 });
    const bytes = songToMidi(song);
    const head = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]);
    ok('MThd 头正确', head === 'MThd', head);
    ok('MTrk 存在', String.fromCharCode(bytes[14], bytes[15], bytes[16], bytes[17]) === 'MTrk');
    ok('文件大小合理', bytes.length > 500, `${bytes.length} bytes`);
    const headerTracks = (bytes[10] << 8) | bytes[11];
    ok('轨数 = 1 + 音轨数', headerTracks === song.tracks.length + 1, `${headerTracks}`);
  }

  section('6. 生成后端');
  {
    const status = await localBackend.probe();
    ok('本地后端可用', status.available, status.detail);
    const result = await localBackend.render({
      prompt: 'techno 凌晨 128bpm',
      intent: parsePrompt('techno 凌晨 128bpm 16小节'),
      mode: 'rave',
      seed: 42,
    });
    ok('返回符号歌曲而非音频', result.kind === 'symbolic' && !!result.song && !result.audio);
    ok('包含真实阶段耗时', result.stages.length === 3 && result.stages.every((s) => s.ms >= 0), result.stages.map((s) => `${s.label}:${s.ms}ms`).join(' | '));
    ok('报告总耗时', result.totalMs >= 0, `${result.totalMs}ms`);
  }

  console.log(`\n${'='.repeat(52)}`);
  if (failures.length === 0) {
    console.log(`ALL PASS — ${passed} 项断言全绿`);
  } else {
    console.log(`FAIL — ${passed} 通过 / ${failures.length} 失败`);
    for (const f of failures) console.log('  ✗ ' + f);
    process.exitCode = 1;
  }
}

void main().catch((err) => {
  console.error('\n测试崩溃：', err);
  process.exitCode = 1;
});

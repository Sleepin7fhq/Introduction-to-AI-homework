import { useEffect, useRef, useState } from 'react';
import { AudioTakeBar } from './components/AudioTakeBar';
import { ProducerPanel } from './components/ProducerPanel';
import { Timeline } from './components/Timeline';
import { TopBar } from './components/TopBar';
import { TrackList } from './components/TrackList';
import { Transport } from './components/Transport';
import { localBackend, pickBackend, probeAll } from './engine/backends';
import type { AudioTake, BackendId, BackendStatus } from './engine/backends';
import { BACKUP_TAKES } from './demo/backups';
import { downloadMidi } from './music/export';
import { GENRES } from './music/genre';
import type { GenreId } from './music/genre';
import { getPlayer } from './music/engine';
import { renderSongToWav } from './music/render';
import { getBank } from './audio/sampler';
import type { SongPlayer } from './music/engine';
import type { Song } from './music/types';
import { fallbackCard, findMemes, memeToPrompt } from './producer/meme';
import type { MemeCard } from './producer/meme';
import { applyOverrides, MOOD_OPTIONS, parsePrompt } from './producer/parse';
import type { ParsedIntent } from './producer/parse';
import type { ProducerMessage, TaskState } from './ui/model';

const EXAMPLES: Array<{ label: string; text: string; mode: 'song' | 'rave' }> = [
  { label: 'techno · 凌晨改代码', text: 'techno，凌晨两点还在改代码，128 BPM，要有压迫感', mode: 'song' },
  { label: 'synthwave · 雨夜回家', text: 'synthwave，下雨的深夜，一个人开车回家，100 BPM', mode: 'song' },
  { label: 'Meme · 早八打工人', text: '早八打工人', mode: 'rave' },
];

export default function App() {
  const [projectName, setProjectName] = useState('未命名工程');
  const [prompt, setPrompt] = useState('techno，凌晨两点还在改代码，128 BPM，要有压迫感');
  const [styleId, setStyleId] = useState<GenreId | 'auto'>('auto');
  const [moodId, setMoodId] = useState('auto');
  const [bpmOverride, setBpmOverride] = useState<number | 'auto'>('auto');
  const [barsOverride, setBarsOverride] = useState<number | 'auto'>('auto');
  const [energy, setEnergy] = useState(0.7);
  const [mode, setMode] = useState<'song' | 'rave'>('song');

  const [song, setSong] = useState<Song | null>(null);
  const [audioTake, setAudioTake] = useState<AudioTake | null>(null);
  const [intent, setIntent] = useState<ParsedIntent | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  const [statuses, setStatuses] = useState<BackendStatus[]>([]);
  const [backend, setBackend] = useState<BackendId>('local-symbolic');
  const [probing, setProbing] = useState(false);

  const [generating, setGenerating] = useState(false);
  const [task, setTask] = useState<TaskState | null>(null);
  const [messages, setMessages] = useState<ProducerMessage[]>([]);

  const [playing, setPlaying] = useState(false);
  const [bar, setBar] = useState(0);
  const [audioBlocked, setAudioBlocked] = useState(false);

  const [memeQuery, setMemeQuery] = useState('');
  const [memeHits, setMemeHits] = useState<MemeCard[]>([]);
  const [memePick, setMemePick] = useState<MemeCard | null>(null);

  const msgId = useRef(1);
  const seed = useRef(1);
  const playerRef = useRef<SongPlayer | null>(null);
  const lastPrompt = useRef(prompt);

  function pushMessage(m: Omit<ProducerMessage, 'id'>) {
    const msg: ProducerMessage = { ...m, id: msgId.current++ };
    setMessages((prev) => [...prev.slice(-24), msg]);
  }

  function player(): SongPlayer {
    if (!playerRef.current) {
      const p = getPlayer();
      p.onBar = (b) => setBar(b);
      playerRef.current = p;
    }
    return playerRef.current;
  }

  useEffect(() => {
    let cancelled = false;
    setProbing(true);
    void probeAll().then((list) => {
      if (cancelled) return;
      setStatuses(list);
      setProbing(false);
      const ace = list.find((s) => s.id === 'ace-step');
      if (ace?.available) {
        setBackend('ace-step');
        pushMessage({
          role: 'producer',
          text: '检测到本机 ACE-Step 服务已就绪，已自动切换到它。',
          meta: ace.detail,
        });
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  async function reprobe() {
    setProbing(true);
    const list = await probeAll();
    setStatuses(list);
    setProbing(false);
  }

  function loadSong(next: Song) {
    const p = player();
    if (p.isPlaying) {
      p.stop();
      setPlaying(false);
    }
    p.setSong(next);
    setSong(next);
  }

  /**
   * 真正的生成流程：解析 → 后端渲染（含段落编排）→ 装载到工作站。
   * 所有耗时都是实测的，没有人为 sleep。
   */
  async function generate(opts: {
    reqMode: 'song' | 'rave';
    meme?: MemeCard | null;
    text?: string;
  }) {
    if (generating) return;
    const rawText = (opts.text ?? lastPrompt.current ?? prompt).trim() || prompt;
    const moodKeywords = MOOD_OPTIONS.find((m) => m.id === moodId)?.keywords ?? '';
    const composedText = moodKeywords ? `${rawText}，${moodKeywords}` : rawText;

    let parsed = parsePrompt(composedText);
    if (opts.meme) {
      const g = GENRES.find((x) => x.id === opts.meme!.genreId);
      parsed = {
        ...parsed,
        ...(g ? { genre: g, genreExplicit: true } : {}),
        bpm: opts.meme.bpm,
        bars: 16,
        energy: opts.meme.energy,
        density: opts.meme.density,
        title: opts.meme.name,
        intent: 'meme',
      };
    }

    const finalIntent = applyOverrides(parsed, {
      styleId: opts.meme ? opts.meme.genreId : styleId,
      bpm: opts.meme ? opts.meme.bpm : bpmOverride,
      bars: typeof barsOverride === 'number' ? barsOverride : opts.meme ? 16 : 'auto',
      energy: opts.meme ? opts.meme.energy : energy,
    });
    setIntent(finalIntent);

    const humanText =
      opts.reqMode === 'rave' && opts.meme ? `把「${opts.meme.name}」做成一段 Rave` : rawText;
    pushMessage({ role: 'user', text: humanText });
    lastPrompt.current = rawText;

    setGenerating(true);
    setTask({ running: true, label: '正在解析描述…', stages: [] });

    try {
      const be = pickBackend(statuses, backend);
      const result = await be.render({
        prompt: composedText,
        intent: finalIntent,
        mode: opts.reqMode,
        seed: seed.current++,
      });

      setTask({
        running: false,
        label: `${be.label} · ${result.totalMs}ms`,
        stages: result.stages,
      });

      if (result.song) {
        loadSong(result.song);
        setAudioTake(null);
        setSelected(result.song.tracks[0]?.id ?? null);
        if (projectName === '未命名工程') setProjectName(result.song.title);
        const genreTxt = `${finalIntent.genre.name} / ${finalIntent.mode === 'major' ? '大调' : '小调'} / ${finalIntent.bpm} BPM / ${finalIntent.bars} 小节`;
        pushMessage({
          role: 'producer',
          text: opts.meme
            ? `做好了：一首「${opts.meme.name}」的 ${finalIntent.genre.name}。${opts.meme.why}`
            : `生成了 ${finalIntent.bars} 小节的 ${finalIntent.genre.name}，按 ${finalIntent.bpm} BPM 播放。`,
          bullets: [...result.notes, ...finalIntent.reasoning].slice(0, 5),
          meta: `${result.backend} · ${result.totalMs}ms · ${genreTxt}`,
        });
      } else if (result.audio) {
        setAudioTake(result.audio);
        setTask({
          running: false,
          label: `ACE-Step 音频 · ${result.totalMs}ms`,
          stages: result.stages,
        });
        pushMessage({
          role: 'producer',
          text: '本机模型返回了一段音频，已放在时间轴上方。它是音频，不是可编辑的谱面。',
          bullets: result.notes,
          meta: `${result.backend} · ${result.totalMs}ms`,
        });
      }
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      setTask({ running: false, label: '生成失败', stages: [], error: detail });
      pushMessage({
        role: 'producer',
        text: `这台后端没能完成生成：${detail}`,
        bullets: ['没有用假结果顶替', '可以切到「本地符号引擎」立刻继续'],
        meta: 'error',
      });
    } finally {
      setGenerating(false);
    }
  }

  async function handlePlay() {
    if (!song) return;
    const p = player();
    if (p.isPlaying) {
      p.stop();
      setPlaying(false);
      return;
    }
    p.setSong(song);
    p.ensureAudio();
    try {
      await p.play();
      setPlaying(true);
      setAudioBlocked(false);
    } catch (err) {
      setAudioBlocked(true);
      pushMessage({
        role: 'producer',
        text: `浏览器拦住了音频：${err instanceof Error ? err.message : String(err)}`,
      });
    }
  }

  function handleStop() {
    if (!playerRef.current) return;
    playerRef.current.stop();
    setPlaying(false);
    setBar(0);
  }

  // 空格键播放/停止：讲课时手不用离开键盘
  const playShortcut = useRef<() => void>(() => {});
  playShortcut.current = () => {
    void handlePlay();
  };
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (e.code === 'Space') {
        e.preventDefault();
        playShortcut.current();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  function handleBpm(v: number) {
    setBpmOverride(v);
    if (song) {
      const next = { ...song, tempo: v };
      setSong(next);
      if (playerRef.current) playerRef.current.setSong(next);
    }
  }

  function handleFollowUp(text: string) {
    pushMessage({ role: 'user', text });
    const modifier = text.length <= 10;
    const combined = modifier ? `${lastPrompt.current}，${text}` : text;
    setPrompt(combined);
    void generate({ reqMode: 'song', text: combined });
  }

  function handleFindMeme() {
    const q = memeQuery.trim();
    if (!q) return;
    const hits = findMemes(q, 3);
    if (hits.length === 0) {
      const custom = fallbackCard(q);
      setMemeHits([custom]);
      setMemePick(custom);
      return;
    }
    setMemeHits(hits);
    setMemePick(hits[0]);
  }

  function runExample(ex: (typeof EXAMPLES)[number]) {
    setPrompt(ex.text);
    lastPrompt.current = ex.text;
    if (ex.mode === 'rave') {
      setMode('rave');
      const hits = findMemes(ex.text, 3);
      const card = hits[0] ?? fallbackCard(ex.text);
      setMemeQuery(ex.text);
      setMemeHits(hits.length ? hits : [card]);
      setMemePick(card);
      void generate({ reqMode: 'rave', meme: card, text: memeToPrompt(card) });
    } else {
      setMode('song');
      void generate({ reqMode: 'song', text: ex.text });
    }
  }


  // 离线渲染钩子：把当前风格渲染成 WAV 并下载。
  // 供脚本生成对比样本使用（脚本里会设置下载目录），也方便手动导出。
  useEffect(() => {
    (window as unknown as Record<string, unknown>).__dshRender = async (
      prompt: string,
      styleId: string,
      bars = 16,
    ) => {
      const parsed = parsePrompt(prompt);
      const intent = applyOverrides(parsed, {
        styleId: styleId as never,
        bpm: 'auto',
        bars,
        energy: 0.8,
      });
      const res = await localBackend.render({ prompt, intent, mode: 'rave', seed: 7 });
      if (!res.song) throw new Error('offline render: no song');
      const blob = await renderSongToWav(res.song);
      const name = `${styleId}_${bars}bars.wav`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      const bank = getBank();
      return {
        name,
        bytes: blob.size,
        bars,
        tempo: res.song.tempo,
        tracks: res.song.tracks.length,
        kit: res.song.soundKit ?? null,
        samplesReady: bank.isReady(),
        sampleCount: bank.manifest?.count ?? 0,
      };
    };
  }, []);
  const currentBpm = song?.tempo ?? (intent?.bpm ?? (bpmOverride === 'auto' ? 120 : bpmOverride));
  const currentBars = song?.bars ?? (intent?.bars ?? 16);

  return (
    <div className="app">
      <TopBar
        projectName={projectName}
        onProjectName={setProjectName}
        statuses={statuses}
        backend={backend}
        onBackend={setBackend}
        onReprobe={() => void reprobe()}
        probing={probing}
        onExport={() => song && downloadMidi(song)}
        canExport={!!song}
        onOpenSelftest={() => {
          window.location.href = '?selftest=1';
        }}
      />

      <div className="workspace">
        {song ? (
          <TrackList
            song={song}
            selected={selected}
            onSelect={setSelected}
            onPatch={(id, patch) => {
              setSong((prev) => {
                if (!prev) return prev;
                const next = {
                  ...prev,
                  tracks: prev.tracks.map((t) => (t.id === id ? { ...t, ...patch } : t)),
                };
                playerRef.current?.setSong(next);
                return next;
              });
            }}
          />
        ) : (
          <aside className="tracklist empty">
            <div className="panel-head">
              <span>音轨</span>
            </div>
            <p className="empty-hint">生成之后，这里会出现鼓组、贝斯、和声、主音等轨道。</p>
          </aside>
        )}

        <main className={`stage ${audioTake && !song ? 'has-audio' : ''}`}>
          {audioTake && (
            <AudioTakeBar
              take={audioTake}
              backendLabel={statuses.find((s) => s.id === 'ace-step')?.label ?? 'ACE-Step'}
            />
          )}

          {song ? (
            <Timeline song={song} selected={selected} onSelect={setSelected} playing={playing} bar={bar} />
          ) : (
            <div className="hero">
              <div className="hero-kicker">DSH STUDIO 2.0</div>
              <h1 className="hero-title">一句话，做一首能蹦的歌</h1>
              <p className="hero-sub">
                解析描述 → 受约束作曲 → 段落编排 → Web Audio 实时合成。生成的每一轨都是可编辑的音符，不是一段黑盒音频。
              </p>
              <div className="hero-actions">
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex.label}
                    className="example-btn"
                    onClick={() => runExample(ex)}
                    disabled={generating}
                    type="button"
                  >
                    {ex.label}
                  </button>
                ))}
              </div>
              <p className="tiny dim">
                右边也可以直接写描述，或切到 Meme-to-Rave，用一个生活梗开场。
              </p>
            </div>
          )}
        </main>

        <ProducerPanel
          mode={mode}
          onMode={setMode}
          prompt={prompt}
          onPrompt={setPrompt}
          styleId={styleId}
          onStyleId={setStyleId}
          moodId={moodId}
          onMoodId={setMoodId}
          bpmOverride={bpmOverride}
          onBpmOverride={setBpmOverride}
          barsOverride={barsOverride}
          onBarsOverride={setBarsOverride}
          energy={energy}
          onEnergy={setEnergy}
          intent={intent}
          statuses={statuses}
          backend={backend}
          onBackend={setBackend}
          generating={generating}
          task={task}
          messages={messages}
          onGenerate={() => void generate({ reqMode: mode })}
          onFollowUp={handleFollowUp}
          meme={{
            query: memeQuery,
            onQuery: setMemeQuery,
            hits: memeHits,
            pick: memePick,
            onPick: setMemePick,
            onGenerate: () => {
              if (!memePick) return;
              void generate({ reqMode: 'rave', meme: memePick, text: memeToPrompt(memePick) });
            },
            onFind: handleFindMeme,
          }}
          bars={typeof barsOverride === 'number' ? barsOverride : (intent?.bars ?? 16)}
          backups={BACKUP_TAKES}
          onPlayBackup={(b) => {
            setAudioTake({
              url: b.url,
              mime: 'audio/wav',
              echoedPrompt: b.label,
              durationSec: b.durationSec,
            });
            pushMessage({
              role: 'producer',
              text: `播放预生成素材「${b.label}」——这是 ACE-Step 真实生成的音频，不是符号引擎。`,
              meta: b.url,
            });
          }}
        />
      </div>

      <Transport
        playing={playing}
        bar={bar}
        bpm={currentBpm}
        bars={currentBars}
        onPlay={() => void handlePlay()}
        onStop={handleStop}
        onBpm={handleBpm}
        hasSong={!!song}
        audioBlocked={audioBlocked}
      />
    </div>
  );
}

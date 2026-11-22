import type { ParsedIntent } from '../producer/parse';
import type { GenreSpec } from '../music/genre';
import { composeSongEx } from '../music/generate';
import { arrangeSong, planRave, planSong } from '../music/arrange';
import type { Song } from '../music/types';

/**
 * 生成后端适配层。
 *
 * 三个后端，状态全部是实时探测出来的，界面上不美化：
 *   local-symbolic : 本项目内置的受约束符号生成器 —— 真正在跑，离线可用
 *   ace-step       : 本机 ACE-Step 1.5 服务（127.0.0.1:8000），探到才可用
 *   suno-mcp       : Suno MCP 通道，需要凭据；没配就是不可用
 *
 * 关键原则：不伪装。local 后端产出的是"算法作曲"，不是神经模型生成的音频；
 * 只有 ace-step 真正返回音频时，界面才会标成「AI 音频生成」。
 */

export type BackendId = 'local-symbolic' | 'ace-step' | 'suno-mcp';

export type BackendKind = 'local' | 'local-model' | 'cloud';

export interface BackendStatus {
  id: BackendId;
  label: string;
  kind: BackendKind;
  available: boolean;
  /** 一句话说明：为什么可用 / 为什么不可用 */
  detail: string;
  /** 探测耗时 */
  probeMs: number;
}

export interface AudioTake {
  url: string;
  mime: string;
  /** 生成服务给的原始 prompt 回执 */
  echoedPrompt: string;
  durationSec: number;
}

export interface RenderStage {
  label: string;
  ms: number;
}

export interface RenderResult {
  kind: 'symbolic' | 'audio';
  backend: BackendId;
  /** 符号生成时一定存在；音频生成时为 null（不伪造 MIDI 结构） */
  song: Song | null;
  audio: AudioTake | null;
  stages: RenderStage[];
  notes: string[];
  totalMs: number;
}

export interface RenderRequest {
  prompt: string;
  intent: ParsedIntent;
  mode: 'song' | 'rave';
  seed?: number;
}

export interface GenerationBackend {
  id: BackendId;
  label: string;
  kind: BackendKind;
  probe(): Promise<BackendStatus>;
  render(req: RenderRequest): Promise<RenderResult>;
}

const ACE_BASE = 'http://127.0.0.1:8000';

function now(): number {
  return typeof performance !== 'undefined' ? performance.now() : Date.now();
}

function genreKeyword(genre: GenreSpec): string {
  return genre.keywords[0] ?? genre.name;
}

async function fetchWithTimeout(url: string, init: RequestInit, ms: number): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  try {
    return await fetch(url, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

/* ------------------------------------------------------------------ */
/* 1. 本地符号引擎（真实可用）                                          */
/* ------------------------------------------------------------------ */

export const localBackend: GenerationBackend = {
  id: 'local-symbolic',
  label: '本地符号引擎',
  kind: 'local',

  async probe() {
    const t0 = now();
    return {
      id: 'local-symbolic',
      label: '本地符号引擎',
      kind: 'local',
      available: true,
      detail: '内置受约束作曲 + Web Audio 合成器 · 离线可用',
      probeMs: Math.round(now() - t0),
    };
  },

  async render(req) {
    const stages: RenderStage[] = [];
    const notes: string[] = [];

    let t = now();
    // 流派关键词置前，确保 matchGenre 命中用户/梗指定的编制
    const text = `${genreKeyword(req.intent.genre)} ${req.prompt}`;
    const seedSalt = `#${req.seed ?? 0}`;
    stages.push({ label: '准备生成上下文', ms: Math.round(now() - t) });
    notes.push(`流派锚点：${req.intent.genre.name}；调式：${req.intent.mode === 'major' ? '大调' : '小调'}`);

    t = now();
    const raw = composeSongEx(text, {
      bars: req.intent.bars,
      tempo: req.intent.bpm,
      salt: seedSalt,
      title: req.intent.title,
      genre: req.intent.genre,
    });
    stages.push({ label: '受约束作曲（和声 / 旋律 / 鼓型）', ms: Math.round(now() - t) });

    t = now();
    const plan = req.mode === 'rave' ? planRave(raw.bars, req.intent.energy) : planSong(raw.bars, req.intent.energy);
    const arranged = arrangeSong(raw, plan);
    stages.push({ label: '段落编排（进 / 抽 / Drop）', ms: Math.round(now() - t) });

    const noteCount = arranged.tracks.reduce(
      (a, tr) => a + tr.clips.reduce((b, c) => b + c.notes.length, 0),
      0,
    );
    notes.push(`共 ${arranged.tracks.length} 轨 / ${noteCount} 个音符 / ${arranged.bars} 小节`);
    notes.push(`音色：${arranged.tracks.map((x) => x.name).join('、')}`);

    return {
      kind: 'symbolic',
      backend: 'local-symbolic',
      song: {
        ...arranged,
        style: arranged.style
          ? { ...arranged.style, bpm: arranged.tempo, name: req.intent.moodName }
          : arranged.style,
      },
      audio: null,
      stages,
      notes,
      totalMs: Math.round(stages.reduce((a, s) => a + s.ms, 0)),
    };
  },
};

/* ------------------------------------------------------------------ */
/* 2. ACE-Step 本机服务                                                 */
/* ------------------------------------------------------------------ */

export const aceBackend: GenerationBackend = {
  id: 'ace-step',
  label: 'ACE-Step 1.5（本机）',
  kind: 'local-model',

  async probe() {
    const t0 = now();
    try {
      const res = await fetchWithTimeout(`${ACE_BASE}/health`, { method: 'GET' }, 1500);
      const ms = Math.round(now() - t0);
      if (!res.ok) {
        return {
          id: 'ace-step',
          label: 'ACE-Step 1.5（本机）',
          kind: 'local-model',
          available: false,
          detail: `服务在 8000 端口有响应但返回 HTTP ${res.status}`,
          probeMs: ms,
        };
      }
      const body = (await res.json().catch(() => ({}))) as {
        status?: string;
        model?: string;
        error?: string | null;
        load_seconds?: number;
      };
      const status = body.status ?? 'unknown';
      if (status !== 'ready') {
        return {
          id: 'ace-step',
          label: 'ACE-Step 1.5（本机）',
          kind: 'local-model',
          available: false,
          detail:
            status === 'loading'
              ? '模型正在加载（首次约 1–2 分钟），稍后点「重新探测」'
              : `服务在线但模型未就绪：${body.error ?? status}`,
          probeMs: ms,
        };
      }
      return {
        id: 'ace-step',
        label: 'ACE-Step 1.5（本机）',
        kind: 'local-model',
        available: true,
        detail: `已就绪 · ${body.model ?? 'model'} · 加载 ${body.load_seconds ?? '?'}s`,
        probeMs: ms,
      };
    } catch (err) {
      const ms = Math.round(now() - t0);
      const aborted = err instanceof Error && err.name === 'AbortError';
      return {
        id: 'ace-step',
        label: 'ACE-Step 1.5（本机）',
        kind: 'local-model',
        available: false,
        detail: aborted ? '探测超时：8000 端口无响应' : '未检测到本机服务（需要 ACE-Step 推理服务）',
        probeMs: ms,
      };
    }
  },

  async render(req) {
    const t = now();
    const duration = Math.max(4, Math.min(30, req.intent.durationSec));
    const res = await fetchWithTimeout(
      `${ACE_BASE}/generate`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: req.prompt,
          duration,
          bpm: req.intent.bpm,
          tags: req.intent.tags,
        }),
      },
      240_000,
    );
    if (!res.ok) {
      throw new Error(`ACE-Step 返回 HTTP ${res.status}：${(await res.text()).slice(0, 200)}`);
    }
    const body = (await res.json()) as {
      audio_url?: string;
      url?: string;
      base64?: string;
      duration?: number;
      generate_seconds?: number;
      peak_vram_gb?: number;
    };
    const raw = body.audio_url ?? body.url;
    // 服务返回的是相对路径（/audio/xxx.wav），必须补上服务源，否则会打到前端静态服务器上 404
    const abs = (u: string) => (u.startsWith('/') ? `${ACE_BASE}${u}` : u);
    const audio: AudioTake | null = raw
      ? { url: abs(raw), mime: 'audio/wav', echoedPrompt: req.prompt, durationSec: body.duration ?? duration }
      : body.base64
        ? {
            url: `data:audio/wav;base64,${body.base64}`,
            mime: 'audio/wav',
            echoedPrompt: req.prompt,
            durationSec: body.duration ?? duration,
          }
        : null;
    if (!audio) throw new Error('ACE-Step 响应里没有 audio_url / base64 字段');
    return {
      kind: 'audio',
      backend: 'ace-step',
      song: null,
      audio,
      stages: [
        {
          label: `ACE-Step 推理（${body.peak_vram_gb ?? '?'}GB 峰值显存）`,
          ms: Math.round(now() - t),
        },
      ],
      notes: [
        '音频由本机 ACE-Step 1.5 turbo 生成（float32 / 48kHz，真实波形）',
        '音频没有音符结构，因此时间轴不可编辑——不伪造 MIDI',
      ],
      totalMs: Math.round(now() - t),
    };
  },
};

/* ------------------------------------------------------------------ */
/* 3. Suno MCP（需要凭据，当前不可用）                                   */
/* ------------------------------------------------------------------ */

export const sunoBackend: GenerationBackend = {
  id: 'suno-mcp',
  label: 'Suno（MCP）',
  kind: 'cloud',

  async probe() {
    const t0 = now();
    return {
      id: 'suno-mcp',
      label: 'Suno（MCP）',
      kind: 'cloud',
      available: false,
      detail: 'MCP 通道未连接 / 未配置凭据，本环境无法调用（不尝试绕过）',
      probeMs: Math.round(now() - t0),
    };
  },

  async render() {
    throw new Error('Suno 后端不可用：未配置凭据。');
  },
};

export const BACKENDS: GenerationBackend[] = [localBackend, aceBackend, sunoBackend];

/** 并行探测所有后端，界面启动时调用 */
export async function probeAll(): Promise<BackendStatus[]> {
  return Promise.all(BACKENDS.map((b) => b.probe()));
}

/** 拿到第一个真正可用的后端；都不可用则回退到本地 */
export function pickBackend(statuses: BackendStatus[], preferred: BackendId): GenerationBackend {
  const status = statuses.find((s) => s.id === preferred);
  if (status?.available) {
    const b = BACKENDS.find((x) => x.id === preferred);
    if (b) return b;
  }
  return localBackend;
}

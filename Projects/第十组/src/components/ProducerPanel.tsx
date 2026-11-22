import type { BackendId, BackendStatus } from '../engine/backends';
import type { GenreId } from '../music/genre';
import type { MemeCard } from '../producer/meme';
import type { ParsedIntent } from '../producer/parse';
import { MOOD_OPTIONS, STYLE_OPTIONS, keyName } from '../producer/parse';
import type { ProducerMessage, TaskState } from '../ui/model';
import { MemeRave } from './MemeRave';

interface Props {
  mode: 'song' | 'rave';
  onMode: (v: 'song' | 'rave') => void;
  prompt: string;
  onPrompt: (v: string) => void;
  styleId: GenreId | 'auto';
  onStyleId: (v: GenreId | 'auto') => void;
  moodId: string;
  onMoodId: (v: string) => void;
  bpmOverride: number | 'auto';
  onBpmOverride: (v: number | 'auto') => void;
  barsOverride: number | 'auto';
  onBarsOverride: (v: number | 'auto') => void;
  energy: number;
  onEnergy: (v: number) => void;
  intent: ParsedIntent | null;
  statuses: BackendStatus[];
  backend: BackendId;
  onBackend: (v: BackendId) => void;
  generating: boolean;
  task: TaskState | null;
  messages: ProducerMessage[];
  onGenerate: () => void;
  onFollowUp: (text: string) => void;
  /** 预生成的真实 AI 音频（服务不可用时的备用演示素材） */
  backups?: Array<{ id: string; label: string; hint: string; url: string; durationSec: number }>;
  onPlayBackup?: (b: { id: string; label: string; hint: string; url: string; durationSec: number }) => void;
  meme: {
    query: string;
    onQuery: (v: string) => void;
    hits: MemeCard[];
    pick: MemeCard | null;
    onPick: (c: MemeCard) => void;
    onGenerate: () => void;
    onFind: () => void;
  };
  bars: number;
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span className="chip">
      <span className="chip-k">{label}</span>
      <span className="chip-v">{value}</span>
    </span>
  );
}

export function ProducerPanel(p: Props) {
  const intent = p.intent;
  const activeStatus = p.statuses.find((s) => s.id === p.backend);

  return (
    <aside className="producer">
      <div className="panel-head">
        <span>AI Producer</span>
        <span className="tiny dim">解析 → 编曲 → 生成</span>
      </div>

      <div className="producer-scroll">
        <div className="mode-tabs">
          <button
            className={`mode-tab ${p.mode === 'song' ? 'on' : ''}`}
            onClick={() => p.onMode('song')}
            type="button"
          >
            创作模式
          </button>
          <button
            className={`mode-tab ${p.mode === 'rave' ? 'on' : ''}`}
            onClick={() => p.onMode('rave')}
            type="button"
          >
            Meme-to-Rave
          </button>
        </div>

        {p.mode === 'rave' ? (
          <MemeRave
            query={p.meme.query}
            onQuery={p.meme.onQuery}
            hits={p.meme.hits}
            pick={p.meme.pick}
            onPick={p.meme.onPick}
            onGenerate={p.meme.onGenerate}
            onFind={p.meme.onFind}
            generating={p.generating}
            bars={p.bars}
          />
        ) : (
          <>
            <label className="field-label" htmlFor="prompt">
              一句话描述你想要的音乐
            </label>
            <textarea
              id="prompt"
              className="prompt-box"
              value={p.prompt}
              onChange={(e) => p.onPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                  e.preventDefault();
                  p.onGenerate();
                }
              }}
              rows={4}
              spellCheck={false}
              placeholder="例：techno，凌晨两点还在改代码，128 BPM，要有点压迫感"
            />

            <div className="param-grid">
              <div className="param">
                <label className="tiny dim" htmlFor="style">
                  风格
                </label>
                <select
                  id="style"
                  className="mini-select wide"
                  value={p.styleId}
                  onChange={(e) => p.onStyleId(e.target.value as GenreId | 'auto')}
                >
                  {STYLE_OPTIONS.map((o) => (
                    <option key={o.id} value={o.id} title={o.hint}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="param">
                <label className="tiny dim" htmlFor="mood">
                  情绪
                </label>
                <select
                  id="mood"
                  className="mini-select wide"
                  value={p.moodId}
                  onChange={(e) => p.onMoodId(e.target.value)}
                >
                  {MOOD_OPTIONS.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="param">
                <label className="tiny dim" htmlFor="bpm">
                  BPM
                </label>
                <div className="param-row">
                  <input
                    id="bpm"
                    className="num-input"
                    type="number"
                    min={60}
                    max={190}
                    value={p.bpmOverride === 'auto' ? (intent?.bpm ?? 120) : p.bpmOverride}
                    onChange={(e) => p.onBpmOverride(parseInt(e.target.value, 10) || 120)}
                  />
                  <button
                    className={`toggle ${p.bpmOverride === 'auto' ? 'on' : ''}`}
                    onClick={() => p.onBpmOverride(p.bpmOverride === 'auto' ? (intent?.bpm ?? 120) : 'auto')}
                    type="button"
                    title="自动 = 由描述推断"
                  >
                    AUTO
                  </button>
                </div>
              </div>

              <div className="param">
                <label className="tiny dim" htmlFor="bars">
                  小节
                </label>
                <div className="param-row">
                  <input
                    id="bars"
                    className="num-input"
                    type="number"
                    min={2}
                    max={64}
                    value={p.barsOverride === 'auto' ? (intent?.bars ?? 16) : p.barsOverride}
                    onChange={(e) => p.onBarsOverride(parseInt(e.target.value, 10) || 16)}
                  />
                  <button
                    className={`toggle ${p.barsOverride === 'auto' ? 'on' : ''}`}
                    onClick={() => p.onBarsOverride(p.barsOverride === 'auto' ? (intent?.bars ?? 16) : 'auto')}
                    type="button"
                    title="自动 = 由描述推断"
                  >
                    AUTO
                  </button>
                </div>
              </div>

              <div className="param">
                <label className="tiny dim" htmlFor="energy">
                  能量 {Math.round(p.energy * 100)}
                </label>
                <input
                  id="energy"
                  className="slider"
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={p.energy}
                  onChange={(e) => p.onEnergy(parseFloat(e.target.value))}
                />
              </div>
            </div>

            <div className="engine-pick">
              <label className="tiny dim" htmlFor="engine">
                生成引擎
              </label>
              <select
                id="engine"
                className="mini-select wide"
                value={p.backend}
                onChange={(e) => p.onBackend(e.target.value as BackendId)}
              >
                {p.statuses.map((s) => (
                  <option key={s.id} value={s.id} disabled={!s.available}>
                    {s.label}
                    {s.available ? '' : '（不可用）'}
                  </option>
                ))}
              </select>
              {activeStatus && (
                <p className={`engine-detail ${activeStatus.available ? 'ok' : 'bad'}`}>
                  {activeStatus.detail} · 探测 {activeStatus.probeMs}ms
                </p>
              )}
            </div>

            <button className="primary-btn wide" onClick={p.onGenerate} disabled={p.generating} type="button">
              {p.generating ? '生成中…' : '生成音乐'}
            </button>

            {p.backups && p.backups.length > 0 && (
              <div className="backup-block">
                <div className="backup-head">
                  <span>预生成真实音频</span>
                  <span className="tiny dim">ACE-Step 已跑过 · 应急用</span>
                </div>
                {p.backups.map((b) => (
                  <button
                    key={b.id}
                    className="backup-item"
                    onClick={() => p.onPlayBackup?.(b)}
                    type="button"
                  >
                    <span className="bk-play">▶</span>
                    <span className="bk-label">{b.label}</span>
                    <span className="bk-hint">{b.hint}</span>
                  </button>
                ))}
                <p className="tiny dim">
                  这两条是模型真生成的 WAV（不是符号引擎），服务没起来时用它顶上。
                </p>
              </div>
            )}
          </>
        )}

        {intent && (
          <div className="parse-card">
            <div className="parse-head">
              <span>解析结果</span>
              <span className={`conf ${intent.confidence > 0.7 ? 'hi' : ''}`}>
                {(intent.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <div className="chips">
              <Chip label="流派" value={intent.genre.name} />
              <Chip label="情绪" value={intent.moodName} />
              <Chip label="调性" value={keyName(intent.keyTonic, intent.mode)} />
              <Chip label="BPM" value={String(intent.bpm)} />
              <Chip label="长度" value={`${intent.bars} 小节`} />
              <Chip label="约" value={`${intent.durationSec} 秒`} />
              <Chip label="密度" value={`${Math.round(intent.density * 100)}%`} />
            </div>
            <ul className="reasoning">
              {intent.reasoning.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        )}

        {p.task && (
          <div className={`task-card ${p.task.error ? 'bad' : ''}`}>
            <div className="task-head">
              <span className={`spinner ${p.task.running ? 'on' : ''}`} />
              <span>{p.task.error ?? p.task.label}</span>
            </div>
            <ul className="stages">
              {p.task.stages.map((s, i) => (
                <li key={i}>
                  <span className="st-label">{s.label}</span>
                  <span className="st-ms">{s.ms}ms</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="messages">
          {p.messages.length === 0 && (
            <p className="empty-hint">
              还没有生成过。写一句描述按「生成音乐」，或切到 Meme-to-Rave 用一个生活梗开场。
            </p>
          )}
          {p.messages.map((m) => (
            <div key={m.id} className={`msg ${m.role}`}>
              <div className="msg-role">{m.role === 'user' ? '你' : 'Producer'}</div>
              <div className="msg-text">{m.text}</div>
              {m.bullets && m.bullets.length > 0 && (
                <ul className="msg-bullets">
                  {m.bullets.map((b, i) => (
                    <li key={i}>{b}</li>
                  ))}
                </ul>
              )}
              {m.meta && <div className="msg-meta">{m.meta}</div>}
            </div>
          ))}
        </div>
      </div>

      <div className="follow-up">
        <input
          className="follow-input"
          placeholder="继续说：再快一点 / 换成 trap / 更燃"
          onKeyDown={(e) => {
            if (e.key !== 'Enter') return;
            const v = (e.target as HTMLInputElement).value.trim();
            if (!v) return;
            (e.target as HTMLInputElement).value = '';
            p.onFollowUp(v);
          }}
        />
      </div>
    </aside>
  );
}

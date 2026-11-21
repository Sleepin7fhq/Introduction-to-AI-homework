import type { MemeCard } from '../producer/meme';
import { raveScript } from '../producer/meme';

interface Props {
  query: string;
  onQuery: (v: string) => void;
  hits: MemeCard[];
  pick: MemeCard | null;
  onPick: (c: MemeCard) => void;
  onGenerate: () => void;
  generating: boolean;
  bars: number;
  onFind: () => void;
}

export function MemeRave({ query, onQuery, hits, pick, onPick, onGenerate, generating, bars, onFind }: Props) {
  return (
    <div className="meme">
      <div className="meme-head">
        <span className="meme-title">Meme → Rave</span>
        <span className="tiny dim">生活梗转电子乐 · 课堂演示模式</span>
      </div>

      <div className="meme-input-row">
        <input
          className="meme-input"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') onFind();
          }}
          placeholder="早八打工人 / 猫猫踩键盘 / 老板画的饼…"
          spellCheck={false}
        />
        <button className="ghost-btn" onClick={onFind} type="button">
          找
        </button>
      </div>

      {hits.length > 0 && (
        <div className="meme-cards">
          {hits.map((c) => (
            <button
              key={c.id}
              className={`meme-card ${pick?.id === c.id ? 'on' : ''}`}
              onClick={() => onPick(c)}
              type="button"
            >
              <div className="mc-top">
                <span className="mc-emoji">{c.emoji}</span>
                <span className="mc-name">{c.name}</span>
                <span className="mc-bpm">{c.bpm}</span>
              </div>
              <p className="mc-punch">{c.punchline}</p>
              <p className="mc-concept">{c.concept}</p>
              <div className="mc-tags">
                {c.tags.slice(0, 3).map((t) => (
                  <span key={t} className="tag">
                    {t}
                  </span>
                ))}
                {c.confidence && (
                  <span className={'conf-tag ' + c.confidence}>
                    {c.confidence === 'high' ? '已核实' : c.confidence === 'medium' ? '部分核实' : '待核实'}
                  </span>
                )}
                {c.sources && c.sources.length > 0 && (
                  <span className="tag dim">
                    {String(c.sources[0]).replace(/^https?:\/\//, '').split('/')[0]}
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {pick && (
        <div className="meme-detail">
          <div className="md-why">
            <span className="md-label">音乐上为什么成立</span>
            <p>{pick.why}</p>
          </div>
          <div className="md-palette">
            <span className="md-label">编制</span>
            <p>{pick.palette}</p>
          </div>
          <div className="md-script">
            <span className="md-label">演示剧本（{bars} 小节）</span>
            <ol>
              {raveScript(pick, bars).map((s) => (
                <li key={s.bar + s.label}>
                  <span className="scr-bar">{s.bar + 1}</span>
                  <span className="scr-label">{s.label}</span>
                  <span className="scr-line">{s.line}</span>
                </li>
              ))}
            </ol>
          </div>
          <button className="primary-btn wide" onClick={onGenerate} disabled={generating} type="button">
            {generating ? '正在生成…' : `生成「${pick.name}」Rave`}
          </button>
          <p className="tiny dim center">Drop 大屏文案：{pick.dropLine}</p>
        </div>
      )}
    </div>
  );
}

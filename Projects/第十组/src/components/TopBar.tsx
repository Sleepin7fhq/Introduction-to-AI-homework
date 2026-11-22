import type { BackendId, BackendStatus } from '../engine/backends';

interface Props {
  projectName: string;
  onProjectName: (v: string) => void;
  statuses: BackendStatus[];
  backend: BackendId;
  onBackend: (id: BackendId) => void;
  onReprobe: () => void;
  probing: boolean;
  onExport: () => void;
  canExport: boolean;
  onOpenSelftest: () => void;
}

export function TopBar({
  projectName,
  onProjectName,
  statuses,
  backend,
  onBackend,
  onReprobe,
  probing,
  onExport,
  canExport,
  onOpenSelftest,
}: Props) {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark" aria-hidden>
          ◉
        </span>
        <span className="brand-name">DSH STUDIO</span>
        <span className="brand-ver">2.0</span>
      </div>

      <div className="project">
        <label className="project-label" htmlFor="project-name">
          工程
        </label>
        <input
          id="project-name"
          className="project-input"
          value={projectName}
          onChange={(e) => onProjectName(e.target.value)}
          spellCheck={false}
          placeholder="未命名工程"
        />
      </div>

      <div className="engine-bar">
        {statuses.map((s) => (
          <button
            key={s.id}
            className={`engine-chip ${s.available ? 'up' : 'down'} ${backend === s.id ? 'active' : ''}`}
            onClick={() => onBackend(s.id)}
            title={`${s.detail}\n探测耗时 ${s.probeMs}ms`}
            type="button"
          >
            <span className="dot" />
            <span className="engine-label">{s.label}</span>
            <span className="engine-state">{s.available ? '可用' : '不可用'}</span>
          </button>
        ))}
        <button className="ghost-btn" onClick={onReprobe} disabled={probing} type="button">
          {probing ? '探测中…' : '重新探测'}
        </button>
      </div>

      <div className="top-actions">
        <button className="ghost-btn" onClick={onOpenSelftest} type="button">
          彩排自检
        </button>
        <button className="primary-btn" onClick={onExport} disabled={!canExport} type="button">
          导出 MIDI
        </button>
      </div>
    </header>
  );
}

import { useState } from 'react';
import { SUNO_EXCLUDE, SUNO_STYLE_PROMPT, tagLyrics } from '../music/suno';

/**
 * 司凤音乐制作台（Suno 版）。
 *
 * 课堂场景：学校电脑、不能装东西、只能双击这个 HTML。
 * 所以这里不做任何网络请求——网页负责「写歌词」和「写提示词」，
 * 生成由 Suno 在浏览器里完成，中间只有复制和跳转。
 */

/** 演示用的示例歌词（原创，不涉及版权） */
const SAMPLE_LYRIC = `雨停在这条街的尽头
我还在等一句没出口的挽留

你说过的话被风吹散
我数着灯灭了几盏

如果那天我没有回头
是不是就不会走丢
如果时间能再慢一点
我是不是还能牵你的手

天亮以后
我把你留在昨夜的梦里`;

const SUNO_CREATE = 'https://suno.com/create';

function copyWithFallback(text: string): boolean {
  try {
    const el = document.createElement('textarea');
    el.value = text;
    el.setAttribute('readonly', '');
    el.style.position = 'fixed';
    el.style.opacity = '0';
    document.body.appendChild(el);
    el.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(el);
    if (ok) return true;
  } catch {
    /* 落到下面的 clipboard */
  }
  return false;
}

export function SunoTool({ onClose }: { onClose: () => void }) {
  const [raw, setRaw] = useState('');
  const [out, setOut] = useState<{ text: string; sections: number; adlibs: number } | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  async function copy(label: string, text: string) {
    let ok = false;
    try {
      await navigator.clipboard.writeText(text);
      ok = true;
    } catch {
      ok = copyWithFallback(text);
    }
    setCopied(ok ? label : '复制失败，请手动选中文本');
    setTimeout(() => setCopied(null), 1800);
  }

  const allInOne = `【风格提示词】\n${SUNO_STYLE_PROMPT}\n\n【排除项】\n${SUNO_EXCLUDE}\n\n【歌词】\n${out?.text ?? raw}`;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <header className="modal-head">
          <div>
            <h2>司凤音乐制作台</h2>
            <p>
              四步走：这里写歌词和提示词，复制到 Suno 生成。网页本身不联网、不登录、不需要安装任何东西——
              学校电脑双击打开就能用。
            </p>
          </div>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </header>

        <div className="modal-body">
          <ol className="steps">
            <li>
              <b>1</b> 贴歌词
            </li>
            <li>
              <b>2</b> 点「加工」
            </li>
            <li>
              <b>3</b> 复制提示词
            </li>
            <li>
              <b>4</b> 打开 Suno 粘贴
            </li>
          </ol>

          <section className="tool-block">
            <div className="tool-label">
              <span>① 歌词</span>
              <button
                className="ghost-btn tiny"
                onClick={() => {
                  setRaw(SAMPLE_LYRIC);
                  setOut(null);
                }}
              >
                用示例歌词
              </button>
            </div>
            <textarea
              className="tool-input"
              rows={7}
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
              placeholder={'第一段歌词…\n\n第二段歌词…\n\n第三段歌词…\n（段落之间空一行）'}
            />
            <div className="tool-actions">
              <button className="prompt-btn" onClick={() => setOut(tagLyrics(raw))} disabled={!raw.trim()}>
                ② 加工成 Suno 格式
              </button>
              {out && (
                <span className="tool-meta">
                  {out.sections} 段 · 插入 {out.adlibs} 处加花
                </span>
              )}
            </div>
          </section>

          {out && (
            <section className="tool-block">
              <div className="tool-label">
                <span>③ 加工后的歌词</span>
                <button className="ghost-btn tiny" onClick={() => copy('lyrics', out.text)}>
                  {copied === 'lyrics' ? '已复制' : '复制歌词'}
                </button>
              </div>
              <pre className="tool-output">{out.text}</pre>
            </section>
          )}

          <section className="tool-block">
            <div className="tool-label">
              <span>③ 风格提示词与排除项</span>
              <button className="ghost-btn tiny" onClick={() => copy('style', SUNO_STYLE_PROMPT)}>
                {copied === 'style' ? '已复制' : '复制风格'}
              </button>
            </div>
            <pre className="tool-output small">{SUNO_STYLE_PROMPT}</pre>
            <div className="tool-label">
              <span>排除项</span>
              <button className="ghost-btn tiny" onClick={() => copy('exclude', SUNO_EXCLUDE)}>
                {copied === 'exclude' ? '已复制' : '复制排除项'}
              </button>
            </div>
            <pre className="tool-output small">{SUNO_EXCLUDE}</pre>
          </section>

          <section className="tool-block">
            <div className="tool-label">
              <span>④ 去 Suno 生成</span>
              <button className="ghost-btn tiny" onClick={() => copy('all', allInOne)}>
                {copied === 'all' ? '已复制' : '复制全部'}
              </button>
            </div>
            <div className="tool-actions">
              <a className="primary-btn link-btn" href={SUNO_CREATE} target="_blank" rel="noreferrer">
                打开 Suno（新标签页）
              </a>
              <span className="tool-meta">Custom 模式：歌词粘歌词框，风格和排除项填对应输入框</span>
            </div>
          </section>

          <p className="tool-note">
            提示词与规则来自 B 站《零基础司凤音乐制作教程》公开的简介内容。
            生成需要有网的浏览器和 Suno 账号——这一步网页替代不了，只能手动完成。
          </p>
        </div>
        {copied && <div className="copy-toast">{copied}</div>}
      </div>
    </div>
  );
}
